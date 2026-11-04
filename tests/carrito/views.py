"""Controlador HTTP de pedidos. No decide nada: llama al servicio.

La identidad sale de la sesión (ADL-01): el cuerpo ya no trae id_cliente.
"""

from django.http import JsonResponse

from comun.http import api, leer_json

from . import serializadores, servicios


@api("GET", "POST")
def pedidos(request):
    """GET: mis pedidos. POST: checkout a nombre del usuario en sesión."""
    if request.method == "POST":
        datos = leer_json(request, permitidos=["items", "envio"])
        pedido = servicios.realizar_checkout(request.user.pk, datos.get("items"), datos.get("envio"))
        return JsonResponse(serializadores.a_dict(pedido), status=201)
    lista = [serializadores.a_dict(p) for p in servicios.pedidos_de(request.user)]
    return JsonResponse({"pedidos": lista})


@api("GET")
def ver_pedido(request, pedido_id):
    pedido = servicios.pedido_visible_para(pedido_id, request.user)
    return JsonResponse(serializadores.a_dict(pedido))
