"""Controlador HTTP del soporte. No decide nada: llama al servicio.

La identidad sale de la sesión (ADL-01): el cuerpo ya no trae id_cliente
ni id_agente; si los trae, la petición se rechaza con 400.
"""

from django.http import JsonResponse

from comun.excepciones import EstadoInvalido
from comun.http import AGENTE, api, leer_json
from cuentas import auditoria
from cuentas.models import EventoAuditoria

from . import serializadores, servicios


@api("GET", "POST")
def tickets(request):
    """GET: mis tickets (HU-06). POST: crear un ticket (HU-05)."""
    if request.method == "POST":
        datos = leer_json(request, permitidos=["descripcion", "id_pedido", "asunto", "tipo"])
        ticket = servicios.crear_ticket(
            cliente_id=request.user.pk,
            descripcion=datos.get("descripcion"),
            pedido_id=datos.get("id_pedido"),
            asunto=datos.get("asunto", ""),
            tipo=datos.get("tipo"),
        )
        return JsonResponse(serializadores.a_dict(ticket), status=201)
    lista = [serializadores.a_dict(t) for t in servicios.tickets_de(request.user)]
    return JsonResponse({"tickets": lista})


@api("GET", acceso=AGENTE)
def cola_sin_asignar(request):
    orden = request.GET.get("orden", "antiguos")
    tickets_cola = [serializadores.a_dict(t) for t in servicios.cola_sin_asignar(orden)]
    return JsonResponse({"tickets": tickets_cola})


@api("GET")
def ver_ticket(request, ticket_id):
    """HU-05/HU-06/HU-10: el ticket con su historial de respuestas."""
    ticket = servicios.ticket_visible_para(ticket_id, request.user)
    return JsonResponse(serializadores.a_dict(ticket, con_respuestas=True))


@api("POST", acceso=AGENTE)
def responder(request, ticket_id):
    """HU-10 criterio 2: el agente asignado responde el ticket."""
    datos = leer_json(request, permitidos=["mensaje"])
    respuesta = servicios.responder_ticket(ticket_id, request.user.pk, datos.get("mensaje"))
    return JsonResponse(serializadores.respuesta_a_dict(respuesta), status=201)


@api("POST", acceso=AGENTE)
def cambiar_estado(request, ticket_id):
    """HU-10 criterio 3: el agente asignado cambia el estado del ticket."""
    datos = leer_json(request, permitidos=["estado"])
    ticket = servicios.cambiar_estado(ticket_id, request.user.pk, datos.get("estado"))
    return JsonResponse(serializadores.a_dict(ticket, con_respuestas=True))


@api("POST")
def tomar_ticket(request, ticket_id):
    # Cuerpo vacío: el agente es el de la sesión. El servicio verifica el rol
    # (403 si quien intenta es un cliente).
    leer_json(request, permitidos=[])
    try:
        ticket = servicios.tomar_ticket(ticket_id, request.user.pk)
    except EstadoInvalido:
        # Fuera de la transacción del servicio, para que el evento no se revierta.
        auditoria.registrar(EventoAuditoria.TICKET_CONFLICTO, request, detalle=f"ticket={ticket_id}")
        raise
    return JsonResponse(serializadores.a_dict(ticket))
