"""El comando cargar_datos_demo debe funcionar sobre una base vacía y no
duplicar datos si se corre dos veces."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from carrito.models import Pedido
from catalogo.models import Producto
from soporte.models import TicketSoporte


class CargarDatosDemoTests(TestCase):
    def test_carga_los_datos_y_no_los_duplica(self):
        call_command("cargar_datos_demo", stdout=StringIO())
        call_command("cargar_datos_demo", stdout=StringIO())  # segunda vez: no hace nada

        self.assertEqual(Producto.objects.count(), 5)
        self.assertEqual(Pedido.objects.count(), 3)
        self.assertEqual(TicketSoporte.objects.count(), 3)
        self.assertEqual(Producto.objects.get(nombre="Teclado mecánico").stock, 24)

    def test_reset_vuelve_a_cargar_desde_cero(self):
        call_command("cargar_datos_demo", stdout=StringIO())
        call_command("cargar_datos_demo", "--reset", stdout=StringIO())

        self.assertEqual(Producto.objects.count(), 5)
        self.assertEqual(TicketSoporte.objects.filter(estado="ABIERTO").count(), 1)
