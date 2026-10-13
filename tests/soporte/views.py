"""Controlador HTTP del soporte. No decide nada: llama al servicio."""

from django.http import JsonResponse

from comun.http import api, leer_json

from . import servicios


@api("POST")
def crear_ticket(request):
    datos = leer_json(request)
    ticket = servicios.crear_ticket(
        cliente_id=datos.get("id_cliente"),
        descripcion=datos.get("descripcion"),
        pedido_id=datos.get("id_pedido"),
        asunto=datos.get("asunto", ""),
    )
    return JsonResponse(servicios.a_dict(ticket), status=201)


@api("GET")
def cola_sin_asignar(request):
    tickets = [servicios.a_dict(t) for t in servicios.cola_sin_asignar()]
    return JsonResponse({"tickets": tickets})


@api("GET")
def ver_ticket(request, ticket_id):
    return JsonResponse(servicios.a_dict(servicios.detalle_ticket(ticket_id)))


@api("POST")
def tomar_ticket(request, ticket_id):
    datos = leer_json(request)
    ticket = servicios.tomar_ticket(ticket_id, datos.get("id_agente"))
    return JsonResponse(servicios.a_dict(ticket))
