"""Registro de eventos críticos (guía semana 13, §4 «Registro de eventos críticos»).

`registrar()` nunca rompe la operación principal: si el registro falla, se
anota en el log y la petición sigue. Cada evento se guarda en su propio
savepoint para no afectar la transacción de quien lo llama.
"""

import ipaddress
import logging

from django.db import transaction

from .models import EventoAuditoria

logger = logging.getLogger("shophub.auditoria")


def _ip(request):
    valor = (request.META.get("REMOTE_ADDR") or "") if request is not None else ""
    try:
        return str(ipaddress.ip_address(valor))
    except ValueError:
        return None


def registrar(tipo, request=None, usuario=None, detalle="", usuario_intentado=""):
    if usuario is None and request is not None:
        actual = getattr(request, "user", None)
        if actual is not None and actual.is_authenticated:
            usuario = actual
    datos = {
        "tipo": tipo,
        "usuario": usuario,
        "usuario_intentado": str(usuario_intentado or "")[:150],
        "ip": _ip(request),
        "ruta": (request.path if request is not None else "")[:200],
        "detalle": str(detalle or "")[:500],
    }
    logger.info("%s usuario=%s ip=%s ruta=%s %s", tipo,
                getattr(usuario, "pk", None) or datos["usuario_intentado"] or "-",
                datos["ip"], datos["ruta"], datos["detalle"])
    try:
        with transaction.atomic():
            EventoAuditoria.objects.create(**datos)
    except Exception:  # el registro nunca debe tumbar la operación
        logger.exception("No se pudo guardar el evento de auditoría %s", tipo)
