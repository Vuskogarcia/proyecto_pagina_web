"""HU-04 · Como cliente, quiero agregar productos a un carrito y realizar el
checkout para completar mi compra."""

import json

from django.test import TestCase

from carrito.models import Pedido
from comun import fabricas


class HU04CheckoutTests(TestCase):
    def setUp(self):
        # PREPARAR: un cliente y dos productos con stock.
        self.cliente = fabricas.cliente()
        self.teclado = fabricas.producto("Teclado mecánico", "150000", stock=5)
        self.mouse = fabricas.producto("Mouse inalámbrico", "60000", stock=3)

    def checkout(self, items, id_cliente=None):
        return self.client.post(
            "/api/pedidos/",
            data=json.dumps({"id_cliente": id_cliente or self.cliente.pk, "items": items}),
            content_type="application/json",
        )

    def test_criterio2_calcula_correctamente_el_total(self):
        respuesta = self.checkout(
            [
                {"id_producto": self.teclado.pk, "cantidad": 2},
                {"id_producto": self.mouse.pk, "cantidad": 1},
            ]
        )

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["total"], "360000.00")  # 2*150000 + 60000

    def test_criterio4_genera_pedido_con_identificador_unico(self):
        primero = self.checkout([{"id_producto": self.teclado.pk, "cantidad": 1}]).json()
        segundo = self.checkout([{"id_producto": self.teclado.pk, "cantidad": 1}]).json()

        self.assertRegex(primero["codigo"], r"^PED-\d{5}$")
        self.assertNotEqual(primero["codigo"], segundo["codigo"])
        self.assertEqual(primero["estado"], "CONFIRMADO")

    def test_el_checkout_descuenta_el_stock(self):
        self.checkout([{"id_producto": self.teclado.pk, "cantidad": 2}])

        self.teclado.refresh_from_db()
        self.assertEqual(self.teclado.stock, 3)

    def test_sin_stock_suficiente_no_se_crea_el_pedido_ni_se_descuenta_nada(self):
        # El teclado sí alcanza, el mouse no: la operación es todo o nada.
        respuesta = self.checkout(
            [
                {"id_producto": self.teclado.pk, "cantidad": 1},
                {"id_producto": self.mouse.pk, "cantidad": 10},
            ]
        )

        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("Stock insuficiente", respuesta.json()["error"])
        self.teclado.refresh_from_db()
        self.assertEqual(self.teclado.stock, 5)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_criterio3_datos_incompletos_o_invalidos_dan_400(self):
        self.assertEqual(self.checkout([]).status_code, 400)
        self.assertEqual(
            self.checkout([{"id_producto": self.teclado.pk, "cantidad": 0}]).status_code, 400
        )
        self.assertEqual(
            self.checkout([{"id_producto": "abc", "cantidad": 1}]).status_code, 400
        )

    def test_producto_o_cliente_inexistente_da_404(self):
        self.assertEqual(self.checkout([{"id_producto": 9999, "cantidad": 1}]).status_code, 404)
        self.assertEqual(
            self.checkout([{"id_producto": self.teclado.pk, "cantidad": 1}], id_cliente=9999).status_code,
            404,
        )

    def test_se_puede_consultar_el_pedido_creado(self):
        creado = self.checkout([{"id_producto": self.mouse.pk, "cantidad": 2}]).json()

        respuesta = self.client.get(f"/api/pedidos/{creado['id']}/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["items"][0]["producto"], "Mouse inalámbrico")
        self.assertEqual(respuesta.json()["items"][0]["cantidad"], 2)
