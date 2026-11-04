"""Convierte las entidades de carrito en diccionarios listos para JSON.

Separado de servicios.py para que el servicio solo tenga reglas de negocio
(responsabilidad única; ver docs/revision-codigo.md, RC-03).
"""


def a_dict(pedido):
    return {
        "id": pedido.pk,
        "codigo": pedido.codigo,
        "id_cliente": pedido.cliente_id,
        "estado": pedido.estado,
        "fecha": pedido.creado_en.isoformat(),
        "total": str(pedido.total()),
        "envio": {
            "nombre": pedido.envio_nombre,
            "direccion": pedido.envio_direccion,
            "ciudad": pedido.envio_ciudad,
            "telefono": pedido.envio_telefono,
        },
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
