"""Reglas de negocio del checkout (HU-04)."""

from django.contrib.auth import get_user_model
from django.db import transaction

from catalogo.models import Producto
from comun.excepciones import DatosInvalidos, EstadoInvalido, NoEncontrado
from comun.roles import es_agente
from comun.validaciones import entero
from cuentas import auditoria
from cuentas.models import EventoAuditoria

from .models import ItemPedido, Pedido


# Cotas de negocio (ADL-04): un pedido de tienda no trae miles de líneas
# ni miles de unidades de un mismo producto.
MAX_ITEMS_POR_PEDIDO = 50
MAX_CANTIDAD_POR_PRODUCTO = 1000
CAMPOS_ITEM = {"id_producto", "cantidad"}


def _normalizar_items(items):
    """Valida la lista de items y agrupa cantidades del mismo producto."""
    if not isinstance(items, list) or not items:
        raise DatosInvalidos("El pedido debe tener al menos un producto")
    if len(items) > MAX_ITEMS_POR_PEDIDO:
        raise DatosInvalidos(f"El pedido admite máximo {MAX_ITEMS_POR_PEDIDO} items")
    cantidades = {}
    for item in items:
        if not isinstance(item, dict):
            raise DatosInvalidos("Cada item debe tener 'id_producto' y 'cantidad'")
        sobrantes = set(item) - CAMPOS_ITEM
        if sobrantes:
            raise DatosInvalidos(f"Campos no permitidos en el item: {', '.join(sorted(sobrantes))}")
        producto_id = entero(item.get("id_producto"), "id_producto")
        cantidad = entero(item.get("cantidad"), "cantidad", maximo=MAX_CANTIDAD_POR_PRODUCTO)
        cantidades[producto_id] = cantidades.get(producto_id, 0) + cantidad
        if cantidades[producto_id] > MAX_CANTIDAD_POR_PRODUCTO:
            raise DatosInvalidos(
                f"Máximo {MAX_CANTIDAD_POR_PRODUCTO} unidades por producto en un pedido"
            )
    return cantidades


@transaction.atomic
def realizar_checkout(cliente_id, items):
    """Crea un pedido confirmado y descuenta el stock.

    Todo o nada: si un producto no tiene stock suficiente, no se crea el
    pedido ni se descuenta nada. select_for_update bloquea las filas de los
    productos para que dos checkouts simultáneos no dejen el stock negativo.
    """
    cliente_id = entero(cliente_id, "id_cliente")
    cantidades = _normalizar_items(items)

    try:
        cliente = get_user_model().objects.get(pk=cliente_id)
    except get_user_model().DoesNotExist:
        raise NoEncontrado(f"El cliente {cliente_id} no existe")

    # Se bloquean en orden de id para evitar deadlocks entre checkouts.
    productos = {
        p.pk: p
        for p in Producto.objects.select_for_update()
        .filter(pk__in=cantidades, activo=True)
        .order_by("pk")
    }
    for producto_id, cantidad in cantidades.items():
        producto = productos.get(producto_id)
        if producto is None:
            raise NoEncontrado(f"El producto {producto_id} no existe")
        if not producto.hay_disponible(cantidad):
            raise EstadoInvalido(f"Stock insuficiente para {producto.nombre}")

    pedido = Pedido.objects.create(cliente=cliente, estado=Pedido.CONFIRMADO)
    for producto_id, cantidad in cantidades.items():
        producto = productos[producto_id]
        producto.stock -= cantidad
        producto.save(update_fields=["stock"])
        ItemPedido.objects.create(
            pedido=pedido, producto=producto, cantidad=cantidad, precio_pactado=producto.precio
        )
    # Dentro de la transacción: si el pedido se revierte, el evento también.
    auditoria.registrar(EventoAuditoria.PEDIDO_CREADO, usuario=cliente,
                        detalle=f"{pedido.codigo} total={pedido.total()}")
    return pedido


def detalle_pedido(pedido_id):
    try:
        return Pedido.objects.prefetch_related("items__producto").get(pk=pedido_id)
    except Pedido.DoesNotExist:
        raise NoEncontrado(f"El pedido {pedido_id} no existe")


def pedido_visible_para(pedido_id, usuario):
    """El pedido si `usuario` puede verlo: su dueño o un agente (HU-09).

    Un pedido ajeno responde igual que uno inexistente (ADL-03, decisión
    del equipo: 404), para no revelar qué pedidos existen.
    """
    pedido = detalle_pedido(pedido_id)
    if pedido.cliente_id != usuario.pk and not es_agente(usuario):
        raise NoEncontrado(f"El pedido {pedido_id} no existe")
    return pedido


def pedidos_de(cliente):
    """Pedidos del cliente, del más reciente al más antiguo."""
    return Pedido.objects.filter(cliente=cliente).prefetch_related("items__producto")
