"""Reglas de negocio del soporte postventa (HU-05, HU-07, HU-08)."""

from django.contrib.auth import get_user_model
from django.db import transaction

from carrito.models import Pedido
from comun.excepciones import DatosInvalidos, EstadoInvalido, NoEncontrado
from comun.http import entero

from .models import RegistroAsignacion, TicketSoporte


def _usuario(usuario_id, rol):
    try:
        return get_user_model().objects.get(pk=usuario_id)
    except get_user_model().DoesNotExist:
        raise NoEncontrado(f"El {rol} {usuario_id} no existe")


def crear_ticket(cliente_id, descripcion, pedido_id=None, asunto=""):
    """HU-05: el cliente crea un ticket, opcionalmente asociado a uno de SUS pedidos."""
    cliente_id = entero(cliente_id, "id_cliente")
    pedido_id = entero(pedido_id, "id_pedido", obligatorio=False)
    descripcion = (descripcion or "").strip() if isinstance(descripcion, str) else ""
    if not descripcion:
        raise DatosInvalidos("La descripción del problema es obligatoria")

    cliente = _usuario(cliente_id, "cliente")
    pedido = None
    if pedido_id is not None:
        try:
            pedido = Pedido.objects.get(pk=pedido_id)
        except Pedido.DoesNotExist:
            raise NoEncontrado(f"El pedido {pedido_id} no existe")
        if pedido.cliente_id != cliente.pk:
            raise DatosInvalidos("El pedido no pertenece a este cliente")

    return TicketSoporte.objects.create(
        cliente=cliente,
        pedido=pedido,
        asunto=(asunto or "").strip()[:200] if isinstance(asunto, str) else "",
        descripcion=descripcion,
    )


def cola_sin_asignar():
    """HU-07: tickets abiertos que ningún agente ha tomado, del más antiguo al más nuevo."""
    return TicketSoporte.objects.filter(
        estado=TicketSoporte.ABIERTO, agente__isnull=True
    ).select_related("cliente", "pedido")


@transaction.atomic
def tomar_ticket(ticket_id, agente_id):
    """HU-08: un agente se asigna un ticket.

    Bloqueo pesimista: select_for_update bloquea la fila del ticket hasta que
    termina la transacción. Si dos agentes llegan a la vez, el segundo espera,
    luego ve el ticket ya asignado y recibe EstadoInvalido (409).
    """
    agente = _usuario(entero(agente_id, "id_agente"), "agente")
    try:
        ticket = TicketSoporte.objects.select_for_update().get(pk=ticket_id)
    except TicketSoporte.DoesNotExist:
        raise NoEncontrado(f"El ticket {ticket_id} no existe")

    if ticket.agente_id is not None or ticket.estado != TicketSoporte.ABIERTO:
        raise EstadoInvalido("El ticket ya fue asignado")

    ticket.agente = agente
    ticket.estado = TicketSoporte.EN_PROCESO
    ticket.save(update_fields=["agente", "estado"])
    RegistroAsignacion.objects.create(ticket=ticket, agente=agente)
    return ticket


def detalle_ticket(ticket_id):
    try:
        return TicketSoporte.objects.select_related("cliente", "pedido", "agente").get(pk=ticket_id)
    except TicketSoporte.DoesNotExist:
        raise NoEncontrado(f"El ticket {ticket_id} no existe")


def a_dict(ticket):
    return {
        "id": ticket.pk,
        "numero": ticket.numero,
        "id_cliente": ticket.cliente_id,
        "cliente": ticket.cliente.username,
        "id_pedido": ticket.pedido_id,
        "pedido": ticket.pedido.codigo if ticket.pedido else None,
        "asunto": ticket.asunto,
        "descripcion": ticket.descripcion,
        "estado": ticket.estado,
        "agente": ticket.agente.username if ticket.agente else None,
        "fecha": ticket.creado_en.isoformat(),
    }
