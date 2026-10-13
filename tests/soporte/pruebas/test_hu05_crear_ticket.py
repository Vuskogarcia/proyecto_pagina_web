"""HU-05 · Como cliente, quiero crear un ticket de soporte asociado a uno de mis
pedidos para reportar una duda, reclamo o problema con mi compra."""

import json

from django.test import TestCase

from comun import fabricas
from soporte.models import TicketSoporte


class HU05CrearTicketTests(TestCase):
    def setUp(self):
        # PREPARAR: un cliente con un pedido, y otro cliente con su propio pedido.
        self.cliente = fabricas.cliente("ana")
        self.otro_cliente = fabricas.cliente("luis")
        teclado = fabricas.producto()
        self.pedido = fabricas.pedido(self.cliente, [(teclado, 1)])
        self.pedido_ajeno = fabricas.pedido(self.otro_cliente, [(teclado, 1)])

    def crear(self, **datos):
        cuerpo = {"id_cliente": self.cliente.pk, "descripcion": "No llegó el paquete"}
        cuerpo.update(datos)
        return self.client.post(
            "/api/tickets/", data=json.dumps(cuerpo), content_type="application/json"
        )

    def test_crear_ticket_endpoint_e2e(self):
        # EJECUTAR: atravesar la frontera HTTP con un POST real al endpoint.
        respuesta = self.crear(id_pedido=None, descripcion="Problema con mi pedido, no llegó el paquete")

        # VERIFICAR: respuesta de la API y persistencia en la base de datos.
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(TicketSoporte.objects.count(), 1)
        ticket_bd = TicketSoporte.objects.first()
        self.assertEqual(ticket_bd.descripcion, "Problema con mi pedido, no llegó el paquete")
        self.assertEqual(ticket_bd.estado, "ABIERTO")

    def test_criterio1y4_el_ticket_queda_asociado_al_pedido_seleccionado(self):
        respuesta = self.crear(id_pedido=self.pedido.pk)

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["id_pedido"], self.pedido.pk)
        self.assertEqual(respuesta.json()["pedido"], self.pedido.codigo)

    def test_criterio2_guarda_asunto_y_descripcion(self):
        respuesta = self.crear(asunto="Paquete perdido", descripcion="Pasaron 10 días")

        self.assertEqual(respuesta.json()["asunto"], "Paquete perdido")
        self.assertEqual(respuesta.json()["descripcion"], "Pasaron 10 días")

    def test_criterio3_genera_un_numero_unico_de_ticket(self):
        primero = self.crear().json()
        segundo = self.crear().json()

        self.assertRegex(primero["numero"], r"^TCK-\d{5}$")
        self.assertNotEqual(primero["numero"], segundo["numero"])

    def test_no_se_puede_asociar_un_pedido_de_otro_cliente(self):
        respuesta = self.crear(id_pedido=self.pedido_ajeno.pk)

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(TicketSoporte.objects.count(), 0)

    def test_sin_descripcion_da_400(self):
        self.assertEqual(self.crear(descripcion="   ").status_code, 400)

    def test_cliente_o_pedido_inexistente_da_404(self):
        self.assertEqual(self.crear(id_cliente=9999).status_code, 404)
        self.assertEqual(self.crear(id_pedido=9999).status_code, 404)
