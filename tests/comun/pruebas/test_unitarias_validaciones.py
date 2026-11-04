"""Pruebas unitarias de comun/: validaciones y lectura de JSON.

Unitarias: no tocan la base de datos ni el servidor HTTP (SimpleTestCase).
Cada prueba ejercita una sola función con una sola entrada."""

from django.test import RequestFactory, SimpleTestCase

from comun.excepciones import DatosInvalidos, EstadoInvalido, NoEncontrado, SinPermiso
from comun.http import leer_json
from comun.validaciones import entero


class EnteroTests(SimpleTestCase):
    def test_convierte_numeros_y_textos_numericos(self):
        self.assertEqual(entero(5, "x"), 5)
        self.assertEqual(entero("7", "x"), 7)

    def test_obligatorio_ausente_lanza_datos_invalidos(self):
        with self.assertRaisesMessage(DatosInvalidos, "El campo 'id_cliente' es obligatorio"):
            entero(None, "id_cliente")

    def test_opcional_ausente_devuelve_none(self):
        self.assertIsNone(entero(None, "id_pedido", obligatorio=False))

    def test_rechaza_valores_no_enteros(self):
        # Caso borde: True es int en Python, pero no es un id válido.
        for valor in ["abc", "1.5", [], {}, True, False]:
            with self.subTest(valor=valor):
                with self.assertRaises(DatosInvalidos):
                    entero(valor, "x")

    def test_rechaza_cero_y_negativos(self):
        for valor in [0, -1, "-3"]:
            with self.subTest(valor=valor):
                with self.assertRaisesMessage(DatosInvalidos, "debe ser mayor que 0"):
                    entero(valor, "x")


class LeerJsonTests(SimpleTestCase):
    def setUp(self):
        self.fabrica = RequestFactory()

    def peticion(self, cuerpo):
        return self.fabrica.post("/", data=cuerpo, content_type="application/json")

    def test_devuelve_el_objeto_json(self):
        self.assertEqual(leer_json(self.peticion('{"a": 1}')), {"a": 1})

    def test_cuerpo_vacio_es_un_objeto_vacio(self):
        self.assertEqual(leer_json(self.peticion("")), {})

    def test_json_mal_formado_lanza_datos_invalidos(self):
        with self.assertRaises(DatosInvalidos):
            leer_json(self.peticion("{no es json"))

    def test_json_que_no_es_objeto_lanza_datos_invalidos(self):
        for cuerpo in ["[1, 2]", '"texto"', "42"]:
            with self.subTest(cuerpo=cuerpo):
                with self.assertRaises(DatosInvalidos):
                    leer_json(self.peticion(cuerpo))


class ExcepcionesTests(SimpleTestCase):
    def test_cada_error_lleva_su_codigo_http(self):
        self.assertEqual(DatosInvalidos.status, 400)
        self.assertEqual(SinPermiso.status, 403)
        self.assertEqual(NoEncontrado.status, 404)
        self.assertEqual(EstadoInvalido.status, 409)
