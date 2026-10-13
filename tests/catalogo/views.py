"""Controlador HTTP del catálogo. No decide nada: llama al servicio."""

from django.http import JsonResponse

from comun.http import api

from . import servicios


@api("GET")
def listar_productos(request):
    productos = [servicios.a_dict(p) for p in servicios.listar_catalogo()]
    return JsonResponse({"productos": productos})


@api("GET")
def ver_producto(request, producto_id):
    producto = servicios.detalle_producto(producto_id)
    return JsonResponse(servicios.a_dict(producto))
