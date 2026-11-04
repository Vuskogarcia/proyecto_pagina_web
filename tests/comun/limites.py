"""Límite de peticiones (guía §5: disponibilidad → rate limiting).

Ventana fija por minuto/hora guardada en la caché. Clave: usuario en sesión
o, si es anónimo, la IP. Como el límite de login, usa la caché local del
proceso; con varios procesos hay que usar una caché compartida (DT-12).
"""

import time

from django.conf import settings
from django.core.cache import cache

from .excepciones import DemasiadosIntentos


def _quien(request):
    usuario = getattr(request, "user", None)
    if usuario is not None and usuario.is_authenticated:
        return f"u{usuario.pk}"
    return f"ip{request.META.get('REMOTE_ADDR', '')}"


def verificar_limite(request, alcance, maximo, ventana_segundos):
    """Cuenta la petición y lanza DemasiadosIntentos (429) si supera `maximo`."""
    ventana = int(time.time() // ventana_segundos)
    llave = f"limite:{alcance}:{_quien(request)}:{ventana}"
    cache.add(llave, 0, ventana_segundos + 5)
    try:
        cuenta = cache.incr(llave)
    except ValueError:  # la llave expiró entre add e incr
        cache.set(llave, 1, ventana_segundos + 5)
        cuenta = 1
    if cuenta > maximo:
        raise DemasiadosIntentos("Demasiadas peticiones. Espera un momento e inténtalo de nuevo.")


def limite_escritura(request):
    verificar_limite(request, "escritura", settings.LIMITE_ESCRITURAS_POR_MINUTO, 60)


def limite_registro(request):
    verificar_limite(request, "registro", settings.LIMITE_REGISTROS_POR_HORA, 3600)
