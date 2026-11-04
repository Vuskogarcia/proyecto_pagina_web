"""Pruebas unitarias del checkout: reglas del servicio y del modelo, sin HTTP."""

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from carrito import servicios
from carrito.models import ItemPedido, Pedido
from comun import fabricas
from comun.excepciones import DatosInvalidos, EstadoInvalido, NoEncontrado


class NormalizarItemsTests(SimpleTestCase):
    def test_agrupa_cantidades_del_mismo_producto(self):
        items = [
            {"id_producto": 1, "cantidad": 2},
            {"id_producto": 1, "cantidad": 3},
            {"id_producto": 2, "cantidad": 1},
        ]
        self.assertEqual(servicios._normalizar_items(items), {1: 5, 2: 1})

    def test_lista_vacia_o_que_no_es_lista_lanza_datos_invalidos(self):
        for items in [[], None, "abc", {"id_producto": 1}]:
            with self.subTest(items=items):
                with self.assertRaises(DatosInvalidos):
                    servicios._normalizar_items(items)

    def test_item_que_no_es_objeto_lanza_datos_invalidos(self):
        with self.assertRaises(DatosInvalidos):
            servicios._normalizar_items([5])


class PedidoModeloTests(SimpleTestCase):
    def test_subtotal_es_precio_por_cantidad(self):
        item = ItemPedido(precio_pactado=Decimal("1500.50"), cantidad=3)
        self.assertEqual(item.subtotal(), Decimal("4501.50"))

    def test_codigo_tiene_formato_ped_con_cinco_digitos(self):
        self.assertEqual(Pedido(pk=7).codigo, "PED-00007")


class RealizarCheckoutServicioTests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente()
        self.teclado = fabricas.producto("Teclado", "100", stock=2)

    def test_crea_el_pedido_con_el_precio_del_momento(self):
        pedido = servicios.realizar_checkout(
            self.cliente.pk, [{"id_producto": self.teclado.pk, "cantidad": 2}], fabricas.ENVIO
        )
        self.assertEqual(pedido.total(), Decimal("200"))
        self.assertEqual(pedido.items.get().precio_pactado, Decimal("100"))

    def test_sin_stock_suficiente_lanza_estado_invalido(self):
        with self.assertRaisesMessage(EstadoInvalido, "Stock insuficiente para Teclado"):
            servicios.realizar_checkout(
                self.cliente.pk, [{"id_producto": self.teclado.pk, "cantidad": 3}], fabricas.ENVIO
            )

    def test_cliente_inexistente_lanza_no_encontrado(self):
        with self.assertRaises(NoEncontrado):
            servicios.realizar_checkout(
                9999, [{"id_producto": self.teclado.pk, "cantidad": 1}], fabricas.ENVIO
            )
