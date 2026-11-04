"""Reglas de negocio del soporte postventa (HU-05, HU-06, HU-07, HU-08, HU-09)."""

from django.contrib.auth import get_user_model
from django.db import transaction

from carrito.models import Pedido
from comun.excepciones import DatosInvalidos, EstadoInvalido, NoEncontrado, SinPermiso
from comun.roles import es_agente
from comun.validaciones import entero, texto, texto_seguro
from cuentas import auditoria
from cuentas.models import EventoAuditoria

from .models import RegistroAsignacion, TicketSoporte

MAX_DESCRIPCION = 5000
MAX_ASUNTO = 200


def _usuario(usuario_id, rol):
    try:
        return get_user_model().objects.get(pk=usuario_id)
    except get_user_model().DoesNotExist:
        raise NoEncontrado(f"El {rol} {usuario_id} no existe")


def crear_ticket(cliente_id, descripcion, pedido_id=None, asunto="", tipo=None):
    """HU-05: el cliente crea un ticket, opcionalmente asociado a uno de SUS pedidos."""
    cliente_id = entero(cliente_id, "id_cliente")
    tipos_validos = {valor for valor, _ in TicketSoporte.TIPOS}
    if tipo is None:
        tipo = TicketSoporte.PETICION
    elif tipo not in tipos_validos:  # lista de permitidos (ADL-04)
        raise DatosInvalidos(f"El tipo debe ser uno de: {', '.join(sorted(tipos_validos))}")
    pedido_id = entero(pedido_id, "id_pedido", obligatorio=False)
    descripcion = texto(descripcion, "descripcion", maximo=MAX_DESCRIPCION)
    # El asunto es opcional y se recorta a 200 caracteres (comportamiento ya
    # acordado), pero igual se valida contra NUL y surrogates (ADL-05).
    asunto = texto_seguro(asunto.strip(), "asunto")[:MAX_ASUNTO] if isinstance(asunto, str) else ""

    cliente = _usuario(cliente_id, "cliente")
    pedido = None
    if pedido_id is not None:
        # Pedido ajeno = pedido inexistente (ADL-03): mismo 404, mismo mensaje.
        pedido = Pedido.objects.filter(pk=pedido_id, cliente=cliente).first()
        if pedido is None:
            raise NoEncontrado(f"El pedido {pedido_id} no existe")

    ticket = TicketSoporte.objects.create(
        cliente=cliente, pedido=pedido, asunto=asunto, descripcion=descripcion, tipo=tipo
    )
    auditoria.registrar(EventoAuditoria.TICKET_CREADO, usuario=cliente,
                        detalle=f"{ticket.numero} {tipo} pedido={pedido.codigo if pedido else '-'}")
    return ticket


ORDENES_COLA = {"antiguos": "creado_en", "recientes": "-creado_en"}


def cola_sin_asignar(orden="antiguos"):
    """HU-07: tickets abiertos que ningún agente ha tomado.

    Por defecto del más antiguo al más nuevo; `orden="recientes"` invierte.
    """
    return (
        TicketSoporte.objects.filter(estado=TicketSoporte.ABIERTO, agente__isnull=True)
        .select_related("cliente", "pedido")
        .order_by(ORDENES_COLA.get(orden, "creado_en"))
    )


@transaction.atomic
def tomar_ticket(ticket_id, agente_id):
    """HU-08: un agente se asigna un ticket.

    Bloqueo pesimista: select_for_update bloquea la fila del ticket hasta que
    termina la transacción. Si dos agentes llegan a la vez, el segundo espera,
    luego ve el ticket ya asignado y recibe EstadoInvalido (409).
    Solo los agentes (grupo "agentes") pueden tomar tickets: un cliente recibe 403.
    """
    agente = _usuario(entero(agente_id, "id_agente"), "agente")
    if not es_agente(agente):
        raise SinPermiso("Solo un agente de soporte puede tomar tickets")
    ticket_id = entero(ticket_id, "id_ticket")
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
    auditoria.registrar(EventoAuditoria.TICKET_TOMADO, usuario=agente, detalle=ticket.numero)
    return ticket


def detalle_ticket(ticket_id):
    try:
        return TicketSoporte.objects.select_related("cliente", "pedido", "agente").get(pk=ticket_id)
    except TicketSoporte.DoesNotExist:
        raise NoEncontrado(f"El ticket {ticket_id} no existe")


def ticket_visible_para(ticket_id, usuario):
    """El ticket si `usuario` es su dueño o un agente; si no, 404 (ADL-03)."""
    ticket = detalle_ticket(ticket_id)
    if ticket.cliente_id != usuario.pk and not es_agente(usuario):
        raise NoEncontrado(f"El ticket {ticket_id} no existe")
    return ticket


def tickets_de(cliente):
    """HU-06: los tickets del cliente, del más reciente al más antiguo."""
    return (
        TicketSoporte.objects.filter(cliente=cliente)
        .select_related("cliente", "pedido", "agente")
        .order_by("-creado_en")
    )


def asignados_a(agente):
    """Tickets que el agente tiene asignados (bandeja del agente)."""
    return (
        TicketSoporte.objects.filter(agente=agente)
        .select_related("cliente", "pedido", "agente")
        .order_by("estado", "-creado_en")
    )
