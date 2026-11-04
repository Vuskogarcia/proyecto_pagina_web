"""Carrito editable guardado en la sesión (HU-04, criterio 1; DT-02).

El cliente agrega, cambia y quita productos antes de pagar. El carrito solo
guarda {id_producto: cantidad}; precios y stock se leen siempre de la base
de datos al mostrarlo y al pagar, así que no se pueden manipular desde el
navegador.
"""

from decimal import Decimal

from catalogo.models import Producto
from comun.excepciones import DatosInvalidos, NoEncontrado
from comun.validaciones import entero

from . import servicios

CLAVE = "carrito"


def _leer(sesion):
    crudo = sesion.get(CLAVE) or {}
    return {int(k): int(v) for k, v in crudo.items()}


def _guardar(sesion, carrito):
    sesion[CLAVE] = {str(k): v for k, v in carrito.items()}
    sesion.modified = True


def agregar(sesion, producto_id, cantidad=1):
    producto_id = entero(producto_id, "id_producto")
    cantidad = entero(cantidad, "cantidad", maximo=servicios.MAX_CANTIDAD_POR_PRODUCTO)
    if not Producto.objects.filter(pk=producto_id, activo=True).exists():
        raise NoEncontrado(f"El producto {producto_id} no existe")
    carrito = _leer(sesion)
    if producto_id not in carrito and len(carrito) >= servicios.MAX_ITEMS_POR_PEDIDO:
        raise DatosInvalidos(f"El carrito admite máximo {servicios.MAX_ITEMS_POR_PEDIDO} productos")
    nueva = carrito.get(producto_id, 0) + cantidad
    if nueva > servicios.MAX_CANTIDAD_POR_PRODUCTO:
        raise DatosInvalidos(f"Máximo {servicios.MAX_CANTIDAD_POR_PRODUCTO} unidades por producto")
    carrito[producto_id] = nueva
    _guardar(sesion, carrito)


def cambiar_cantidad(sesion, producto_id, cantidad):
    producto_id = entero(producto_id, "id_producto")
    carrito = _leer(sesion)
    if producto_id not in carrito:
        raise NoEncontrado("Ese producto no está en tu carrito")
    carrito[producto_id] = entero(cantidad, "cantidad", maximo=servicios.MAX_CANTIDAD_POR_PRODUCTO)
    _guardar(sesion, carrito)


def quitar(sesion, producto_id):
    producto_id = entero(producto_id, "id_producto")
    carrito = _leer(sesion)
    carrito.pop(producto_id, None)
    _guardar(sesion, carrito)


def vaciar(sesion):
    sesion.pop(CLAVE, None)


def unidades(sesion):
    return sum(_leer(sesion).values())


def resumen(sesion):
    """Líneas del carrito con precios actuales y el total (criterio 2)."""
    carrito = _leer(sesion)
    productos = Producto.objects.filter(pk__in=carrito, activo=True).order_by("nombre")
    lineas = []
    for producto in productos:
        cantidad = carrito[producto.pk]
        lineas.append(
            {
                "producto": producto,
                "cantidad": cantidad,
                "subtotal": producto.precio * cantidad,
                "sin_stock": not producto.hay_disponible(cantidad),
            }
        )
    total = sum((linea["subtotal"] for linea in lineas), start=Decimal("0"))
    return {"lineas": lineas, "total": total}


def pagar(sesion, cliente):
    """Convierte el carrito en un pedido con el checkout transaccional."""
    carrito = _leer(sesion)
    items = [{"id_producto": pid, "cantidad": cant} for pid, cant in carrito.items()]
    pedido = servicios.realizar_checkout(cliente.pk, items)
    vaciar(sesion)
    return pedido
