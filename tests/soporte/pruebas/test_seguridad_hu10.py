"""Seguridad de HU-10 (responder y cambiar estado): control de acceso,
transiciones válidas, validación de entrada, XSS, CSRF, concurrencia y auditoría."""

import json
import threading

from django.db import connection
from django.test import Client, TestCase, TransactionTestCase

from comun import fabricas
from comun.excepciones import EstadoInvalido
from cuentas.models import EventoAuditoria
from soporte import servicios
from soporte.models import RespuestaTicket, TicketSoporte

XSS = "<script>alert(1)</script>"


class ControlDeAccesoHU10Tests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente()
        self.agente = fabricas.agente("agente1")
        self.ticket = fabricas.ticket(self.cliente)
        servicios.tomar_ticket(self.ticket.pk, self.agente.pk)

    def post(self, usuario, ruta, datos, cliente_http=None):
        http = cliente_http or self.client
        if usuario is not None:
            http.force_login(usuario)
        return http.post(f"/api/tickets/{self.ticket.pk}/{ruta}/", data=json.dumps(datos),
                         content_type="application/json")

    def test_anonimo_cliente_y_agente_no_asignado_no_pueden_responder_ni_cambiar_estado(self):
        casos = [(None, 401), (self.cliente, 403), (fabricas.agente("agente2"), 403)]
        for usuario, codigo in casos:
            for ruta, datos in (("respuestas", {"mensaje": "x"}), ("estado", {"estado": "RESUELTO"})):
                with self.subTest(usuario=getattr(usuario, "username", "anonimo"), ruta=ruta):
                    self.assertEqual(self.post(usuario, ruta, datos, self.client_class()).status_code, codigo)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado, "EN_PROCESO")
        self.assertFalse(RespuestaTicket.objects.exists())

    def test_ticket_inexistente_responde_404(self):
        self.client.force_login(self.agente)
        respuesta = self.client.post("/api/tickets/999999/respuestas/", data='{"mensaje": "x"}',
                                     content_type="application/json")
        self.assertEqual(respuesta.status_code, 404)


class TransicionesYValidacionHU10Tests(TestCase):
    def setUp(self):
        self.agente = fabricas.agente()
        self.ticket = fabricas.ticket(fabricas.cliente())
        servicios.tomar_ticket(self.ticket.pk, self.agente.pk)
        self.client.force_login(self.agente)

    def post(self, ruta, cuerpo):
        datos = cuerpo if isinstance(cuerpo, str) else json.dumps(cuerpo)
        return self.client.post(f"/api/tickets/{self.ticket.pk}/{ruta}/", data=datos,
                                content_type="application/json")

    def test_estados_invalidos_o_saltos_no_permitidos(self):
        casos = [
            ({"estado": "INVENTADO"}, 400),
            ({"estado": ["RESUELTO"]}, 400),  # tipo incorrecto: no debe ser un 500
            ({"estado": "CERRADO"}, 409),  # no se puede cerrar sin pasar por Resuelto
            ({"estado": "ABIERTO"}, 409),  # no se devuelve a la cola
            ({"estado": "RESUELTO", "agente": 1}, 400),  # campo no permitido
        ]
        for cuerpo, codigo in casos:
            with self.subTest(cuerpo=cuerpo):
                self.assertEqual(self.post("estado", cuerpo).status_code, codigo)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado, "EN_PROCESO")

    def test_un_ticket_cerrado_no_admite_respuestas_ni_cambios(self):
        self.post("estado", {"estado": "RESUELTO"})
        self.post("estado", {"estado": "CERRADO"})

        self.assertEqual(self.post("respuestas", {"mensaje": "una más"}).status_code, 409)
        self.assertEqual(self.post("estado", {"estado": "EN_PROCESO"}).status_code, 409)
        self.assertFalse(RespuestaTicket.objects.exists())

    def test_mensajes_invalidos_responden_400(self):
        for cuerpo in [{"mensaje": "   "}, {"mensaje": "x" * 5001}, {"mensaje": 123},
                       {"mensaje": "a\x00b"}, '{"mensaje": "\\ud800"}', {"mensaje": "x", "autor": 9}]:
            with self.subTest(cuerpo=str(cuerpo)[:40]):
                self.assertEqual(self.post("respuestas", cuerpo).status_code, 400)
        self.assertFalse(RespuestaTicket.objects.exists())

    def test_xss_en_la_respuesta_se_muestra_escapado_al_cliente(self):
        self.post("respuestas", {"mensaje": XSS})
        self.client.force_login(self.ticket.cliente)
        html = self.client.get(f"/pqr/{self.ticket.pk}/").content.decode()
        self.assertNotIn(XSS, html)
        self.assertIn("&lt;script&gt;", html)

    def test_cada_respuesta_y_cambio_de_estado_queda_en_auditoria(self):
        self.post("respuestas", {"mensaje": "Hola"})
        self.post("estado", {"estado": "RESUELTO"})
        eventos = EventoAuditoria.objects.filter(
            tipo__in=[EventoAuditoria.TICKET_RESPONDIDO, EventoAuditoria.TICKET_ESTADO]
        ).order_by("id")
        self.assertEqual([e.tipo for e in eventos], ["TICKET_RESPONDIDO", "TICKET_ESTADO"])
        self.assertIn("EN_PROCESO -> RESUELTO", eventos[1].detalle)


class WebHU10Tests(TestCase):
    def setUp(self):
        self.agente = fabricas.agente()
        self.ticket = fabricas.ticket(fabricas.cliente())
        servicios.tomar_ticket(self.ticket.pk, self.agente.pk)

    def test_los_formularios_exigen_csrf_y_un_cliente_no_entra(self):
        navegador = Client(enforce_csrf_checks=True)
        navegador.force_login(self.agente)
        respuesta = navegador.post(f"/agente/tickets/{self.ticket.pk}/responder/", {"mensaje": "x"})
        self.assertEqual(respuesta.status_code, 403)

        self.client.force_login(self.ticket.cliente)
        respuesta = self.client.post(f"/agente/tickets/{self.ticket.pk}/estado/", {"estado": "RESUELTO"})
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(RespuestaTicket.objects.exists())

    def test_positivo_el_agente_asignado_responde_y_resuelve_desde_la_web(self):
        self.client.force_login(self.agente)
        self.client.post(f"/agente/tickets/{self.ticket.pk}/responder/", {"mensaje": "Listo"})
        self.client.post(f"/agente/tickets/{self.ticket.pk}/estado/", {"estado": "RESUELTO"})
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado, "RESUELTO")
        self.assertEqual(RespuestaTicket.objects.get().mensaje, "Listo")


class CambioDeEstadoConcurrenteTests(TransactionTestCase):
    """Dos pestañas del mismo agente cierran a la vez: el bloqueo de fila
    evita que ambas «ganen». Necesita PostgreSQL (select_for_update)."""

    def test_dos_cierres_simultaneos_solo_uno_tiene_exito(self):
        agente = fabricas.agente()
        ticket = fabricas.ticket(fabricas.cliente())
        servicios.tomar_ticket(ticket.pk, agente.pk)
        servicios.cambiar_estado(ticket.pk, agente.pk, "RESUELTO")
        resultados, salida = [], threading.Barrier(2)

        def cerrar():
            try:
                salida.wait()
                servicios.cambiar_estado(ticket.pk, agente.pk, "CERRADO")
                resultados.append("exito")
            except EstadoInvalido:
                resultados.append("rechazado")
            finally:
                connection.close()

        hilos = [threading.Thread(target=cerrar) for _ in range(2)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        self.assertEqual(sorted(resultados), ["exito", "rechazado"])
        self.assertEqual(
            EventoAuditoria.objects.filter(tipo=EventoAuditoria.TICKET_ESTADO, detalle__contains="CERRADO").count(), 1
        )
        self.assertEqual(TicketSoporte.objects.get().estado, "CERRADO")
