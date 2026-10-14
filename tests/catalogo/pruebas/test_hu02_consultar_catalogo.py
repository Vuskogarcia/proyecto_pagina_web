"""HU-02 · Como cliente, quiero consultar el catálogo de productos para conocer
los productos disponibles antes de realizar una compra."""

from django.test import TestCase

from comun import fabricas


class HU02ConsultarCatalogoTests(TestCase):
    def setUp(self):
        # PREPARAR: un producto con stock, uno agotado y uno retirado del catálogo.
        self.teclado = fabricas.producto("Teclado mecánico", "150000", stock=10)
        self.mouse = fabricas.producto("Mouse inalámbrico", "60000", stock=0)
        self.retirado = fabricas.producto("Monitor viejo", "300000", stock=5, activo=False)

    def test_criterio1y2_muestra_solo_productos_activos_con_nombre_precio_y_descripcion(self):
        respuesta = self.client.get("/api/productos/")

        self.assertEqual(respuesta.status_code, 200)
        productos = respuesta.json()["productos"]
        nombres = [p["nombre"] for p in productos]
        self.assertEqual(nombres, ["Mouse inalámbrico", "Teclado mecánico"])
        self.assertNotIn("Monitor viejo", nombres)
        for producto in productos:
            self.assertTrue(producto["nombre"])
            self.assertTrue(producto["precio"])
            self.assertIn("descripcion", producto)

    def test_criterio3_consultar_detalle_de_un_producto(self):
        respuesta = self.client.get(f"/api/productos/{self.teclado.pk}/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["nombre"], "Teclado mecánico")
        self.assertEqual(respuesta.json()["precio"], "150000.00")
        # Un producto inexistente o retirado no tiene detalle.
        self.assertEqual(self.client.get("/api/productos/9999/").status_code, 404)
        self.assertEqual(
            self.client.get(f"/api/productos/{self.retirado.pk}/").status_code, 404
        )

    def test_criterio4_producto_sin_stock_se_identifica_como_agotado(self):
        productos = {p["nombre"]: p for p in self.client.get("/api/productos/").json()["productos"]}

        self.assertTrue(productos["Mouse inalámbrico"]["agotado"])
        self.assertFalse(productos["Teclado mecánico"]["agotado"])
