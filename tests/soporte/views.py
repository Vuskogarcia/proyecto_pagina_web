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
    ticket = servicios.ticket_visible_para(ticket_id, request.user)
    return JsonResponse(serializadores.a_dict(ticket))


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
