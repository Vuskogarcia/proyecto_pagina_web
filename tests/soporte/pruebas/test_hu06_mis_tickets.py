"""HU-06 · Como cliente, quiero consultar el estado de mis tickets para conocer
el avance de mi solicitud."""

from django.test import TestCase

from comun import fabricas
from soporte import servicios


class HU06MisTicketsTests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente("ana")
        self.agente = fabricas.agente()
        self.pedido = fabricas.pedido(self.cliente, [(fabricas.producto(), 1)])
        self.mio = fabricas.ticket(self.cliente, "Llegó roto", self.pedido)
        fabricas.ticket(fabricas.cliente("luis"), "Ticket de otro cliente")
        self.client.force_login(self.cliente)

    def test_criterio1y2_veo_solo_mis_tickets_con_numero_fecha_asunto_y_pedido(self):
        tickets = self.client.get("/api/tickets/").json()["tickets"]

        self.assertEqual(len(tickets), 1)
        ticket = tickets[0]
        self.assertEqual(ticket["numero"], self.mio.numero)
        self.assertEqual(ticket["pedido"], self.pedido.codigo)
        self.assertIn("fecha", ticket)
        self.assertIn("asunto", ticket)

    def test_criterio3_muestra_los_estados_abierto_en_proceso_resuelto_y_cerrado(self):
        vistos = [self.client.get("/api/tickets/").json()["tickets"][0]["estado"]]
        servicios.tomar_ticket(self.mio.pk, self.agente.pk)
        vistos.append(self.client.get(f"/api/tickets/{self.mio.pk}/").json()["estado"])
        for estado in ("RESUELTO", "CERRADO"):
            servicios.cambiar_estado(self.mio.pk, self.agente.pk, estado)
            vistos.append(self.client.get(f"/api/tickets/{self.mio.pk}/").json()["estado"])

        self.assertEqual(vistos, ["ABIERTO", "EN_PROCESO", "RESUELTO", "CERRADO"])

    def test_criterio4_el_estado_se_actualiza_cuando_el_agente_hace_cambios(self):
        servicios.tomar_ticket(self.mio.pk, self.agente.pk)
        servicios.cambiar_estado(self.mio.pk, self.agente.pk, "RESUELTO")

        html = self.client.get("/pqr/").content.decode()
        self.assertIn("Resuelto", html)
        self.assertIn(self.mio.numero, html)
