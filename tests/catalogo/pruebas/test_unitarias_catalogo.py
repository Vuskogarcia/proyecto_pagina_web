"""Pruebas unitarias del catálogo: reglas del modelo y del servicio.

Las del modelo no tocan la base de datos (el objeto no se guarda)."""

from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from catalogo import serializadores, servicios
from catalogo.models import Producto
from comun import fabricas
from comun.excepciones import NoEncontrado


class ProductoModeloTests(SimpleTestCase):
    def test_agotado_solo_cuando_el_stock_es_cero(self):
        self.assertTrue(Producto(stock=0).agotado)
        self.assertFalse(Producto(stock=1).agotado)

    def test_hay_disponible_compara_contra_el_stock(self):
        producto = Producto(stock=3)
        self.assertTrue(producto.hay_disponible(3))  # caso borde: exactamente el stock
        self.assertFalse(producto.hay_disponible(4))

    def test_serializador_expone_precio_como_texto_y_marca_agotado(self):
        datos = serializadores.a_dict(
            Producto(nombre="Mouse", descripcion="d", precio=Decimal("60000.00"), stock=0)
        )
        self.assertEqual(datos["precio"], "60000.00")
        self.assertTrue(datos["agotado"])


class CatalogoServicioTests(TestCase):
    def test_listar_catalogo_excluye_productos_inactivos(self):
        activo = fabricas.producto("Activo")
        fabricas.producto("Retirado", activo=False)

        self.assertEqual(list(servicios.listar_catalogo()), [activo])

    def test_detalle_de_producto_inactivo_lanza_no_encontrado(self):
        retirado = fabricas.producto("Retirado", activo=False)

        with self.assertRaises(NoEncontrado):
            servicios.detalle_producto(retirado.pk)
