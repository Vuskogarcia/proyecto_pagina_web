"""HU-09 · Como agente de servicio al cliente, quiero consultar la información
del pedido asociado a un ticket para conocer qué compró el cliente."""

from django.test import TestCase

from comun import fabricas


class HU09PedidoDelTicketTests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente()
        self.monitor = fabricas.producto("Monitor 24", "650000")
        self.pedido = fabricas.pedido(self.cliente, [(self.monitor, 2)])
        self.ticket = fabricas.ticket(self.cliente, "No enciende", self.pedido)
        self.client.force_login(fabricas.agente())

    def test_criterio1_desde_el_ticket_se_llega_al_pedido(self):
        ticket = self.client.get(f"/api/tickets/{self.ticket.pk}/").json()

        self.assertEqual(ticket["id_pedido"], self.pedido.pk)
        self.assertEqual(self.client.get(f"/api/pedidos/{ticket['id_pedido']}/").status_code, 200)

    def test_criterio2y3_muestra_productos_fecha_y_estado_del_pedido(self):
        pedido = self.client.get(f"/api/pedidos/{self.pedido.pk}/").json()

        self.assertEqual([(i["producto"], i["cantidad"]) for i in pedido["items"]], [("Monitor 24", 2)])
        self.assertEqual(pedido["estado"], "CONFIRMADO")
        self.assertTrue(pedido["fecha"].startswith(str(self.pedido.creado_en.date())))

    def test_criterio4_la_informacion_corresponde_al_pedido_del_ticket(self):
        otro = fabricas.pedido(self.cliente, [(fabricas.producto("Mouse"), 1)])
        html = self.client.get(f"/pqr/{self.ticket.pk}/").content.decode()

        self.assertIn(self.pedido.codigo, html)
        self.assertIn("Monitor 24", html)
        self.assertNotIn(otro.codigo, html)
