"""Módulo 7 · Historia 06: identificador de seguimiento en los errores 500.

- La respuesta (API y web) trae un UUID de seguimiento.
- El mismo UUID aparece en el log `shophub` junto al traceback, y en la auditoría.
- La respuesta no filtra nada interno (mensaje de la excepción, traceback,
  rutas de archivos, tipo de excepción, configuración).
"""

import re
import uuid
from unittest import mock

from django.test import Client, TestCase

from comun import fabricas
from cuentas.models import EventoAuditoria

SECRETO = "detalle-interno-secreto password=adminpassword C:\\srv\\shophub\\config\\settings.py"
FILTRACION = re.compile(
    r"detalle-interno-secreto|adminpassword|Traceback|File \"|settings\.py|RuntimeError|"
    r"SECRET_KEY|DATABASES|psycopg2|django\.|\\srv\\", re.IGNORECASE)


class IdDeSeguimientoTests(TestCase):
    def setUp(self):
        # El cliente de pruebas relanza las excepciones por defecto; aquí se
        # quiere ver la respuesta 500 real que recibe un navegador.
        self.navegador = Client(raise_request_exception=False)

    def provocar_500(self, url, servicio):
        with mock.patch(servicio, side_effect=RuntimeError(SECRETO)), \
                self.assertLogs("shophub", level="ERROR") as log:
            respuesta = self.navegador.get(url)
        self.assertEqual(respuesta.status_code, 500)
        return respuesta, "\n".join(log.output)

    def assertIdEnElLog(self, id_error, log):
        self.assertEqual(str(uuid.UUID(id_error)), id_error)  # es un UUID válido
        # En el log: el id, el traceback y el detalle real, en el mismo registro.
        registro = next(r for r in log.split("ERROR:shophub:") if id_error in r)
        self.assertIn("Traceback", registro)
        self.assertIn("RuntimeError", registro)
        self.assertIn("detalle-interno-secreto", registro)
        evento = EventoAuditoria.objects.get(tipo=EventoAuditoria.ERROR_INTERNO)
        self.assertIn(id_error, evento.detalle)
        self.assertNotIn("detalle-interno-secreto", evento.detalle)

    def test_api_el_500_trae_el_id_y_el_mismo_id_queda_en_el_log(self):
        respuesta, log = self.provocar_500("/api/productos/", "catalogo.servicios.listar_catalogo")
        cuerpo = respuesta.json()
        self.assertEqual(set(cuerpo), {"error", "id_error"})
        self.assertEqual(cuerpo["error"], "Error interno del servidor")
        self.assertEqual(respuesta["X-Error-Id"], cuerpo["id_error"])
        self.assertIdEnElLog(cuerpo["id_error"], log)
        self.assertNotRegex(respuesta.content.decode(), FILTRACION)

    def test_web_el_500_muestra_el_id_con_la_pagina_propia(self):
        respuesta, log = self.provocar_500("/", "catalogo.servicios.listar_catalogo")
        html = respuesta.content.decode()
        id_error = respuesta["X-Error-Id"]
        self.assertTemplateUsed(respuesta, "500.html")
        self.assertIn(id_error, html)
        self.assertIdEnElLog(id_error, log)
        self.assertNotRegex(html, FILTRACION)

    def test_web_autenticada_tambien_lleva_id(self):
        cliente = fabricas.cliente()
        self.navegador.force_login(cliente)
        respuesta, log = self.provocar_500("/pedidos/", "carrito.servicios.pedidos_de")
        self.assertIn(respuesta["X-Error-Id"], respuesta.content.decode())
        self.assertIn(f"usuario={cliente.pk}", log)

    def test_cada_error_tiene_su_propio_id(self):
        primero, _ = self.provocar_500("/api/productos/", "catalogo.servicios.listar_catalogo")
        segundo, _ = self.provocar_500("/api/productos/", "catalogo.servicios.listar_catalogo")
        self.assertNotEqual(primero.json()["id_error"], segundo.json()["id_error"])

    def test_si_la_plantilla_500_falla_igual_responde_con_el_id_y_sin_detalles(self):
        with mock.patch("comun.http.render", side_effect=RuntimeError("plantilla rota")):
            respuesta, log = self.provocar_500("/", "catalogo.servicios.listar_catalogo")
        id_error = respuesta["X-Error-Id"]
        self.assertIn(id_error, respuesta.content.decode())
        self.assertNotRegex(respuesta.content.decode(), FILTRACION)
        self.assertIn(id_error, log)

    def test_positivo_las_respuestas_normales_no_llevan_id(self):
        self.assertEqual(self.navegador.get("/api/productos/").status_code, 200)
        self.assertNotIn("X-Error-Id", self.navegador.get("/api/productos/"))
        respuesta = self.navegador.get("/api/productos/999/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertNotIn("id_error", respuesta.json())
