"""Casos borde de HU-05, HU-07 y HU-08, probados de punta a punta por HTTP."""

import json

from django.test import TestCase

from comun import fabricas
from soporte.models import RegistroAsignacion, TicketSoporte


class SoporteCasosBordeTests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente()
        self.agente = fabricas.agente()
        self.ticket = fabricas.ticket(self.cliente)

    def tomar(self, cuerpo, ticket_id=None):
        return self.client.post(
            f"/api/tickets/{ticket_id or self.ticket.pk}/tomar/",
            data=json.dumps(cuerpo),
            content_type="application/json",
        )

    def test_un_cliente_que_intenta_tomar_un_ticket_recibe_403(self):
        respuesta = self.tomar({"id_agente": self.cliente.pk})

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta.json()["error"], "Solo un agente de soporte puede tomar tickets")
        self.assertEqual(RegistroAsignacion.objects.count(), 0)

    def test_tomar_sin_id_agente_responde_400(self):
        self.assertEqual(self.tomar({}).status_code, 400)

    def test_tomar_con_agente_inexistente_responde_404(self):
        self.assertEqual(self.tomar({"id_agente": 9999}).status_code, 404)

    def test_un_ticket_cerrado_no_se_puede_tomar_ni_aparece_en_la_cola(self):
        self.ticket.estado = TicketSoporte.CERRADO
        self.ticket.save()

        self.assertEqual(self.tomar({"id_agente": self.agente.pk}).status_code, 409)
        self.assertEqual(self.client.get("/api/tickets/cola/").json()["tickets"], [])

    def test_la_cola_vacia_responde_200_con_lista_vacia(self):
        self.tomar({"id_agente": self.agente.pk})

        respuesta = self.client.get("/api/tickets/cola/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"tickets": []})

    def test_ticket_sin_pedido_se_crea_y_muestra_pedido_nulo(self):
        respuesta = self.client.post(
            "/api/tickets/",
            data=json.dumps({"id_cliente": self.cliente.pk, "descripcion": "Duda general"}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertIsNone(respuesta.json()["pedido"])

    def test_ver_ticket_inexistente_responde_404(self):
        self.assertEqual(self.client.get("/api/tickets/9999/").status_code, 404)
