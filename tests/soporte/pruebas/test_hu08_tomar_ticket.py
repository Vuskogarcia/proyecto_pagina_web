"""HU-08 · Como agente de servicio al cliente, quiero tomar (asignarme) un
ticket de la cola para atenderlo, incluso si otro agente intenta tomarlo al
mismo tiempo, para evitar que dos agentes atiendan el mismo caso.

Es el "problema duro" del proyecto (docs/problema-duro.md)."""

import json
import threading

from django.db import connection
from django.test import TestCase, TransactionTestCase

from comun import fabricas
from comun.excepciones import EstadoInvalido
from soporte import servicios
from soporte.models import RegistroAsignacion, TicketSoporte


class HU08TomarTicketTests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente()
        self.agente1 = fabricas.agente("agente1")
        self.agente2 = fabricas.agente("agente2")
        self.ticket = fabricas.ticket(self.cliente)

    def tomar(self, agente, ticket_id=None):
        return self.client.post(
            f"/api/tickets/{ticket_id or self.ticket.pk}/tomar/",
            data=json.dumps({"id_agente": agente.pk}),
            content_type="application/json",
        )

    def test_criterio1y4_el_ticket_queda_asignado_y_registrado(self):
        respuesta = self.tomar(self.agente1)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["agente"], "agente1")
        self.assertEqual(respuesta.json()["estado"], "EN_PROCESO")
        registro = RegistroAsignacion.objects.get(ticket=self.ticket)
        self.assertEqual(registro.agente, self.agente1)
        self.assertIsNotNone(registro.asignado_en)

    def test_criterio2_un_ticket_ya_tomado_responde_409(self):
        self.tomar(self.agente1)

        respuesta = self.tomar(self.agente2)

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.json()["error"], "El ticket ya fue asignado")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.agente, self.agente1)
        # El intento rechazado no deja registro de asignación.
        self.assertEqual(RegistroAsignacion.objects.filter(ticket=self.ticket).count(), 1)
        # Un ticket que no existe tampoco se puede tomar.
        self.assertEqual(self.tomar(self.agente1, ticket_id=9999).status_code, 404)


class HU08ConcurrenciaTests(TransactionTestCase):
    """Criterio 3: prueba automatizada de asignación concurrente.

    TransactionTestCase (y no TestCase) porque cada hilo necesita su propia
    conexión y transacción real contra PostgreSQL."""

    def setUp(self):
        # PREPARAR: dos agentes y un ticket sin asignar.
        self.agente1 = fabricas.agente("agente1")
        self.agente2 = fabricas.agente("agente2")
        self.ticket = fabricas.ticket(fabricas.cliente())

    def test_criterio3_dos_agentes_compiten_y_solo_uno_obtiene_el_ticket(self):
        resultados = {}
        salida = threading.Barrier(2)  # ambos hilos arrancan al mismo tiempo

        def intentar_tomar(nombre, agente):
            try:
                salida.wait()
                servicios.tomar_ticket(self.ticket.pk, agente.pk)
                resultados[nombre] = "exito"
            except EstadoInvalido:
                resultados[nombre] = "rechazado"
            finally:
                connection.close()  # cada hilo cierra su propia conexión

        # EJECUTAR: dos hilos, cada uno con su conexión, intentan tomar el ticket.
        hilos = [
            threading.Thread(target=intentar_tomar, args=("agente1", self.agente1)),
            threading.Thread(target=intentar_tomar, args=("agente2", self.agente2)),
        ]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        # VERIFICAR: exactamente uno tuvo éxito y el otro fue rechazado,
        # nunca ambos con éxito (eso sería la condición de carrera).
        self.assertEqual(sorted(resultados.values()), ["exito", "rechazado"])
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado, TicketSoporte.EN_PROCESO)
        self.assertEqual(RegistroAsignacion.objects.filter(ticket=self.ticket).count(), 1)
