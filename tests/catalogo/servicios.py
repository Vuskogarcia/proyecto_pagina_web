"""Reglas de negocio del catálogo (HU-02)."""

from comun.excepciones import NoEncontrado

from .models import Producto


def listar_catalogo():
    """Productos visibles en la tienda: solo los activos. Los agotados sí
    aparecen, marcados como agotados (criterio 4 de HU-02)."""
    return Producto.objects.filter(activo=True)


def detalle_producto(producto_id):
    try:
        return Producto.objects.get(pk=producto_id, activo=True)
    except Producto.DoesNotExist:
        raise NoEncontrado(f"El producto {producto_id} no existe")
