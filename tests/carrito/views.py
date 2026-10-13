"""Controlador HTTP de pedidos. No decide nada: llama al servicio."""

from django.http import JsonResponse

from comun.http import api, leer_json

from . import servicios


@api("POST")
def checkout(request):
    datos = leer_json(request)
    pedido = servicios.realizar_checkout(datos.get("id_cliente"), datos.get("items"))
    return JsonResponse(servicios.a_dict(pedido), status=201)


@api("GET")
def ver_pedido(request, pedido_id):
    return JsonResponse(servicios.a_dict(servicios.detalle_pedido(pedido_id)))
