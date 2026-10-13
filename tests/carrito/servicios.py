"""Reglas de negocio del checkout (HU-04)."""

from django.contrib.auth import get_user_model
from django.db import transaction

from catalogo.models import Producto
from comun.excepciones import DatosInvalidos, EstadoInvalido, NoEncontrado
from comun.http import entero

from .models import ItemPedido, Pedido


def _normalizar_items(items):
    """Valida la lista de items y agrupa cantidades del mismo producto."""
    if not isinstance(items, list) or not items:
        raise DatosInvalidos("El pedido debe tener al menos un producto")
    cantidades = {}
    for item in items:
        if not isinstance(item, dict):
            raise DatosInvalidos("Cada item debe tener 'id_producto' y 'cantidad'")
        producto_id = entero(item.get("id_producto"), "id_producto")
        cantidad = entero(item.get("cantidad"), "cantidad")
        cantidades[producto_id] = cantidades.get(producto_id, 0) + cantidad
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
    return pedido


def detalle_pedido(pedido_id):
    try:
        return Pedido.objects.prefetch_related("items__producto").get(pk=pedido_id)
    except Pedido.DoesNotExist:
        raise NoEncontrado(f"El pedido {pedido_id} no existe")


def a_dict(pedido):
    return {
        "id": pedido.pk,
        "codigo": pedido.codigo,
        "id_cliente": pedido.cliente_id,
        "estado": pedido.estado,
        "fecha": pedido.creado_en.isoformat(),
        "total": str(pedido.total()),
        "items": [
            {
                "id_producto": item.producto_id,
                "producto": item.producto.nombre,
                "cantidad": item.cantidad,
                "precio": str(item.precio_pactado),
                "subtotal": str(item.subtotal()),
            }
            for item in pedido.items.all()
        ],
    }
