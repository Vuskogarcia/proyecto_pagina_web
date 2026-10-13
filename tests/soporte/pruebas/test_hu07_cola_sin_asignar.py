"""HU-07 · Como agente de servicio al cliente, quiero visualizar una cola de
tickets sin asignar para elegir cuáles atender."""

from django.test import TestCase

from comun import fabricas
from soporte import servicios


class HU07ColaSinAsignarTests(TestCase):
    def setUp(self):
        # PREPARAR: dos tickets libres y uno que ya tomó un agente.
        self.cliente = fabricas.cliente()
        self.agente = fabricas.agente()
        pedido = fabricas.pedido(self.cliente, [(fabricas.producto(), 1)])
        self.primero = fabricas.ticket(self.cliente, "Primero", pedido)
        self.segundo = fabricas.ticket(self.cliente, "Segundo")
        self.tomado = fabricas.ticket(self.cliente, "Ya tomado")
        servicios.tomar_ticket(self.tomado.pk, self.agente.pk)

    def test_criterio1y4_muestra_solo_los_tickets_sin_asignar(self):
        respuesta = self.client.get("/api/tickets/cola/")

        self.assertEqual(respuesta.status_code, 200)
        descripciones = [t["descripcion"] for t in respuesta.json()["tickets"]]
        self.assertNotIn("Ya tomado", descripciones)
        self.assertEqual(len(descripciones), 2)

    def test_criterio2_cada_ticket_muestra_cliente_y_pedido(self):
        primero = self.client.get("/api/tickets/cola/").json()["tickets"][0]

        self.assertEqual(primero["cliente"], self.cliente.username)
        self.assertEqual(primero["pedido"], self.primero.pedido.codigo)

    def test_criterio3_ordenada_por_fecha_del_mas_antiguo_al_mas_nuevo(self):
        descripciones = [t["descripcion"] for t in self.client.get("/api/tickets/cola/").json()["tickets"]]

        self.assertEqual(descripciones, ["Primero", "Segundo"])
