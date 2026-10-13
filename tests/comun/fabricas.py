"""Fábricas de datos de prueba.

No son pruebas: construyen objetos ya en el estado que cada prueba necesita,
para no repetir las mismas líneas en todos los tests.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model


def cliente(username="cliente1"):
    return get_user_model().objects.create_user(username=username, password="clave123")


def agente(username="agente1"):
    return get_user_model().objects.create_user(
        username=username, password="clave123", is_staff=True
    )


def producto(nombre="Teclado mecánico", precio="150000", stock=10, activo=True):
    from catalogo.models import Producto

    return Producto.objects.create(
        nombre=nombre,
        descripcion=f"Descripción de {nombre}",
        precio=Decimal(precio),
        stock=stock,
        activo=activo,
    )


def pedido(cliente_obj, productos_cantidades=None):
    """Crea un pedido confirmado sin pasar por el checkout."""
    from carrito.models import ItemPedido, Pedido

    pedido_obj = Pedido.objects.create(cliente=cliente_obj, estado=Pedido.CONFIRMADO)
    for prod, cantidad in productos_cantidades or []:
        ItemPedido.objects.create(
            pedido=pedido_obj, producto=prod, cantidad=cantidad, precio_pactado=prod.precio
        )
    return pedido_obj


def ticket(cliente_obj, descripcion="No llegó el paquete", pedido_obj=None):
    from soporte.models import TicketSoporte

    return TicketSoporte.objects.create(
        cliente=cliente_obj, pedido=pedido_obj, descripcion=descripcion
    )
