"""Casos borde de HU-04 (checkout), probados de punta a punta por HTTP."""

import json

from django.test import TestCase

from carrito.models import Pedido
from comun import fabricas


class CheckoutCasosBordeTests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente()
        self.teclado = fabricas.producto("Teclado", "100", stock=5)

    def post(self, cuerpo):
        return self.client.post("/api/pedidos/", data=cuerpo, content_type="application/json")

    def checkout(self, items):
        return self.post(json.dumps({"id_cliente": self.cliente.pk, "items": items}))

    def test_el_mismo_producto_repetido_se_agrupa_en_un_solo_item(self):
        respuesta = self.checkout(
            [
                {"id_producto": self.teclado.pk, "cantidad": 2},
                {"id_producto": self.teclado.pk, "cantidad": 3},
            ]
        )

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(len(respuesta.json()["items"]), 1)
        self.assertEqual(respuesta.json()["items"][0]["cantidad"], 5)
        self.teclado.refresh_from_db()
        self.assertEqual(self.teclado.stock, 0)

    def test_repetido_que_en_suma_supera_el_stock_responde_409(self):
        respuesta = self.checkout(
            [
                {"id_producto": self.teclado.pk, "cantidad": 3},
                {"id_producto": self.teclado.pk, "cantidad": 3},
            ]
        )
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_comprar_exactamente_todo_el_stock_lo_deja_agotado(self):
        self.checkout([{"id_producto": self.teclado.pk, "cantidad": 5}])

        producto = self.client.get(f"/api/productos/{self.teclado.pk}/").json()
        self.assertEqual(producto["stock"], 0)
        self.assertTrue(producto["agotado"])

    def test_producto_retirado_del_catalogo_no_se_puede_comprar(self):
        retirado = fabricas.producto("Retirado", stock=10, activo=False)

        respuesta = self.checkout([{"id_producto": retirado.pk, "cantidad": 1}])
        self.assertEqual(respuesta.status_code, 404)

    def test_cuerpo_mal_formado_responde_400(self):
        for cuerpo in ["{no es json", "[1, 2]"]:
            with self.subTest(cuerpo=cuerpo):
                self.assertEqual(self.post(cuerpo).status_code, 400)

    def test_cantidad_negativa_o_booleana_responde_400(self):
        for cantidad in [-1, True, "dos"]:
            with self.subTest(cantidad=cantidad):
                respuesta = self.checkout([{"id_producto": self.teclado.pk, "cantidad": cantidad}])
                self.assertEqual(respuesta.status_code, 400)

    def test_pedido_inexistente_responde_404_y_metodo_no_permitido_405(self):
        self.assertEqual(self.client.get("/api/pedidos/9999/").status_code, 404)
        self.assertEqual(self.client.get("/api/pedidos/").status_code, 405)
