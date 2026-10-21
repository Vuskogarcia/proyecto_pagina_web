"""Convierte las entidades de catalogo en diccionarios listos para JSON.

Separado de servicios.py para que el servicio solo tenga reglas de negocio
(responsabilidad única; ver docs/revision-codigo.md, RC-03).
"""


def a_dict(producto):
    return {
        "id": producto.pk,
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "precio": str(producto.precio),
        "stock": producto.stock,
        "agotado": producto.agotado,
    }
