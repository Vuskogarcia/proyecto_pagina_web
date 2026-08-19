import threading

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase

from .models import TicketSoporte, RegistroAsignacion


class ConcurrenciaTicketsTests(TransactionTestCase):
    def setUp(self):
        # Preparar: dos agentes y un ticket sin asignar.
        Usuario = get_user_model()
        self.agente1 = Usuario.objects.create_user(username="agente1", password="clave123")
        self.agente2 = Usuario.objects.create_user(username="agente2", password="clave123")
        self.ticket = TicketSoporte.objects.create(
            asunto="Problema con mi pedido", descripcion="No llegó el paquete"
        )

    def test_dos_agentes_compiten_por_el_mismo_ticket(self):
        # Ejecutar: ambos agentes intentan tomar el ticket casi al mismo tiempo,
        # cada uno en su propio hilo con su propia conexión a la base de datos.
        resultados = {}

        def intentar_tomar(nombre_agente, agente):
            connection.close()  # cada hilo necesita su propia conexión
            try:
                self.ticket.tomar(agente=agente)
                resultados[nombre_agente] = "exito"
            except ValueError:
                resultados[nombre_agente] = "rechazado"
            finally:
                connection.close()

        hilo1 = threading.Thread(target=intentar_tomar, args=("agente1", self.agente1))
        hilo2 = threading.Thread(target=intentar_tomar, args=("agente2", self.agente2))

        hilo1.start()
        hilo2.start()
        hilo1.join()
        hilo2.join()

        # Verificar: exactamente uno tuvo éxito y el otro fue rechazado,
        # nunca ambos con éxito (eso sería la condición de carrera).
        self.assertEqual(list(resultados.values()).count("exito"), 1)
        self.assertEqual(list(resultados.values()).count("rechazado"), 1)

        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.estado, "asignado")
        self.assertEqual(RegistroAsignacion.objects.filter(ticket=self.ticket).count(), 1)
