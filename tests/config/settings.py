"""
Django settings for config project.

La configuración sensible (SECRET_KEY, base de datos, etc.) se lee de
variables de entorno o de un archivo .env (ver .env.example).

Seguro por defecto (ADL-07): DEBUG está apagado salvo que el .env lo
encienda, y no existe SECRET_KEY de respaldo en el código.
"""

import hashlib
import os
import sys
import warnings
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga variables desde tests/.env si existe (ENV_FILE permite usar otro
# archivo; las pruebas de configuración lo apuntan a uno vacío).
load_dotenv(os.getenv("ENV_FILE", BASE_DIR / ".env"))


def _bool(nombre, defecto=False):
    return os.getenv(nombre, str(defecto)).strip().lower() in ("1", "true", "yes", "si", "sí")


DEBUG = _bool("DEBUG", False)

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "Falta SECRET_KEY. Cópiala a tests/.env (ver .env.example) o genera una con: "
        "python -c \"from django.core.management.utils import get_random_secret_key as g; print(g())\""
    )
_CLAVES_DE_EJEMPLO = ("django-insecure", "cambia-esto")
# DT-13 / H12 (Módulo 7, Historia 05): claves que estuvieron en el historial
# de Git. Se consideran comprometidas y quedan revocadas para siempre, con
# o sin DEBUG. Se guarda la huella SHA-256, no la clave, para no volver a
# escribirla en el repositorio. Procedimiento: docs/seguridad/rotacion-secret-key.md
_CLAVES_REVOCADAS_SHA256 = {
    "afed7fff6c98ef00c738422d3ec335a248cbc559be02584d63aaac731e98d5b1",  # commit 1a2b391
    "07537ba1ab9d584aa9d186aaea1259d6e5584c56da2f68814cd2e183bc9fcec2",  # commit 2c19daf
    "096833cf7a974b26f7b5d0e2a3922bb4845e4f8ab236612eddc6dfa3fdacb1a3",  # commit 83705b3
}
if hashlib.sha256(SECRET_KEY.encode("utf-8")).hexdigest() in _CLAVES_REVOCADAS_SHA256:
    raise ImproperlyConfigured(
        "SECRET_KEY revocada: estuvo publicada en el historial de Git (DT-13). "
        "Genera una nueva (ver docs/seguridad/rotacion-secret-key.md)."
    )
if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith(_CLAVES_DE_EJEMPLO)):
    raise ImproperlyConfigured(
        "SECRET_KEY es de ejemplo o muy corta (mínimo 50 caracteres) y DEBUG está apagado."
    )

ALLOWED_HOSTS = [
    h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cuentas",
    "catalogo",
    "carrito",
    "soporte",
    "web",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "comun.middleware.CabecerasDeSeguridadMiddleware",
    "comun.middleware.LimiteDeCuerpoMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "web.contexto.navegacion",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Base de datos
# PostgreSQL es la base de datos del proyecto (ver docker-compose.yml en la
# raíz del repo). DB_ENGINE=sqlite permite correr sin Postgres para pruebas
# rápidas, pero el test de concurrencia de soporte requiere PostgreSQL.
if os.getenv("DB_ENGINE", "postgres").lower() == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "ecommerce_db"),
            "USER": os.getenv("DB_USER", "admin"),
            # Sin contraseña por defecto en el código (DT-09): viene del .env.
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }


# Hash de contraseñas (Módulo 7, Historia 04): Argon2id primero. PBKDF2 se
# conserva después para verificar los hashes que ya existen; Django los
# reemplaza por Argon2id cuando el usuario vuelve a iniciar sesión.
PASSWORD_HASHERS = [
    "comun.hashers.Argon2idPasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]
# Parámetros de Argon2id: segunda configuración recomendada por el RFC 9106
# (t=3, m=64 MiB, p=4). Elegida midiendo tres configuraciones en esta
# aplicación: docs/rendimiento/argon2.md (Historia 10). memory_cost va en KiB.
ARGON2_TIME_COST = int(os.getenv("ARGON2_TIME_COST", "3"))
ARGON2_MEMORY_COST = int(os.getenv("ARGON2_MEMORY_COST", "65536"))
ARGON2_PARALLELISM = int(os.getenv("ARGON2_PARALLELISM", "4"))

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "web:entrar"
LOGIN_REDIRECT_URL = "web:inicio"
LOGOUT_REDIRECT_URL = "web:inicio"


# Seguridad de sesión, cookies y cabeceras
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 8  # una jornada
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "comun.http.fallo_csrf"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
DATA_UPLOAD_MAX_MEMORY_SIZE = 64 * 1024  # la API no recibe cuerpos grandes

# Solo cuando el sitio se sirve por HTTPS (en local con runserver no).
if _bool("HTTPS", False):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = int(os.getenv("HSTS_SECONDS", "3600"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False

# Límite de intentos de inicio de sesión (cuentas/servicios.py).
LOGIN_MAX_INTENTOS = int(os.getenv("LOGIN_MAX_INTENTOS", "5"))
LOGIN_BLOQUEO_SEGUNDOS = int(os.getenv("LOGIN_BLOQUEO_SEGUNDOS", "900"))
# Límite general de peticiones que cambian datos (comun/limites.py).
LIMITE_ESCRITURAS_POR_MINUTO = int(os.getenv("LIMITE_ESCRITURAS_POR_MINUTO", "30"))
LIMITE_REGISTROS_POR_HORA = int(os.getenv("LIMITE_REGISTROS_POR_HORA", "10"))


LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# whitenoise avisa si staticfiles/ aún no existe (antes del primer
# collectstatic, p. ej. en desarrollo o en el CI). No es un error.
warnings.filterwarnings("ignore", message=r"No directory at: .*staticfiles")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Registro (ADL-06): los errores inesperados quedan aquí con su traceback;
# al cliente solo le llega un mensaje genérico. Durante `manage.py test` la
# consola se silencia (las pruebas que revisan el log usan assertLogs).
_EN_PRUEBAS = len(sys.argv) > 1 and sys.argv[1] == "test"

# Solo durante `manage.py test`: Argon2id con costo mínimo para que la suite
# (cientos de usuarios creados) no se vuelva lenta. Sigue siendo Argon2id;
# los parámetros reales se verifican aparte en
# cuentas/pruebas/test_m7_h04_argon2.py (cargando settings fuera de las pruebas).
if _EN_PRUEBAS:
    ARGON2_TIME_COST, ARGON2_MEMORY_COST, ARGON2_PARALLELISM = 1, 1024, 1

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "consola": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "CRITICAL" if _EN_PRUEBAS else "DEBUG",
        },
    },
    "loggers": {
        "shophub": {"handlers": ["consola"], "level": os.getenv("LOG_LEVEL", "INFO"),
                    "propagate": False},
        # Los eventos de auditoría también quedan en la tabla cuentas_eventoauditoria.
        "django.request": {"handlers": ["consola"], "level": "ERROR", "propagate": False},
        "django.security": {"handlers": ["consola"], "level": "WARNING", "propagate": False},
    },
}
