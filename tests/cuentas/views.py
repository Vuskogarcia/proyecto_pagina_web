"""API de sesión (HU-01). La interfaz web usa los mismos servicios."""

from django.contrib.auth import login, logout
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from comun.http import PUBLICO, api, leer_json
from comun.limites import limite_registro

from . import auditoria
from .models import EventoAuditoria

from . import serializadores, servicios


@ensure_csrf_cookie
@api("GET", "POST", "DELETE", acceso=PUBLICO)
def sesion(request):
    """GET: quién soy (y entrega la cookie CSRF). POST: entrar. DELETE: salir."""
    if request.method == "POST":
        datos = leer_json(request, permitidos=["usuario", "clave"])
        cuenta = servicios.autenticar(
            request, datos.get("usuario"), datos.get("clave"), ip=servicios.ip_de(request)
        )
        login(request, cuenta)  # rota el id de sesión (evita fijación de sesión)
        return JsonResponse(serializadores.a_dict(cuenta))
    if request.method == "DELETE":
        if request.user.is_authenticated:
            auditoria.registrar(EventoAuditoria.LOGOUT, request)
        logout(request)
        return HttpResponse(status=204)
    if not request.user.is_authenticated:
        return JsonResponse({"autenticado": False})
    return JsonResponse({"autenticado": True, **serializadores.a_dict(request.user)})


@api("POST", acceso=PUBLICO)
def registro(request):
    limite_registro(request)
    datos = leer_json(request, permitidos=["email", "clave", "nombre"])
    cuenta = servicios.registrar_cliente(datos.get("email"), datos.get("clave"), datos.get("nombre"))
    return JsonResponse(serializadores.a_dict(cuenta), status=201)
