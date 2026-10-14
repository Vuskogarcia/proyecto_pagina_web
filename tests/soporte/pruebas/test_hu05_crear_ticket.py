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
        # Criterios 1, 2 y 4: el ticket guarda asunto, descripción y el pedido elegido.
        # EJECUTAR: atravesar la frontera HTTP con un POST real al endpoint.
        respuesta = self.crear(
            id_pedido=self.pedido.pk,
            asunto="Paquete perdido",
            descripcion="Problema con mi pedido, no llegó el paquete",
        )

        # VERIFICAR: respuesta de la API y persistencia en la base de datos.
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["id_pedido"], self.pedido.pk)
        self.assertEqual(respuesta.json()["pedido"], self.pedido.codigo)
        self.assertEqual(respuesta.json()["asunto"], "Paquete perdido")
        self.assertEqual(TicketSoporte.objects.count(), 1)
        ticket_bd = TicketSoporte.objects.first()
        self.assertEqual(ticket_bd.descripcion, "Problema con mi pedido, no llegó el paquete")
        self.assertEqual(ticket_bd.estado, "ABIERTO")

    def test_criterio3_genera_un_numero_unico_de_ticket(self):
        primero = self.crear().json()
        segundo = self.crear().json()

        self.assertRegex(primero["numero"], r"^TCK-\d{5}$")
        self.assertNotEqual(primero["numero"], segundo["numero"])

    def test_datos_invalidos_o_pedido_ajeno_no_crean_el_ticket(self):
        # Un cliente no puede asociar el pedido de otro cliente.
        self.assertEqual(self.crear(id_pedido=self.pedido_ajeno.pk).status_code, 400)
        self.assertEqual(self.crear(descripcion="   ").status_code, 400)
        self.assertEqual(self.crear(id_cliente=9999).status_code, 404)
        self.assertEqual(self.crear(id_pedido=9999).status_code, 404)

        self.assertEqual(TicketSoporte.objects.count(), 0)
