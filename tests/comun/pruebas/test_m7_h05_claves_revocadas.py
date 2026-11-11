"""Módulo 7 · Historia 05: las SECRET_KEY que quedaron en el historial de
Git (H12, DT-13) son rechazadas.

Las claves no se copian a este archivo (sería volver a publicarlas): se leen
del propio historial de Git en el momento de la prueba, con la misma regex
que usa gitleaks (.gitleaks.toml). Por eso el CI hace checkout con todo el
historial (fetch-depth: 0). Si el historial no está disponible, la prueba
se salta y lo dice, en vez de pasar sin revisar nada.
"""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

from config import settings as configuracion

DIR_PROYECTO = Path(__file__).resolve().parents[2]
REGEX_GITLEAKS = re.compile(r"django-insecure-[A-Za-z0-9!@#$%^&*()_+=\-]{30,}")


def claves_del_historial():
    """Claves django-insecure agregadas en cualquier commit del historial."""
    try:
        superficial = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=DIR_PROYECTO, capture_output=True, text=True, check=True,
        ).stdout.strip()
        if superficial == "true":
            return None
        salida = subprocess.run(
            ["git", "log", "--all", "-p", "--format=", "-S", "django-insecure"],
            cwd=DIR_PROYECTO, capture_output=True, check=True,
        ).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.CalledProcessError):
        return None
    claves = set()
    for linea in salida.splitlines():
        if linea.startswith("+") and not linea.startswith("+++"):
            claves.update(REGEX_GITLEAKS.findall(linea))
    return claves


class ClavesHistoricasRevocadasTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.claves = claves_del_historial()

    def setUp(self):
        if self.claves is None:
            self.skipTest("Sin historial completo de Git (clon superficial o sin git): "
                          "no se pueden leer las claves históricas.")

    def cargar_settings(self, clave, debug):
        entorno = {k: v for k, v in os.environ.items() if k not in ("DEBUG", "SECRET_KEY")}
        entorno.update(ENV_FILE=os.devnull, DJANGO_SETTINGS_MODULE="config.settings",
                       SECRET_KEY=clave, DEBUG=debug)
        return subprocess.run(
            [sys.executable, "-c", "from django.conf import settings; settings.DEBUG"],
            cwd=DIR_PROYECTO, env=entorno, capture_output=True, text=True,
        )

    def test_el_historial_tiene_las_tres_claves_conocidas(self):
        # Si esto falla con menos claves, la extracción dejó de funcionar;
        # con más, apareció una clave nueva en el historial.
        self.assertEqual(len(self.claves), 3)

    def test_cada_clave_historica_esta_en_la_lista_de_revocadas(self):
        huellas = {hashlib.sha256(c.encode("utf-8")).hexdigest() for c in self.claves}
        self.assertEqual(huellas - configuracion._CLAVES_REVOCADAS_SHA256, set())

    def test_las_claves_historicas_se_rechazan_con_debug_false(self):
        for numero, clave in enumerate(sorted(self.claves), start=1):
            with self.subTest(clave=f"histórica #{numero}"):  # sin mostrar la clave
                resultado = self.cargar_settings(clave, debug="False")
                self.assertNotEqual(resultado.returncode, 0)
                self.assertIn("SECRET_KEY revocada", resultado.stderr)
                self.assertNotIn(clave, resultado.stderr)  # el error no la repite

    def test_tambien_se_rechazan_con_debug_true(self):
        # Revocada es revocada: ni siquiera en desarrollo.
        for clave in self.claves:
            resultado = self.cargar_settings(clave, debug="True")
            self.assertNotEqual(resultado.returncode, 0)
            self.assertIn("SECRET_KEY revocada", resultado.stderr)

    def test_positivo_una_clave_nueva_si_arranca(self):
        resultado = self.cargar_settings("n" * 60, debug="False")
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
