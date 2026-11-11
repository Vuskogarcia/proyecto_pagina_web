"""Utilidades de la frontera HTTP compartidas por todos los módulos."""

import json
import logging
import sys
import uuid
from functools import wraps

from django.core.exceptions import RequestDataTooBig
from django.http import HttpResponseServerError, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .excepciones import DatosInvalidos, ErrorDeNegocio, NoAutenticado, SinPermiso
from .limites import limite_escritura
from .roles import es_administrador, es_agente
from .validaciones import texto_seguro

logger = logging.getLogger("shophub")

PUBLICO = "publico"
AUTENTICADO = "autenticado"
AGENTE = "agente"
ADMINISTRADOR = "administrador"


def api(*metodos, acceso=AUTENTICADO):
    """Decorador para las vistas de la API.

    - Restringe los métodos HTTP permitidos (405 si llega otro).
    - Exige sesión (401) y, si `acceso=AGENTE`, el rol de agente (403).
      La identidad sale siempre de la sesión, nunca del cuerpo (ADL-01).
    - CSRF activo: con sesiones, los POST deben traer el token (H13).
    - Convierte los errores de negocio en JSON con su código HTTP.
    - Red genérica (ADL-06): cualquier otra excepción se registra con su
      traceback en el log "shophub" y al cliente le llega un 500 genérico.
    - Límite de escrituras por usuario (429) y auditoría de accesos denegados
      y errores internos en la tabla de eventos (guía semana 13, §4 y §5).
    """

    def decorador(vista):
        @require_http_methods(list(metodos))
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            try:
                if acceso != PUBLICO and not request.user.is_authenticated:
                    raise NoAutenticado("Debes iniciar sesión")
                if acceso == AGENTE and not es_agente(request.user):
                    raise SinPermiso("Solo un agente de soporte puede hacer esto")
                if acceso == ADMINISTRADOR and not es_administrador(request.user):
                    raise SinPermiso("Solo un administrador puede hacer esto")
                if request.method != "GET" and request.user.is_authenticated:
                    limite_escritura(request)
                return vista(request, *args, **kwargs)
            except ErrorDeNegocio as error:
                if error.status in (401, 403, 429):
                    logger.warning(
                        "Acceso rechazado (%s) %s %s usuario=%s",
                        error.status, request.method, request.path, _quien(request),
                    )
                    if not getattr(error, "auditado", False):
                        _auditar(
                            "LIMITE_EXCEDIDO" if error.status == 429 else "ACCESO_DENEGADO",
                            request, f"{error.status} {request.method}: {error}",
                        )
                return JsonResponse({"error": str(error)}, status=error.status)
            except RequestDataTooBig:
                return JsonResponse({"error": "La petición es demasiado grande"}, status=413)
            except Exception:
                return _respuesta_500(request, sys.exc_info())

        return envoltura

    return decorador


MENSAJE_500 = "Error interno del servidor"


def _respuesta_500(request, exc_info):
    """Historia 06 (Módulo 7): todo 500 lleva un identificador de seguimiento.

    El mismo UUID va en la respuesta (campo `id_error` y cabecera
    `X-Error-Id`), en el log `shophub` junto al traceback y en la auditoría.
    Así soporte puede encontrar el error exacto con lo que ve el usuario,
    sin que la respuesta revele nada interno.
    """
    id_error = str(uuid.uuid4())
    logger.error(
        "Error inesperado id_error=%s en %s %s usuario=%s",
        id_error, request.method, request.path, _quien(request), exc_info=exc_info,
    )
    _auditar("ERROR_INTERNO", request, f"{request.method} id_error={id_error} (detalle en el log)")
    if request.path.startswith("/api/"):
        respuesta = JsonResponse({"error": MENSAJE_500, "id_error": id_error}, status=500)
    else:
        try:
            respuesta = render(request, "500.html", {"id_error": id_error}, status=500)
        except Exception:  # si la plantilla también falla, una respuesta mínima
            logger.exception("No se pudo mostrar 500.html id_error=%s", id_error)
            respuesta = HttpResponseServerError(
                f"Error interno del servidor. Código de seguimiento: {id_error}",
                content_type="text/plain; charset=utf-8",
            )
    respuesta["X-Error-Id"] = id_error
    return respuesta


def error_500(request):
    """handler500 de Django (config/urls.py) para todo lo que no pasa por `@api`.

    Django lo llama dentro del `except` que atrapó la excepción, así que
    `sys.exc_info()` todavía tiene el traceback original.
    """
    return _respuesta_500(request, sys.exc_info())


def _auditar(tipo, request, detalle=""):
    from cuentas.auditoria import registrar  # import tardío: comun no depende de cuentas al cargar

    registrar(tipo, request=request, detalle=detalle)


def _quien(request):
    usuario = getattr(request, "user", None)
    return usuario.pk if usuario is not None and usuario.is_authenticated else "anonimo"


def leer_json(request, permitidos=None):
    """Devuelve el cuerpo de la petición como dict, o lanza DatosInvalidos.

    - `permitidos`: lista de campos aceptados; cualquier otro campo es un 400
      (ADL-04). Así un `id_cliente` en el cuerpo ya no se ignora en silencio.
    - Todo texto del cuerpo (claves y valores, a cualquier profundidad) se
      valida contra NUL y surrogates sueltos (ADL-05).
    """
    try:
        datos = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise DatosInvalidos("El cuerpo de la petición no es JSON válido")
    if not isinstance(datos, dict):
        raise DatosInvalidos("El cuerpo de la petición debe ser un objeto JSON")
    _revisar_textos(datos)
    if permitidos is not None:
        sobrantes = sorted(set(datos) - set(permitidos))
        if sobrantes:
            raise DatosInvalidos(f"Campos no permitidos: {', '.join(sobrantes)}")
    return datos


def _revisar_textos(valor, profundidad=0):
    if profundidad > 10:
        raise DatosInvalidos("El cuerpo de la petición está demasiado anidado")
    if isinstance(valor, str):
        texto_seguro(valor)
    elif isinstance(valor, dict):
        for clave, contenido in valor.items():
            texto_seguro(clave)
            _revisar_textos(contenido, profundidad + 1)
    elif isinstance(valor, list):
        for contenido in valor:
            _revisar_textos(contenido, profundidad + 1)


def fallo_csrf(request, reason=""):
    """CSRF_FAILURE_VIEW: JSON para la API, página amable para la web."""
    logger.warning("CSRF rechazado %s %s: %s", request.method, request.path, reason)
    _auditar("CSRF_RECHAZADO", request, f"{request.method}: {reason}")
    if request.path.startswith("/api/"):
        return JsonResponse(
            {"error": "Falta el token CSRF o no es válido. Pide GET /api/sesion/ y envíalo "
                      "en la cabecera X-CSRFToken."},
            status=403,
        )
    return render(request, "403_csrf.html", status=403)
