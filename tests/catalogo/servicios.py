"""Reglas de negocio del catálogo (HU-02 consultar, HU-03 gestionar)."""

from django.db import transaction

from comun.excepciones import DatosInvalidos, NoEncontrado, SinPermiso
from comun.roles import es_administrador
from comun.validaciones import booleano, dinero, entero, texto
from cuentas import auditoria
from cuentas.models import EventoAuditoria

from .models import Producto

MAX_STOCK = 1_000_000
# Lista de permitidos (ADL-04): ni el id, ni la fecha de creación ni ningún
# otro campo se pueden fijar desde fuera (asignación masiva).
CAMPOS_EDITABLES = ("nombre", "descripcion", "precio", "stock", "activo")


def listar_catalogo():
    """Productos visibles en la tienda: solo los activos. Los agotados sí
    aparecen, marcados como agotados (criterio 4 de HU-02)."""
    return Producto.objects.filter(activo=True)


def detalle_producto(producto_id):
    try:
        return Producto.objects.get(pk=producto_id, activo=True)
    except Producto.DoesNotExist:
        raise NoEncontrado(f"El producto {producto_id} no existe")


# --- HU-03: gestión del catálogo (solo administradores) -------------------

def _exigir_administrador(usuario):
    # Defensa en profundidad: la vista ya lo verifica, el servicio también.
    if not es_administrador(usuario):
        raise SinPermiso("Solo un administrador puede gestionar el catálogo")


def _limpiar(datos, parcial):
    if not isinstance(datos, dict):
        raise DatosInvalidos("Los datos del producto deben ser un objeto")
    sobrantes = set(datos) - set(CAMPOS_EDITABLES)
    if sobrantes:
        raise DatosInvalidos(f"Campos no permitidos: {', '.join(sorted(sobrantes))}")
    if parcial and not datos:
        raise DatosInvalidos("No hay cambios que aplicar")
    limpios = {}
    if "nombre" in datos or not parcial:
        limpios["nombre"] = texto(datos.get("nombre"), "nombre", maximo=200)
    if "descripcion" in datos:
        limpios["descripcion"] = texto(datos.get("descripcion"), "descripcion",
                                       obligatorio=False, maximo=2000)
    if "precio" in datos or not parcial:
        limpios["precio"] = dinero(datos.get("precio"), "precio")
    if "stock" in datos:
        limpios["stock"] = entero(datos.get("stock"), "stock", minimo=0, maximo=MAX_STOCK)
    if "activo" in datos:
        limpios["activo"] = booleano(datos.get("activo"), "activo")
    return limpios


def listar_todos(usuario):
    """Todos los productos, también los desactivados (vista del administrador)."""
    _exigir_administrador(usuario)
    return Producto.objects.order_by("-activo", "nombre")


def producto_para_editar(usuario, producto_id):
    _exigir_administrador(usuario)
    try:
        return Producto.objects.get(pk=entero(producto_id, "id_producto"))
    except Producto.DoesNotExist:
        raise NoEncontrado(f"El producto {producto_id} no existe")


def crear_producto(usuario, datos):
    """HU-03 criterio 1: el administrador crea productos."""
    _exigir_administrador(usuario)
    producto = Producto.objects.create(**_limpiar(datos, parcial=False))
    auditoria.registrar(EventoAuditoria.PRODUCTO_CREADO, usuario=usuario,
                        detalle=f"#{producto.pk} precio={producto.precio} stock={producto.stock}")
    return producto


@transaction.atomic
def actualizar_producto(usuario, producto_id, datos):
    """HU-03 criterios 2 y 3: modificar datos y stock, o desactivar.

    Bloquea la fila igual que el checkout: un cambio de stock del
    administrador y una compra simultánea no se pisan.
    """
    _exigir_administrador(usuario)
    cambios = _limpiar(datos, parcial=True)
    producto_id = entero(producto_id, "id_producto")
    try:
        producto = Producto.objects.select_for_update().get(pk=producto_id)
    except Producto.DoesNotExist:
        raise NoEncontrado(f"El producto {producto_id} no existe")
    antes = {campo: getattr(producto, campo) for campo in cambios}
    for campo, valor in cambios.items():
        setattr(producto, campo, valor)
    producto.save(update_fields=list(cambios))
    resumen = ", ".join(f"{c}: {antes[c]} -> {v}" for c, v in cambios.items()
                        if c not in ("nombre", "descripcion"))
    auditoria.registrar(EventoAuditoria.PRODUCTO_EDITADO, usuario=usuario,
                        detalle=f"#{producto.pk} {resumen or 'texto actualizado'}"[:500])
    return producto
