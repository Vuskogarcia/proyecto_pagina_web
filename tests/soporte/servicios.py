"""Reglas de negocio del soporte postventa (HU-05, HU-06, HU-07, HU-08, HU-09)."""

from django.contrib.auth import get_user_model
from django.db import transaction

from carrito.models import Pedido
from comun.excepciones import DatosInvalidos, EstadoInvalido, NoEncontrado, SinPermiso
from comun.roles import es_agente
from comun.validaciones import entero, texto
from cuentas import auditoria
from cuentas.models import EventoAuditoria

from .models import RegistroAsignacion, RespuestaTicket, TicketSoporte

MAX_DESCRIPCION = 5000
MAX_RESPUESTA = 5000
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
    elif not isinstance(tipo, str) or tipo not in tipos_validos:  # lista de permitidos (ADL-04)
        raise DatosInvalidos(f"El tipo debe ser uno de: {', '.join(sorted(tipos_validos))}")
    pedido_id = entero(pedido_id, "id_pedido", obligatorio=False)
    descripcion = texto(descripcion, "descripcion", maximo=MAX_DESCRIPCION)
    # El asunto es opcional. Antes se recortaba a 200 caracteres; desde la
    # Historia 03 (Módulo 7) un asunto más largo es un 400, igual que la
    # descripción: un texto de 50 000 caracteres no se acepta a medias.
    asunto = texto(asunto, "asunto", obligatorio=False, maximo=MAX_ASUNTO) if asunto is not None else ""

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


# El id desempata: dos tickets creados en el mismo instante (mismo
# `creado_en`) salían en orden arbitrario y la prueba de orden fallaba a veces.
ORDENES_COLA = {"antiguos": ("creado_en", "id"), "recientes": ("-creado_en", "-id")}


def cola_sin_asignar(orden="antiguos"):
    """HU-07: tickets abiertos que ningún agente ha tomado.

    Por defecto del más antiguo al más nuevo; `orden="recientes"` invierte.
    Un orden fuera de la lista de permitidos es un 400 (ADL-04, Historia 03
    del Módulo 7); antes se ignoraba en silencio.
    """
    if orden not in ORDENES_COLA:
        raise DatosInvalidos(f"El orden debe ser uno de: {', '.join(sorted(ORDENES_COLA))}")
    return (
        TicketSoporte.objects.filter(estado=TicketSoporte.ABIERTO, agente__isnull=True)
        .select_related("cliente", "pedido")
        .order_by(*ORDENES_COLA[orden])
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



def _ticket_del_agente(ticket_id, agente_id):
    """Bloquea el ticket y verifica que lo tenga asignado ESTE agente.

    HU-10 criterio 1: solo el agente asignado puede responder o cambiar el
    estado. select_for_update evita que dos cambios simultáneos se pisen.
    """
    agente = _usuario(entero(agente_id, "id_agente"), "agente")
    if not es_agente(agente):
        raise SinPermiso("Solo un agente de soporte puede atender tickets")
    ticket_id = entero(ticket_id, "id_ticket")
    try:
        ticket = TicketSoporte.objects.select_for_update().get(pk=ticket_id)
    except TicketSoporte.DoesNotExist:
        raise NoEncontrado(f"El ticket {ticket_id} no existe")
    if ticket.agente_id != agente.pk:
        raise SinPermiso("Solo el agente asignado puede atender este ticket")
    return ticket, agente


@transaction.atomic
def responder_ticket(ticket_id, agente_id, mensaje):
    """HU-10 criterio 2: la respuesta queda registrada con fecha y autor."""
    mensaje = texto(mensaje, "mensaje", maximo=MAX_RESPUESTA)
    ticket, agente = _ticket_del_agente(ticket_id, agente_id)
    if ticket.estado == TicketSoporte.CERRADO:
        raise EstadoInvalido("El ticket está cerrado: ya no admite respuestas")
    respuesta = RespuestaTicket.objects.create(ticket=ticket, autor=agente, mensaje=mensaje)
    auditoria.registrar(EventoAuditoria.TICKET_RESPONDIDO, usuario=agente, detalle=ticket.numero)
    return respuesta


@transaction.atomic
def cambiar_estado(ticket_id, agente_id, nuevo_estado):
    """HU-10 criterio 3: En proceso -> Resuelto -> Cerrado (y reabrir).

    Solo se permiten las transiciones de TicketSoporte.TRANSICIONES: un
    estado desconocido es 400; uno no permitido desde el actual, 409.
    """
    validos = {valor for valor, _ in TicketSoporte.ESTADOS}
    if not isinstance(nuevo_estado, str) or nuevo_estado not in validos:
        raise DatosInvalidos(f"El estado debe ser uno de: {', '.join(sorted(validos))}")
    ticket, agente = _ticket_del_agente(ticket_id, agente_id)
    permitidos = TicketSoporte.TRANSICIONES.get(ticket.estado, set())
    if nuevo_estado not in permitidos:
        raise EstadoInvalido(
            f"No se puede pasar de {ticket.get_estado_display()} a "
            f"{dict(TicketSoporte.ESTADOS)[nuevo_estado]}"
        )
    anterior = ticket.estado
    ticket.estado = nuevo_estado
    ticket.save(update_fields=["estado"])
    auditoria.registrar(EventoAuditoria.TICKET_ESTADO, usuario=agente,
                        detalle=f"{ticket.numero} {anterior} -> {nuevo_estado}")
    return ticket


def estados_siguientes(ticket):
    """Estados a los que el agente asignado puede mover el ticket (para la web)."""
    nombres = dict(TicketSoporte.ESTADOS)
    return [(e, nombres[e]) for e in (TicketSoporte.EN_PROCESO, TicketSoporte.RESUELTO,
                                      TicketSoporte.CERRADO)
            if e in TicketSoporte.TRANSICIONES.get(ticket.estado, set())]
