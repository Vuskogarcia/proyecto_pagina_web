"""HU-03 · Como administrador, quiero gestionar el catálogo y el inventario
para mantener actualizada la información de los productos disponibles."""

import json

from django.test import TestCase

from catalogo.models import Producto
from comun import fabricas


class HU03GestionarCatalogoTests(TestCase):
    def setUp(self):
        self.admin = fabricas.administrador()
        self.client.force_login(self.admin)

    def enviar(self, metodo, url, datos):
        return getattr(self.client, metodo)(url, data=json.dumps(datos), content_type="application/json")

    def test_criterio1y4_crea_un_producto_y_aparece_en_el_catalogo(self):
        respuesta = self.enviar("post", "/api/productos/", {
            "nombre": "Silla ergonómica", "descripcion": "Con soporte lumbar",
            "precio": "450000.50", "stock": 7,
        })

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["precio"], "450000.50")
        catalogo = self.client_class().get("/api/productos/").json()["productos"]
        self.assertEqual([(p["nombre"], p["stock"]) for p in catalogo], [("Silla ergonómica", 7)])

    def test_criterio2y4_modifica_nombre_descripcion_precio_y_stock(self):
        producto = fabricas.producto("Teclado", "150000", stock=5)

        respuesta = self.enviar("patch", f"/api/productos/{producto.pk}/", {
            "nombre": "Teclado RGB", "descripcion": "Nueva versión", "precio": 160000, "stock": 12,
        })

        self.assertEqual(respuesta.status_code, 200)
        visto = self.client_class().get(f"/api/productos/{producto.pk}/").json()
        self.assertEqual((visto["nombre"], visto["descripcion"], visto["precio"], visto["stock"]),
                         ("Teclado RGB", "Nueva versión", "160000.00", 12))

    def test_criterio3y4_desactivar_lo_retira_del_catalogo_sin_borrarlo(self):
        producto = fabricas.producto("Webcam")

        self.assertEqual(self.enviar("patch", f"/api/productos/{producto.pk}/", {"activo": False}).status_code, 200)

        publico = self.client_class()
        self.assertEqual(publico.get("/api/productos/").json()["productos"], [])
        self.assertEqual(publico.get(f"/api/productos/{producto.pk}/").status_code, 404)
        self.assertTrue(Producto.objects.filter(pk=producto.pk, activo=False).exists())  # no se borró
