"""Módulo 7 · Historia 03: regresión de ReDoS (denegación de servicio por
expresiones regulares).

1. Se envían 50 000 caracteres + "!" a cada campo que se valida con regex
   o con largo máximo. El "!" final obliga a una regex vulnerable a
   retroceder (backtracking) por toda la cadena antes de fallar.
   Se espera 400, nada creado y un tiempo de respuesta acotado.
2. Las regex del propio proyecto se revisan en forma estática: ninguna
   puede tener cuantificadores anidados, como `(a+)+`.
3. Las regex se prueban también directamente (sin el filtro de largo que
   las protege en los servicios), para que la cota no dependa de ese orden.
"""

import ast
import json
import os
import re
import time
from pathlib import Path

from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.test import TestCase

from carrito.models import Pedido
from comun import fabricas
from soporte.models import TicketSoporte

try:  # Python 3.11+
    from re import _constants as sre_constants, _parser as sre_parse
except ImportError:  # pragma: no cover
    import sre_constants
    import sre_parse

DIR_PROYECTO = Path(__file__).resolve().parents[2]
CARGA = "a" * 50_000 + "!"
CARGA_DIGITOS = "1" * 50_000 + "!"  # para el teléfono: dígitos que la regex sí acepta
# Cota holgada para el CI: una regex vulnerable con 50 000 caracteres tarda
# minutos u horas; una petición normal de esta API tarda milisegundos.
COTA_SEGUNDOS = 1.0


def post_json(cliente_http, url, datos):
    return cliente_http.post(url, data=json.dumps(datos), content_type="application/json")


class CargaGiganteEnCamposValidadosTests(TestCase):
    def setUp(self):
        cache.clear()  # el límite de registros por IP no debe interferir
        self.cliente = fabricas.cliente()
        self.producto = fabricas.producto(stock=5)

    def medir(self, peticion):
        inicio = time.perf_counter()
        respuesta = peticion()
        return respuesta, time.perf_counter() - inicio

    def assertRechazoRapido(self, peticion):
        respuesta, segundos = self.medir(peticion)
        self.assertEqual(respuesta.status_code, 400, respuesta.content[:200])
        self.assertLess(segundos, COTA_SEGUNDOS)
        return respuesta

    def test_telefono_de_envio(self):
        self.client.force_login(self.cliente)
        for telefono in (CARGA, CARGA_DIGITOS, "+" + CARGA_DIGITOS):
            with self.subTest(inicio=telefono[:3]):
                self.assertRechazoRapido(lambda: post_json(self.client, "/api/pedidos/", {
                    "items": [{"id_producto": self.producto.pk, "cantidad": 1}],
                    "envio": {**fabricas.ENVIO, "telefono": telefono},
                }))
        self.assertFalse(Pedido.objects.exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 5)

    def test_email_de_registro(self):
        usuarios = get_user_model().objects.count()
        for email in (CARGA, CARGA + "@example.com", "a@" + CARGA):
            with self.subTest(email=email[:5] + "…" + email[-5:]):
                self.assertRechazoRapido(lambda: post_json(self.client, "/api/registro/", {
                    "email": email, "clave": "UnaClaveLarga#2026"}))
        self.assertEqual(get_user_model().objects.count(), usuarios)

    def test_usuario_del_login(self):
        respuesta = self.assertRechazoRapido(
            lambda: post_json(self.client, "/api/sesion/", {"usuario": CARGA, "clave": "x"}))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertIn("usuario", respuesta.json()["error"])

    def test_asunto_y_descripcion_de_la_pqr(self):
        self.client.force_login(self.cliente)
        for campo in ("asunto", "descripcion"):
            with self.subTest(campo=campo):
                datos = {"descripcion": "Llegó roto", campo: CARGA}
                respuesta = self.assertRechazoRapido(
                    lambda: post_json(self.client, "/api/tickets/", datos))
                self.assertIn(campo, respuesta.json()["error"])
        self.assertFalse(TicketSoporte.objects.exists())

    def test_parametro_orden_de_la_cola(self):
        self.client.force_login(fabricas.agente())
        fabricas.ticket(self.cliente)
        self.assertRechazoRapido(lambda: self.client.get("/api/tickets/cola/", {"orden": CARGA}))

    def test_positivo_valores_normales_si_se_aceptan(self):
        self.client.force_login(self.cliente)
        self.assertEqual(post_json(self.client, "/api/tickets/", {
            "asunto": "a" * 200, "descripcion": "d" * 5000}).status_code, 201)
        self.assertEqual(post_json(self.client, "/api/pedidos/", {
            "items": [{"id_producto": self.producto.pk, "cantidad": 1}],
            "envio": fabricas.ENVIO}).status_code, 201)
        agente = fabricas.agente()
        self.client.force_login(agente)
        self.assertEqual(self.client.get("/api/tickets/cola/?orden=recientes").status_code, 200)


# --- Revisión estática de las regex del proyecto ----------------------------

_REPETICIONES = {sre_constants.MAX_REPEAT, sre_constants.MIN_REPEAT}
if hasattr(sre_constants, "POSSESSIVE_REPEAT"):
    _REPETICIONES.add(sre_constants.POSSESSIVE_REPEAT)


def tiene_cuantificador_anidado(patron):
    """True si un cuantificador que repite (máximo > 1) contiene otro."""

    def recorrer(elementos, dentro_de_repeticion):
        for op, arg in elementos:
            if op in _REPETICIONES:
                _minimo, maximo, sub = arg
                repite = maximo is sre_constants.MAXREPEAT or maximo > 1
                if repite and dentro_de_repeticion:
                    return True
                if recorrer(sub, dentro_de_repeticion or repite):
                    return True
            elif op is sre_constants.SUBPATTERN:
                if recorrer(arg[-1], dentro_de_repeticion):
                    return True
            elif op is sre_constants.BRANCH:
                if any(recorrer(rama, dentro_de_repeticion) for rama in arg[1]):
                    return True
            elif op in (sre_constants.ASSERT, sre_constants.ASSERT_NOT):
                if recorrer(arg[1], dentro_de_repeticion):
                    return True
            elif getattr(sre_constants, "ATOMIC_GROUP", None) is op:
                if recorrer(arg, dentro_de_repeticion):
                    return True
        return False

    return recorrer(sre_parse.parse(patron), False)


_FUNCIONES_RE = {"compile", "match", "fullmatch", "search", "sub", "subn", "findall", "finditer", "split"}
_CARPETAS_EXCLUIDAS = {"venv", ".venv", "staticfiles", "__pycache__", "migrations", "pruebas"}


def regex_del_proyecto():
    """(archivo:línea, patrón) de cada regex literal del código del proyecto:
    llamadas re.compile/match/..., atributos `regex = "..."` (convertidores
    de URL) y atributos HTML `"pattern": "..."` de los formularios."""
    encontradas = []
    for raiz, carpetas, archivos in os.walk(DIR_PROYECTO):
        carpetas[:] = [c for c in carpetas if c not in _CARPETAS_EXCLUIDAS]
        for nombre in archivos:
            if not nombre.endswith(".py"):
                continue
            ruta = Path(raiz) / nombre
            arbol = ast.parse(ruta.read_text(encoding="utf-8"))
            donde = lambda nodo: f"{ruta.relative_to(DIR_PROYECTO)}:{nodo.lineno}"  # noqa: E731
            for nodo in ast.walk(arbol):
                if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                        and isinstance(nodo.func.value, ast.Name) and nodo.func.value.id == "re"
                        and nodo.func.attr in _FUNCIONES_RE and nodo.args
                        and isinstance(nodo.args[0], ast.Constant) and isinstance(nodo.args[0].value, str)):
                    encontradas.append((donde(nodo), nodo.args[0].value))
                elif (isinstance(nodo, ast.Assign) and len(nodo.targets) == 1
                        and isinstance(nodo.targets[0], ast.Name) and nodo.targets[0].id == "regex"
                        and isinstance(nodo.value, ast.Constant) and isinstance(nodo.value.value, str)):
                    encontradas.append((donde(nodo), nodo.value.value))
                elif isinstance(nodo, ast.Dict):
                    for clave, valor in zip(nodo.keys, nodo.values):
                        if (isinstance(clave, ast.Constant) and clave.value == "pattern"
                                and isinstance(valor, ast.Constant) and isinstance(valor.value, str)):
                            encontradas.append((donde(valor), valor.value))
    return encontradas


class RegexSinCuantificadoresAnidadosTests(TestCase):
    def test_el_detector_reconoce_patrones_vulnerables_clasicos(self):
        # Controles negativos: si el detector no los marca, la prueba de
        # abajo pasaría sin revisar nada.
        for vulnerable in [r"(a+)+$", r"(a*)*b", r"([a-z]+\s?)*!", r"(\d{1,3}){2,}", r"(?:x|y+)+z"]:
            with self.subTest(patron=vulnerable):
                self.assertTrue(tiene_cuantificador_anidado(vulnerable))
        for seguro in [r"\+?[0-9][0-9 ]{6,19}", r"[0-9]{1,10}(\.[0-9]{1,2})?", r"-?[0-9]{1,19}"]:
            with self.subTest(patron=seguro):
                self.assertFalse(tiene_cuantificador_anidado(seguro))

    def test_ninguna_regex_del_proyecto_tiene_cuantificadores_anidados(self):
        encontradas = regex_del_proyecto()
        # Si esta lista se vacía, la búsqueda dejó de funcionar.
        self.assertGreaterEqual(len(encontradas), 5, encontradas)
        vulnerables = [f"{donde}: {patron}" for donde, patron in encontradas
                       if tiene_cuantificador_anidado(patron)]
        self.assertEqual(vulnerables, [])

    def test_las_regex_del_proyecto_fallan_rapido_con_la_carga(self):
        # Directo sobre la regex, sin el filtro de largo de los servicios.
        for donde, patron in regex_del_proyecto():
            compilada = re.compile(patron)
            for carga in (CARGA, CARGA_DIGITOS, "+" + CARGA_DIGITOS):
                with self.subTest(regex=donde, carga=carga[:2]):
                    inicio = time.perf_counter()
                    compilada.fullmatch(carga)
                    self.assertLess(time.perf_counter() - inicio, COTA_SEGUNDOS)

    def test_el_validador_de_email_de_django_falla_rapido(self):
        # validate_email es de Django (no del proyecto): se mide su tiempo.
        for carga in (CARGA, CARGA + "@example.com", "a@" + CARGA, ("a." * 25_000) + "!@x.co"):
            with self.subTest(carga=carga[:5]):
                inicio = time.perf_counter()
                with self.assertRaises(ValidationError):
                    validate_email(carga)
                self.assertLess(time.perf_counter() - inicio, COTA_SEGUNDOS)
