"""Controlador HTTP de pedidos. No decide nada: llama al servicio."""

from django.http import JsonResponse

from comun.http import api, leer_json

from . import serializadores, servicios


@api("POST")
def checkout(request):
    datos = leer_json(request)
    pedido = servicios.realizar_checkout(datos.get("id_cliente"), datos.get("items"))
    return JsonResponse(serializadores.a_dict(pedido), status=201)


@api("GET")
def ver_pedido(request, pedido_id):
    return JsonResponse(serializadores.a_dict(servicios.detalle_pedido(pedido_id)))
