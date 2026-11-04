"""Pruebas unitarias de las piezas de seguridad nuevas (sin HTTP)."""

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import SimpleTestCase, TestCase

from carrito import carrito_sesion
from comun import fabricas
from comun.convertidores import IdConverter
from comun.excepciones import DatosInvalidos, NoEncontrado
from comun.roles import es_agente, rol
from comun.validaciones import MAX_ENTERO, entero, texto, texto_seguro


class EnteroListaDePermitidosTests(SimpleTestCase):
    def test_rechaza_float_digitos_no_ascii_espacios_y_fuera_de_cota(self):
        for valor in [1.0, 1.9, "١", "٣", " 7", "7 ", "1e3", "+5", MAX_ENTERO + 1, 10**30]:
            with self.subTest(valor=valor), self.assertRaises(DatosInvalidos):
                entero(valor, "x")

    def test_cota_personalizada(self):
        self.assertEqual(entero(1000, "cantidad", maximo=1000), 1000)
        with self.assertRaises(DatosInvalidos):
            entero(1001, "cantidad", maximo=1000)


class TextoSeguroTests(SimpleTestCase):
    def test_rechaza_nul_y_surrogates_sueltos(self):
        for valor in ["a\x00b", "\ud800", "x\udfffy"]:
            with self.subTest(valor=repr(valor)), self.assertRaises(DatosInvalidos):
                texto_seguro(valor)

    def test_acepta_tildes_emoji_y_saltos_de_linea(self):
        self.assertEqual(texto_seguro("Ñandú 📦\nlínea 2"), "Ñandú 📦\nlínea 2")

    def test_texto_valida_largo_y_obligatorio(self):
        with self.assertRaises(DatosInvalidos):
            texto("   ", "descripcion")
        with self.assertRaises(DatosInvalidos):
            texto("x" * 11, "asunto", maximo=10)
        self.assertEqual(texto("  hola  ", "x"), "hola")


class IdConverterTests(SimpleTestCase):
    def test_id_fuera_de_rango_no_llega_a_la_consulta(self):
        with self.assertRaises(ValueError):
            IdConverter().to_python(str(MAX_ENTERO + 1))
        self.assertEqual(IdConverter().to_python("42"), 42)


class RolesTests(TestCase):
    def test_agente_es_el_grupo_no_is_staff(self):
        agente = fabricas.agente()
        staff = fabricas.cliente("staff")
        staff.is_staff = True
        staff.save()

        self.assertTrue(es_agente(agente))
        self.assertFalse(agente.is_staff)
        self.assertFalse(es_agente(staff))
        self.assertEqual(rol(agente), "agente")
        self.assertEqual(rol(staff), "cliente")


class CarritoSesionTests(TestCase):
    def setUp(self):
        self.sesion = SessionStore()
        self.producto = fabricas.producto(precio="1000", stock=3)

    def test_agrega_suma_y_calcula_total_con_precio_de_la_base(self):
        carrito_sesion.agregar(self.sesion, self.producto.pk, 1)
        carrito_sesion.agregar(self.sesion, str(self.producto.pk), "2")
        resumen = carrito_sesion.resumen(self.sesion)
        self.assertEqual(resumen["lineas"][0]["cantidad"], 3)
        self.assertEqual(str(resumen["total"]), "3000.00")

    def test_producto_inexistente_o_retirado_no_entra_al_carrito(self):
        retirado = fabricas.producto("Retirado", activo=False)
        for producto_id in (9999, retirado.pk):
            with self.subTest(producto_id=producto_id), self.assertRaises(NoEncontrado):
                carrito_sesion.agregar(self.sesion, producto_id)
        self.assertEqual(carrito_sesion.unidades(self.sesion), 0)

    def test_cantidad_fuera_de_cota_se_rechaza(self):
        with self.assertRaises(DatosInvalidos):
            carrito_sesion.agregar(self.sesion, self.producto.pk, 1001)
