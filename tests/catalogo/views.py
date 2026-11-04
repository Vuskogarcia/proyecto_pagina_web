"""Controlador HTTP del catálogo. No decide nada: llama al servicio."""

from django.http import JsonResponse

from comun.http import PUBLICO, api

from . import serializadores, servicios


@api("GET", acceso=PUBLICO)
def listar_productos(request):
    productos = [serializadores.a_dict(p) for p in servicios.listar_catalogo()]
    return JsonResponse({"productos": productos})


@api("GET", acceso=PUBLICO)
def ver_producto(request, producto_id):
    producto = servicios.detalle_producto(producto_id)
    return JsonResponse(serializadores.a_dict(producto))
