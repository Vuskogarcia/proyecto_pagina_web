"""Módulo 7 · Historia 04: contraseñas con Argon2id.

- El hash guardado es Argon2id (prefijo `argon2$argon2id$`).
- La misma clave produce hashes distintos (sal aleatoria).
- check_password acepta la correcta y rechaza la incorrecta.
- La clave nunca queda en texto plano (usuario, auditoría ni log).
- Un hash PBKDF2 existente sigue sirviendo y pasa a Argon2id al iniciar sesión.
- Los parámetros de producción son los documentados (se cargan los
  settings en otro proceso: dentro de `manage.py test` el costo es mínimo
  para no volver lenta la suite).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, identify_hasher, make_password
from django.core.cache import cache
from django.test import TestCase

from cuentas.models import EventoAuditoria

DIR_PROYECTO = Path(__file__).resolve().parents[2]
CLAVE = "Clave-Segura#2026"


def post_json(cliente_http, url, datos):
    return cliente_http.post(url, data=json.dumps(datos), content_type="application/json")


class Argon2idTests(TestCase):
    def setUp(self):
        cache.clear()

    def registrar(self, email, clave=CLAVE):
        respuesta = post_json(self.client, "/api/registro/", {"email": email, "clave": clave})
        self.assertEqual(respuesta.status_code, 201, respuesta.content)
        return get_user_model().objects.get(username=email)

    def test_el_registro_guarda_un_hash_argon2id(self):
        usuario = self.registrar("ana@example.com")
        self.assertTrue(usuario.password.startswith("argon2$argon2id$"), usuario.password[:20])
        self.assertEqual(identify_hasher(usuario.password).algorithm, "argon2")

    def test_la_misma_clave_da_dos_hashes_distintos(self):
        uno = self.registrar("uno@example.com").password
        dos = self.registrar("dos@example.com").password
        self.assertNotEqual(uno, dos)
        # Formato: argon2$argon2id$v=19$m=…,t=…,p=…$<sal>$<hash>. Variante y
        # parámetros iguales; la sal (y por eso el hash) cambia.
        self.assertEqual(uno.split("$")[:4], dos.split("$")[:4])
        self.assertNotEqual(uno.split("$")[4], dos.split("$")[4])
        self.assertNotEqual(uno.split("$")[5], dos.split("$")[5])

    def test_check_password_acepta_la_correcta_y_rechaza_la_incorrecta(self):
        usuario = self.registrar("ana@example.com")
        self.assertTrue(check_password(CLAVE, usuario.password))
        self.assertTrue(usuario.check_password(CLAVE))
        for incorrecta in ["", "clave-segura#2026", CLAVE + " ", CLAVE[:-1]]:
            with self.subTest(incorrecta=incorrecta):
                self.assertFalse(check_password(incorrecta, usuario.password))
        # Y por la API: la correcta entra, la incorrecta no.
        self.assertEqual(post_json(self.client, "/api/sesion/",
                                   {"usuario": "ana@example.com", "clave": "otra-cosa"}).status_code, 401)
        self.assertEqual(post_json(self.client, "/api/sesion/",
                                   {"usuario": "ana@example.com", "clave": CLAVE}).status_code, 200)

    def test_la_clave_nunca_queda_en_texto_plano(self):
        with self.assertLogs("shophub", level="INFO") as log:
            self.registrar("ana@example.com")
            post_json(self.client, "/api/sesion/", {"usuario": "ana@example.com", "clave": "mala-" + CLAVE})
            post_json(self.client, "/api/sesion/", {"usuario": "ana@example.com", "clave": CLAVE})
        # Ni en la fila del usuario, ni en la auditoría, ni en el log.
        guardadas = list(get_user_model().objects.values_list("password", flat=True))
        self.assertTrue(guardadas)
        for guardada in guardadas:
            self.assertNotIn(CLAVE, guardada)
        for evento in EventoAuditoria.objects.all():
            self.assertNotIn(CLAVE, f"{evento.detalle} {evento.usuario_intentado}")
        self.assertNotIn(CLAVE, "\n".join(log.output))

    def test_un_hash_pbkdf2_existente_sirve_y_se_actualiza_a_argon2id_al_entrar(self):
        Usuario = get_user_model()
        viejo = Usuario.objects.create(username="viejo@example.com",
                                       password=make_password(CLAVE, hasher="pbkdf2_sha256"))
        self.assertTrue(viejo.password.startswith("pbkdf2_sha256$"))

        # Una clave incorrecta no entra ni toca el hash.
        self.assertEqual(post_json(self.client, "/api/sesion/",
                                   {"usuario": "viejo@example.com", "clave": "incorrecta"}).status_code, 401)
        viejo.refresh_from_db()
        self.assertTrue(viejo.password.startswith("pbkdf2_sha256$"))

        # La correcta entra y Django reemplaza el hash por Argon2id.
        self.assertEqual(post_json(self.client, "/api/sesion/",
                                   {"usuario": "viejo@example.com", "clave": CLAVE}).status_code, 200)
        viejo.refresh_from_db()
        self.assertTrue(viejo.password.startswith("argon2$argon2id$"))
        self.assertTrue(viejo.check_password(CLAVE))


class ParametrosDeProduccionTests(TestCase):
    """Fuera de `manage.py test` se usan los parámetros reales (no los mínimos)."""

    SCRIPT = (
        "import django, json; django.setup();"
        "from django.conf import settings;"
        "from django.contrib.auth.hashers import get_hasher, make_password;"
        "h = get_hasher('default'); c = make_password('x');"
        "print(json.dumps({'hashers': settings.PASSWORD_HASHERS, 'algoritmo': h.algorithm,"
        " 't': h.time_cost, 'm': h.memory_cost, 'p': h.parallelism, 'hash': c[:40]}))"
    )

    def cargar(self, **variables):
        entorno = {k: v for k, v in os.environ.items() if not k.startswith(("ARGON2_", "DEBUG"))}
        entorno.update(variables, ENV_FILE=os.devnull, DJANGO_SETTINGS_MODULE="config.settings",
                       SECRET_KEY="k" * 60, DEBUG="False")
        resultado = subprocess.run([sys.executable, "-c", self.SCRIPT], cwd=DIR_PROYECTO, env=entorno,
                                   capture_output=True, text=True)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        return json.loads(resultado.stdout)

    def test_argon2id_primero_y_pbkdf2_despues_con_los_parametros_documentados(self):
        datos = self.cargar()
        self.assertEqual(datos["hashers"][0], "comun.hashers.Argon2idPasswordHasher")
        self.assertIn("django.contrib.auth.hashers.PBKDF2PasswordHasher", datos["hashers"][1:])
        self.assertEqual(datos["algoritmo"], "argon2")
        # Valores elegidos en docs/rendimiento/argon2.md (Historia 10).
        self.assertEqual((datos["t"], datos["m"], datos["p"]), (2, 102400, 8))
        self.assertTrue(datos["hash"].startswith("argon2$argon2id$v=19$m=102400,t=2,p=8$"))

    def test_los_parametros_se_pueden_ajustar_por_entorno(self):
        datos = self.cargar(ARGON2_TIME_COST="3", ARGON2_MEMORY_COST="19456", ARGON2_PARALLELISM="1")
        self.assertTrue(datos["hash"].startswith("argon2$argon2id$v=19$m=19456,t=3,p=1$"))
