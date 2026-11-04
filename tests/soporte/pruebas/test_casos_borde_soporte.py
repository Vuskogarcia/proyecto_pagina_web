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

    def tomar(self, usuario, cuerpo=None, ticket_id=None):
        # HU-01: quien toma el ticket es el usuario en sesión (ADL-01).
        self.client.force_login(usuario)
        return self.client.post(
            f"/api/tickets/{ticket_id or self.ticket.pk}/tomar/",
            data=json.dumps(cuerpo or {}),
            content_type="application/json",
        )

    def test_un_cliente_que_intenta_tomar_un_ticket_recibe_403(self):
        respuesta = self.tomar(self.cliente)

        self.assertEqual(respuesta.status_code, 403)
        self.assertEqual(respuesta.json()["error"], "Solo un agente de soporte puede tomar tickets")
        self.assertEqual(RegistroAsignacion.objects.count(), 0)

    def test_tomar_sin_sesion_responde_401(self):
        respuesta = self.client.post(f"/api/tickets/{self.ticket.pk}/tomar/")
        self.assertEqual(respuesta.status_code, 401)

    def test_enviar_id_agente_en_el_cuerpo_responde_400(self):
        # Antes el agente venía en el cuerpo; ahora es un campo no permitido.
        self.assertEqual(self.tomar(self.agente, {"id_agente": self.agente.pk}).status_code, 400)
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.agente)

    def test_un_ticket_cerrado_no_se_puede_tomar_ni_aparece_en_la_cola(self):
        self.ticket.estado = TicketSoporte.CERRADO
        self.ticket.save()

        self.assertEqual(self.tomar(self.agente).status_code, 409)
        self.assertEqual(self.client.get("/api/tickets/cola/").json()["tickets"], [])

    def test_la_cola_vacia_responde_200_con_lista_vacia(self):
        self.tomar(self.agente)

        respuesta = self.client.get("/api/tickets/cola/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"tickets": []})

    def test_ticket_sin_pedido_se_crea_y_muestra_pedido_nulo(self):
        self.client.force_login(self.cliente)
        respuesta = self.client.post(
            "/api/tickets/",
            data=json.dumps({"descripcion": "Duda general"}),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertIsNone(respuesta.json()["pedido"])

    def test_ver_ticket_inexistente_responde_404(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get("/api/tickets/9999/").status_code, 404)

    def test_la_cola_se_puede_ordenar_de_la_mas_nueva_a_la_mas_antigua(self):
        # HU-07 criterio 3 (DT-05): orden por fecha en ambos sentidos.
        nuevo = fabricas.ticket(self.cliente, "Más nuevo")
        self.client.force_login(self.agente)

        recientes = self.client.get("/api/tickets/cola/?orden=recientes").json()["tickets"]
        antiguos = self.client.get("/api/tickets/cola/").json()["tickets"]

        self.assertEqual([t["id"] for t in recientes], [nuevo.pk, self.ticket.pk])
        self.assertEqual([t["id"] for t in antiguos], [self.ticket.pk, nuevo.pk])
