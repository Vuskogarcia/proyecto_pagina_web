"""Middleware propio: límite de tamaño del cuerpo y cabeceras de seguridad."""

import logging

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

logger = logging.getLogger("shophub")


class LimiteDeCuerpoMiddleware:
    """Historia 01 (Módulo 7): un cuerpo mayor a DATA_UPLOAD_MAX_MEMORY_SIZE → 413.

    Sin esto, la API respondía 413 (lo atrapaba `@api`), pero la web
    respondía 400: el middleware de CSRF lee `request.POST` antes de llegar
    a la vista y Django convierte `RequestDataTooBig` en un 400 genérico.
    Aquí se corta antes de leer el cuerpo, con la cabecera Content-Length,
    así nada (sesión, CSRF, vista) llega a procesarlo. La aplicación no
    recibe archivos, así que el límite se aplica a todo cuerpo.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        maximo = settings.DATA_UPLOAD_MAX_MEMORY_SIZE
        try:
            largo = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            largo = 0  # Django trata un Content-Length inválido como 0
        if maximo is not None and largo > maximo:
            logger.warning("Cuerpo demasiado grande (%s bytes) %s %s", largo, request.method, request.path)
            if request.path.startswith("/api/"):
                return JsonResponse({"error": "La petición es demasiado grande"}, status=413)
            return render(request, "413.html", status=413)
        return self.get_response(request)

# La interfaz no usa scripts ni estilos en línea, así que la política puede
# ser estricta: todo sale del mismo origen. Mitiga XSS: aunque un ticket
# trajera <script>, el navegador no lo ejecutaría.
CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=()"


class CabecerasDeSeguridadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        # El admin de Django trae su propio JS; se le deja fuera de la CSP.
        if not request.path.startswith("/admin/"):
            respuesta.setdefault("Content-Security-Policy", CSP)
        respuesta.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        if request.path.startswith("/api/"):
            respuesta.setdefault("Cache-Control", "no-store")
        return respuesta
