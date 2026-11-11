"""Pruebas unitarias del soporte: reglas de los servicios llamadas directamente,
sin pasar por HTTP."""

from django.test import SimpleTestCase, TestCase

from comun import fabricas
from comun.excepciones import DatosInvalidos, EstadoInvalido, NoEncontrado, SinPermiso
from soporte import servicios
from soporte.models import RegistroAsignacion, TicketSoporte


class TicketModeloTests(SimpleTestCase):
    def test_numero_tiene_formato_tck_con_cinco_digitos(self):
        self.assertEqual(TicketSoporte(pk=42).numero, "TCK-00042")


class CrearTicketServicioTests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente()

    def test_limpia_espacios_de_la_descripcion(self):
        ticket = servicios.crear_ticket(self.cliente.pk, "  No llegó  ")
        self.assertEqual(ticket.descripcion, "No llegó")
        self.assertEqual(ticket.estado, TicketSoporte.ABIERTO)

    def test_descripcion_que_no_es_texto_lanza_datos_invalidos(self):
        for descripcion in [None, 123, ["a"]]:
            with self.subTest(descripcion=descripcion):
                with self.assertRaises(DatosInvalidos):
                    servicios.crear_ticket(self.cliente.pk, descripcion)

    def test_asunto_de_mas_de_200_caracteres_se_rechaza(self):
        # Antes se recortaba a 200; desde la Historia 03 (Módulo 7) es un 400.
        with self.assertRaises(DatosInvalidos):
            servicios.crear_ticket(self.cliente.pk, "desc", asunto="x" * 201)
        ticket = servicios.crear_ticket(self.cliente.pk, "desc", asunto="x" * 200)
        self.assertEqual(len(ticket.asunto), 200)


class TomarTicketServicioTests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente()
        self.agente = fabricas.agente()
        self.ticket = fabricas.ticket(self.cliente)

    def test_asigna_el_ticket_y_deja_registro(self):
        ticket = servicios.tomar_ticket(self.ticket.pk, self.agente.pk)

        self.assertEqual(ticket.agente, self.agente)
        self.assertEqual(ticket.estado, TicketSoporte.EN_PROCESO)
        self.assertEqual(RegistroAsignacion.objects.count(), 1)

    def test_un_cliente_no_puede_tomar_tickets(self):
        # Defecto corregido (docs/revision-codigo.md, RC-01): antes cualquier
        # usuario, incluso un cliente, podía asignarse un ticket.
        with self.assertRaises(SinPermiso):
            servicios.tomar_ticket(self.ticket.pk, self.cliente.pk)

        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.agente)
        self.assertEqual(RegistroAsignacion.objects.count(), 0)

    def test_ticket_cerrado_no_se_puede_tomar(self):
        self.ticket.estado = TicketSoporte.CERRADO
        self.ticket.save()

        with self.assertRaises(EstadoInvalido):
            servicios.tomar_ticket(self.ticket.pk, self.agente.pk)

    def test_ticket_inexistente_lanza_no_encontrado(self):
        with self.assertRaises(NoEncontrado):
            servicios.tomar_ticket(9999, self.agente.pk)


class ColaSinAsignarServicioTests(TestCase):
    def test_solo_devuelve_abiertos_sin_agente_del_mas_antiguo_al_mas_nuevo(self):
        cliente = fabricas.cliente()
        primero = fabricas.ticket(cliente, "primero")
        segundo = fabricas.ticket(cliente, "segundo")
        tomado = fabricas.ticket(cliente, "tomado")
        servicios.tomar_ticket(tomado.pk, fabricas.agente().pk)

        self.assertEqual(list(servicios.cola_sin_asignar()), [primero, segundo])
