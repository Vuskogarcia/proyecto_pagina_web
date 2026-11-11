"""Módulo 7 · Historia 01: un cuerpo mayor a DATA_UPLOAD_MAX_MEMORY_SIZE
responde 413 y no crea nada, en la API y en la web.

Se usa un cliente con CSRF activo y token válido, como un navegador real:
así el rechazo no puede deberse a que falte el token.
"""

import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from carrito.models import Pedido
from catalogo.models import Producto
from comun import fabricas
from cuentas.models import EventoAuditoria
from soporte.models import TicketSoporte


class CuerpoDemasiadoGrandeTests(TestCase):
    def setUp(self):
        self.maximo = settings.DATA_UPLOAD_MAX_MEMORY_SIZE
        self.producto = fabricas.producto(stock=5)
        self.navegador = Client(enforce_csrf_checks=True)
        self.token = self.navegador.get("/api/sesion/").cookies["csrftoken"].value

    def post_api(self, url, datos):
        cuerpo = json.dumps(datos)
        return self.navegador.post(url, data=cuerpo, content_type="application/json",
                                   HTTP_X_CSRFTOKEN=self.token), len(cuerpo.encode())

    def relleno(self, extra=1):
        """Texto que hace que el cuerpo JSON pase el límite por `extra` bytes o más."""
        return "x" * (self.maximo + extra)

    def assertNadaCreado(self, usuarios_antes):
        self.assertFalse(TicketSoporte.objects.exists())
        self.assertFalse(Pedido.objects.exists())
        self.assertEqual(Producto.objects.count(), 1)
        self.assertEqual(get_user_model().objects.count(), usuarios_antes)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 5)

    def test_api_responde_413_en_json_y_no_crea_nada(self):
        cliente = fabricas.cliente()
        usuarios_antes = get_user_model().objects.count()
        casos = [
            ("/api/registro/", {"email": "nuevo@example.com", "clave": "UnaClaveLarga#2026",
                                "nombre": self.relleno()}),
            ("/api/sesion/", {"usuario": self.relleno(), "clave": "x"}),
        ]
        for url, datos in casos:
            with self.subTest(url=url, autenticado=False):
                respuesta, largo = self.post_api(url, datos)
                self.assertGreater(largo, self.maximo)
                self.assertEqual(respuesta.status_code, 413)
                self.assertEqual(respuesta["Content-Type"], "application/json")
                self.assertEqual(respuesta.json(), {"error": "La petición es demasiado grande"})

        self.navegador.force_login(cliente)
        self.token = self.navegador.get("/api/sesion/").cookies["csrftoken"].value
        casos = [
            ("/api/tickets/", {"descripcion": self.relleno()}),
            ("/api/pedidos/", {"items": [{"id_producto": self.producto.pk, "cantidad": 1}],
                               "envio": {**fabricas.ENVIO, "direccion": self.relleno()}}),
        ]
        for url, datos in casos:
            with self.subTest(url=url, autenticado=True):
                respuesta, largo = self.post_api(url, datos)
                self.assertGreater(largo, self.maximo)
                self.assertEqual(respuesta.status_code, 413)

        self.assertNadaCreado(usuarios_antes)
        # No se registró un inicio de sesión ni un registro a medias.
        self.assertFalse(EventoAuditoria.objects.filter(
            tipo__in=[EventoAuditoria.REGISTRO, EventoAuditoria.PEDIDO_CREADO,
                      EventoAuditoria.TICKET_CREADO]).exists())

    def test_admin_tampoco_crea_productos_con_un_cuerpo_gigante(self):
        self.navegador.force_login(fabricas.administrador())
        self.token = self.navegador.get("/api/sesion/").cookies["csrftoken"].value
        respuesta, _ = self.post_api("/api/productos/", {
            "nombre": "Nuevo", "descripcion": self.relleno(), "precio": "1000", "stock": 1})
        self.assertEqual(respuesta.status_code, 413)
        self.assertEqual(Producto.objects.count(), 1)

    def test_web_responde_413_con_pagina_propia_y_no_crea_la_pqr(self):
        cliente = fabricas.cliente()
        self.navegador.force_login(cliente)
        respuesta = self.navegador.post("/pqr/nueva/", {
            "csrfmiddlewaretoken": self.token, "tipo": "PETICION",
            "asunto": "Pedido roto", "descripcion": self.relleno(),
        })
        self.assertEqual(respuesta.status_code, 413)
        self.assertTemplateUsed(respuesta, "413.html")
        self.assertNotIn("RequestDataTooBig", respuesta.content.decode())
        self.assertFalse(TicketSoporte.objects.exists())

    def test_el_limite_es_exacto_un_byte_de_mas_ya_es_413(self):
        self.navegador.force_login(fabricas.cliente())
        self.token = self.navegador.get("/api/sesion/").cookies["csrftoken"].value
        base = json.dumps({"descripcion": ""})
        justo = self.maximo - len(base)  # cuerpo de exactamente `maximo` bytes

        respuesta = self.navegador.post(
            "/api/tickets/", data=json.dumps({"descripcion": "x" * (justo + 1)}),
            content_type="application/json", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(respuesta.status_code, 413)

        # En el límite exacto el cuerpo SÍ se lee: el 400 lo da la regla de
        # negocio (descripción de máximo 5000 caracteres), no el tamaño.
        respuesta = self.navegador.post(
            "/api/tickets/", data=json.dumps({"descripcion": "x" * justo}),
            content_type="application/json", HTTP_X_CSRFTOKEN=self.token)
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(TicketSoporte.objects.exists())

    def test_positivo_un_cuerpo_normal_si_se_acepta(self):
        self.navegador.force_login(fabricas.cliente())
        self.token = self.navegador.get("/api/sesion/").cookies["csrftoken"].value
        respuesta, _ = self.post_api("/api/tickets/", {"descripcion": "d" * 5000})
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(TicketSoporte.objects.count(), 1)
