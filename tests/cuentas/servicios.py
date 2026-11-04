"""Reglas de negocio de cuentas (HU-01): registro e inicio de sesión."""

import hashlib
import logging

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from comun.excepciones import DatosInvalidos, DemasiadosIntentos, NoAutenticado
from comun.validaciones import texto

from . import auditoria
from .models import EventoAuditoria

logger = logging.getLogger("shophub")

MENSAJE_CREDENCIALES = "Usuario o contraseña incorrectos"


def _clave_intentos(usuario, ip):
    # Se guarda un hash: el usuario tal cual podría traer caracteres raros.
    base = f"{(usuario or '').strip().lower()}|{ip or ''}"
    return "login-fallidos:" + hashlib.sha256(base.encode("utf-8", "replace")).hexdigest()


def autenticar(request, usuario, clave, ip=None):
    """Devuelve el usuario si las credenciales son válidas.

    - Mismo mensaje si el usuario no existe o la clave es incorrecta (no se
      revela qué cuentas existen).
    - Tras LOGIN_MAX_INTENTOS fallos seguidos (por usuario + IP) se bloquea
      durante LOGIN_BLOQUEO_SEGUNDOS, aunque luego llegue la clave correcta.
    """
    usuario = texto(usuario, "usuario", maximo=150)
    clave = texto(clave, "clave", maximo=128)
    llave = _clave_intentos(usuario, ip)
    if cache.get(llave, 0) >= settings.LOGIN_MAX_INTENTOS:
        logger.warning("Login bloqueado por intentos: usuario=%r ip=%s", usuario, ip)
        auditoria.registrar(EventoAuditoria.LOGIN_BLOQUEADO, request, usuario_intentado=usuario)
        error = DemasiadosIntentos("Demasiados intentos fallidos. Espera unos minutos.")
        error.auditado = True
        raise error

    cuenta = authenticate(request, username=usuario, password=clave)
    if cuenta is None:
        try:
            cache.incr(llave)
        except ValueError:
            cache.set(llave, 1, settings.LOGIN_BLOQUEO_SEGUNDOS)
        logger.info("Login fallido: usuario=%r ip=%s", usuario, ip)
        auditoria.registrar(EventoAuditoria.LOGIN_FALLIDO, request, usuario_intentado=usuario)
        error = NoAutenticado(MENSAJE_CREDENCIALES)
        error.auditado = True
        raise error

    cache.delete(llave)
    auditoria.registrar(EventoAuditoria.LOGIN_OK, request, usuario=cuenta)
    return cuenta


def registrar_cliente(email, clave, nombre=""):
    """HU-01 criterios 1 y 2: registro con email y contraseña; rol cliente.

    El rol no se elige al registrarse: agente y administrador los asigna un
    administrador desde /admin/.
    """
    email = texto(email, "email", maximo=150).lower()
    try:
        validate_email(email)
    except ValidationError:
        raise DatosInvalidos("El email no es válido")
    nombre = texto(nombre, "nombre", obligatorio=False, maximo=150)
    clave = texto(clave, "clave", maximo=128)

    Usuario = get_user_model()
    if Usuario.objects.filter(username__iexact=email).exists():
        raise DatosInvalidos("Ya existe una cuenta con ese email")
    candidato = Usuario(username=email, email=email, first_name=nombre)
    try:
        validate_password(clave, user=candidato)
    except ValidationError as error:
        raise DatosInvalidos(" ".join(error.messages))
    candidato.set_password(clave)
    candidato.save()
    auditoria.registrar(EventoAuditoria.REGISTRO, usuario=candidato)
    return candidato


def ip_de(request):
    # Sin proxy de confianza configurado, solo se usa REMOTE_ADDR
    # (X-Forwarded-For lo puede falsificar cualquiera).
    return request.META.get("REMOTE_ADDR", "")
