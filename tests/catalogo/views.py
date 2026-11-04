"""Controlador HTTP del catálogo. No decide nada: llama al servicio.

- GET es público (HU-02).
- POST / PATCH y la lista completa son solo para administradores (HU-03).
"""

from django.http import JsonResponse

from comun.excepciones import NoAutenticado, SinPermiso
from comun.http import ADMINISTRADOR, PUBLICO, api, leer_json
from comun.roles import es_administrador

from . import serializadores, servicios


def _solo_administrador(request):
    if not request.user.is_authenticated:
        raise NoAutenticado("Debes iniciar sesión")
    if not es_administrador(request.user):
        raise SinPermiso("Solo un administrador puede gestionar el catálogo")


@api("GET", "POST", acceso=PUBLICO)
def listar_productos(request):
    """GET: catálogo público. POST: crear producto (administrador)."""
    if request.method == "POST":
        _solo_administrador(request)
        datos = leer_json(request, permitidos=servicios.CAMPOS_EDITABLES)
        producto = servicios.crear_producto(request.user, datos)
        return JsonResponse(serializadores.a_dict_admin(producto), status=201)
    productos = [serializadores.a_dict(p) for p in servicios.listar_catalogo()]
    return JsonResponse({"productos": productos})


@api("GET", "PATCH", acceso=PUBLICO)
def ver_producto(request, producto_id):
    """GET: detalle público. PATCH: modificar o desactivar (administrador)."""
    if request.method == "PATCH":
        _solo_administrador(request)
        datos = leer_json(request, permitidos=servicios.CAMPOS_EDITABLES)
        producto = servicios.actualizar_producto(request.user, producto_id, datos)
        return JsonResponse(serializadores.a_dict_admin(producto))
    producto = servicios.detalle_producto(producto_id)
    return JsonResponse(serializadores.a_dict(producto))


@api("GET", acceso=ADMINISTRADOR)
def gestion_productos(request):
    """Todos los productos, incluidos los desactivados (HU-03)."""
    productos = [serializadores.a_dict_admin(p) for p in servicios.listar_todos(request.user)]
    return JsonResponse({"productos": productos})
