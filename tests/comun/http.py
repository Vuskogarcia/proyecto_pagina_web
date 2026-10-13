"""Utilidades de la frontera HTTP compartidas por todos los módulos."""

import json
from functools import wraps

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .excepciones import DatosInvalidos, ErrorDeNegocio


def api(*metodos):
    """Decorador para las vistas de la API.

    - Restringe los métodos HTTP permitidos (405 si llega otro).
    - Desactiva CSRF: es una API JSON, todavía sin sesiones (ver HU-01).
    - Convierte los errores de negocio en JSON con su código HTTP.
    """

    def decorador(vista):
        @csrf_exempt
        @require_http_methods(list(metodos))
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            try:
                return vista(request, *args, **kwargs)
            except ErrorDeNegocio as error:
                return JsonResponse({"error": str(error)}, status=error.status)

        return envoltura

    return decorador


def leer_json(request):
    """Devuelve el cuerpo de la petición como dict, o lanza DatosInvalidos."""
    try:
        datos = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise DatosInvalidos("El cuerpo de la petición no es JSON válido")
    if not isinstance(datos, dict):
        raise DatosInvalidos("El cuerpo de la petición debe ser un objeto JSON")
    return datos


def entero(valor, campo, obligatorio=True):
    """Convierte `valor` a entero positivo o lanza DatosInvalidos."""
    if valor is None:
        if obligatorio:
            raise DatosInvalidos(f"El campo '{campo}' es obligatorio")
        return None
    if isinstance(valor, bool):
        raise DatosInvalidos(f"El campo '{campo}' debe ser un número entero")
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise DatosInvalidos(f"El campo '{campo}' debe ser un número entero")
    if numero < 1:
        raise DatosInvalidos(f"El campo '{campo}' debe ser mayor que 0")
    return numero
