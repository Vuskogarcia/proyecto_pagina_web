"""Datos que todas las plantillas necesitan: rol del usuario y carrito."""

from carrito import carrito_sesion
from comun import roles


def navegacion(request):
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {"rol": None, "unidades_carrito": 0}
    return {
        "rol": roles.rol(usuario),
        "es_agente": roles.es_agente(usuario),
        "unidades_carrito": carrito_sesion.unidades(request.session),
    }
