"""Fábricas de datos de prueba.

No son pruebas: construyen objetos ya en el estado que cada prueba necesita,
para no repetir las mismas líneas en todos los tests.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model


# Datos de envío válidos para las pruebas del checkout (HU-04 criterio 3).
ENVIO = {
    "nombre": "Ana Torres",
    "direccion": "Calle 10 # 20-30",
    "ciudad": "Bogotá",
    "telefono": "+57 300 123 4567",
}


def cliente(username="cliente1"):
    return get_user_model().objects.create_user(username=username, password="clave123")


def agente(username="agente1"):
    """Agente de soporte: miembro del grupo "agentes" (no es is_staff, H14)."""
    from django.contrib.auth.models import Group

    from comun.roles import GRUPO_AGENTES

    usuario = get_user_model().objects.create_user(username=username, password="clave123")
    usuario.groups.add(Group.objects.get_or_create(name=GRUPO_AGENTES)[0])
    return usuario


def administrador(username="admin1"):
    """Administrador (HU-01): superusuario de Django."""
    return get_user_model().objects.create_superuser(
        username=username, email=f"{username}@example.com", password="clave123"
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

    pedido_obj = Pedido.objects.create(
        cliente=cliente_obj,
        estado=Pedido.CONFIRMADO,
        envio_nombre=ENVIO["nombre"],
        envio_direccion=ENVIO["direccion"],
        envio_ciudad=ENVIO["ciudad"],
        envio_telefono=ENVIO["telefono"],
    )
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
