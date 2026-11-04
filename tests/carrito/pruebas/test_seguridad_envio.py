"""Seguridad de los datos de envío (HU-04 criterio 3).

La dirección y el teléfono son datos personales: se validan como cualquier
entrada no confiable y solo los ven el dueño del pedido y los agentes."""

import json

from django.test import TestCase

from carrito.models import Pedido
from comun import fabricas
from cuentas.models import EventoAuditoria

XSS = "<script>alert(1)</script>"
SQLI = "' OR 1=1 --"


class ValidacionDelEnvioTests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente()
        self.producto = fabricas.producto(stock=10)
        self.client.force_login(self.cliente)

    def checkout(self, envio):
        cuerpo = {"items": [{"id_producto": self.producto.pk, "cantidad": 1}], "envio": envio}
        return self.client.post("/api/pedidos/", data=json.dumps(cuerpo), content_type="application/json")

    def test_envio_mal_formado_responde_400_y_no_crea_pedido_ni_descuenta_stock(self):
        invalidos = {
            "no es objeto": "Calle 10",
            "falta un campo": {k: v for k, v in fabricas.ENVIO.items() if k != "ciudad"},
            "campo extra (asignación masiva)": {**fabricas.ENVIO, "costo_envio": 0},
            "NUL en la dirección": {**fabricas.ENVIO, "direccion": "Calle\x0010"},
            "dirección de 201 caracteres": {**fabricas.ENVIO, "direccion": "x" * 201},
            "teléfono con letras": {**fabricas.ENVIO, "telefono": "300-ABC-1234"},
            "teléfono muy corto": {**fabricas.ENVIO, "telefono": "12345"},
            "teléfono con dígitos no ASCII": {**fabricas.ENVIO, "telefono": "٣٠٠١٢٣٤٥٦٧"},
            "teléfono numérico (no texto)": {**fabricas.ENVIO, "telefono": 3001234567},
        }
        for caso, envio in invalidos.items():
            with self.subTest(caso=caso):
                self.assertEqual(self.checkout(envio).status_code, 400)
        self.assertFalse(Pedido.objects.exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_positivo_xss_y_sqli_se_guardan_como_texto_y_se_muestran_escapados(self):
        respuesta = self.checkout({**fabricas.ENVIO, "nombre": XSS, "direccion": SQLI})
        self.assertEqual(respuesta.status_code, 201)
        pedido = Pedido.objects.get()
        self.assertEqual((pedido.envio_nombre, pedido.envio_direccion), (XSS, SQLI))

        html = self.client.get(f"/pedidos/{pedido.pk}/").content.decode()
        self.assertNotIn(XSS, html)
        self.assertIn("&lt;script&gt;", html)


class PrivacidadDelEnvioTests(TestCase):
    def setUp(self):
        self.duenio = fabricas.cliente("duenio")
        self.pedido = fabricas.pedido(self.duenio, [(fabricas.producto(), 1)])

    def test_un_intruso_no_ve_la_direccion_ni_por_api_ni_por_web(self):
        self.client.force_login(fabricas.cliente("intruso"))
        for url in (f"/api/pedidos/{self.pedido.pk}/", f"/pedidos/{self.pedido.pk}/"):
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 404)
                self.assertNotIn(fabricas.ENVIO["direccion"], respuesta.content.decode())
        self.assertEqual(self.client.get("/api/pedidos/").json(), {"pedidos": []})

    def test_positivo_el_duenio_y_el_agente_si_ven_el_envio(self):
        for usuario in (self.duenio, fabricas.agente()):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                envio = self.client.get(f"/api/pedidos/{self.pedido.pk}/").json()["envio"]
                self.assertEqual(envio, fabricas.ENVIO)

    def test_el_registro_de_auditoria_no_guarda_la_direccion_ni_el_telefono(self):
        self.client.force_login(self.duenio)
        cuerpo = {"items": [{"id_producto": fabricas.producto("Otro").pk, "cantidad": 1}],
                  "envio": fabricas.ENVIO}
        self.client.post("/api/pedidos/", data=json.dumps(cuerpo), content_type="application/json")

        evento = EventoAuditoria.objects.get(tipo=EventoAuditoria.PEDIDO_CREADO)
        guardado = f"{evento.detalle} {evento.usuario_intentado} {evento.ruta}"
        for dato in (fabricas.ENVIO["direccion"], fabricas.ENVIO["telefono"]):
            self.assertNotIn(dato, guardado)
