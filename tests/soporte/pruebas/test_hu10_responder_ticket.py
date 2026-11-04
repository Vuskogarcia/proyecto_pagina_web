"""HU-10 · Como agente de servicio al cliente, quiero responder los tickets que
tengo asignados y cambiar su estado para registrar el proceso de atención."""

import json

from django.test import TestCase

from comun import fabricas
from soporte import servicios
from soporte.models import RespuestaTicket, TicketSoporte


class HU10ResponderTicketTests(TestCase):
    def setUp(self):
        # PREPARAR: un ticket que ya tomó agente1.
        self.cliente = fabricas.cliente()
        self.agente = fabricas.agente("agente1")
        self.otro_agente = fabricas.agente("agente2")
        self.ticket = fabricas.ticket(self.cliente)
        servicios.tomar_ticket(self.ticket.pk, self.agente.pk)

    def post(self, usuario, ruta, datos):
        self.client.force_login(usuario)
        return self.client.post(f"/api/tickets/{self.ticket.pk}/{ruta}/", data=json.dumps(datos),
                                content_type="application/json")

    def test_criterio1_solo_el_agente_asignado_puede_responder(self):
        rechazo = self.post(self.otro_agente, "respuestas", {"mensaje": "Yo lo atiendo"})

        self.assertEqual(rechazo.status_code, 403)
        self.assertEqual(rechazo.json()["error"], "Solo el agente asignado puede atender este ticket")
        self.assertFalse(RespuestaTicket.objects.exists())
        self.assertEqual(self.post(self.agente, "respuestas", {"mensaje": "Hola"}).status_code, 201)

    def test_criterio2_la_respuesta_queda_registrada_con_fecha_y_autor(self):
        respuesta = self.post(self.agente, "respuestas", {"mensaje": "Ya enviamos el reemplazo"})

        self.assertEqual(respuesta.status_code, 201)
        guardada = RespuestaTicket.objects.get()
        self.assertEqual((guardada.ticket, guardada.autor, guardada.mensaje),
                         (self.ticket, self.agente, "Ya enviamos el reemplazo"))
        self.assertIsNotNone(guardada.creado_en)
        self.assertEqual(respuesta.json()["autor"], "agente1")

    def test_criterio3y4_cambia_el_estado_y_el_cliente_ve_respuesta_y_estado(self):
        self.post(self.agente, "respuestas", {"mensaje": "Solucionado"})
        resuelto = self.post(self.agente, "estado", {"estado": "RESUELTO"})
        cerrado = self.post(self.agente, "estado", {"estado": "CERRADO"})

        self.assertEqual((resuelto.status_code, cerrado.status_code), (200, 200))
        self.client.force_login(self.cliente)
        visto = self.client.get(f"/api/tickets/{self.ticket.pk}/").json()
        self.assertEqual(visto["estado"], "CERRADO")
        self.assertEqual([r["mensaje"] for r in visto["respuestas"]], ["Solucionado"])
