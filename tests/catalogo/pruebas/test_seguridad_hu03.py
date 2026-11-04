"""Seguridad de HU-03 (gestión del catálogo): solo el administrador escribe,
validación por lista de permitidos, asignación masiva, XSS, integridad de
pedidos pasados, CSRF y auditoría."""

import json
from decimal import Decimal

from django.test import Client, TestCase

from carrito.models import ItemPedido
from catalogo.models import Producto
from comun import fabricas
from cuentas.models import EventoAuditoria

XSS = "<script>alert(1)</script>"
VALIDO = {"nombre": "Lámpara", "precio": "50000", "stock": 3}


def enviar(cliente_http, metodo, url, datos):
    cuerpo = datos if isinstance(datos, str) else json.dumps(datos)
    return getattr(cliente_http, metodo)(url, data=cuerpo, content_type="application/json")


class ControlDeAccesoHU03Tests(TestCase):
    def setUp(self):
        self.producto = fabricas.producto("Teclado", "150000", stock=5)

    def test_solo_el_administrador_crea_edita_o_lista_todo(self):
        casos = [(None, 401), (fabricas.cliente(), 403), (fabricas.agente(), 403)]
        staff_sin_superusuario = fabricas.cliente("staff")
        staff_sin_superusuario.is_staff = True
        staff_sin_superusuario.save()
        casos.append((staff_sin_superusuario, 403))
        for usuario, codigo in casos:
            http = Client()
            if usuario is not None:
                http.force_login(usuario)
            nombre = getattr(usuario, "username", "anonimo")
            with self.subTest(usuario=nombre, accion="crear"):
                self.assertEqual(enviar(http, "post", "/api/productos/", VALIDO).status_code, codigo)
            with self.subTest(usuario=nombre, accion="editar"):
                respuesta = enviar(http, "patch", f"/api/productos/{self.producto.pk}/", {"precio": "1"})
                self.assertEqual(respuesta.status_code, codigo)
            with self.subTest(usuario=nombre, accion="listar todo"):
                self.assertEqual(http.get("/api/gestion/productos/").status_code, codigo)

        self.assertEqual(Producto.objects.count(), 1)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio, Decimal("150000"))

    def test_la_web_de_gestion_es_solo_para_administradores(self):
        self.assertEqual(self.client.get("/gestion/productos/").status_code, 302)  # anónimo → entrar
        for usuario in (fabricas.cliente(), fabricas.agente()):
            self.client.force_login(usuario)
            with self.subTest(usuario=usuario.username):
                self.assertEqual(self.client.get("/gestion/productos/").status_code, 403)
                respuesta = self.client.post(f"/gestion/productos/{self.producto.pk}/activo/", {"activo": "0"})
                self.assertEqual(respuesta.status_code, 403)
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.activo)


class ValidacionHU03Tests(TestCase):
    def setUp(self):
        self.client.force_login(fabricas.administrador())
        self.producto = fabricas.producto("Teclado", "150000", stock=5)

    def test_valores_invalidos_responden_400_y_no_cambian_nada(self):
        invalidos = [
            {**VALIDO, "precio": -1}, {**VALIDO, "precio": 0}, {**VALIDO, "precio": "abc"},
            {**VALIDO, "precio": "1.999"}, {**VALIDO, "precio": "1e5"}, {**VALIDO, "precio": True},
            {**VALIDO, "precio": "١٠٠"}, {**VALIDO, "precio": 10**12},
            {**VALIDO, "stock": -1}, {**VALIDO, "stock": 1.5}, {**VALIDO, "stock": 10**7},
            {**VALIDO, "nombre": "   "}, {**VALIDO, "nombre": "x" * 201}, {**VALIDO, "nombre": "a\x00b"},
            {**VALIDO, "activo": "false"}, {"precio": "100"},  # sin nombre
        ]
        for datos in invalidos:
            with self.subTest(datos=str(datos)[:60]):
                self.assertEqual(enviar(self.client, "post", "/api/productos/", datos).status_code, 400)
        self.assertEqual(enviar(self.client, "post", "/api/productos/", '{"nombre": "x", "precio": NaN}')
                         .status_code, 400)
        self.assertEqual(Producto.objects.count(), 1)

    def test_no_se_pueden_fijar_campos_internos_asignacion_masiva(self):
        for extra in ({"id": 999}, {"creado_en": "2020-01-01"}, {"agotado": True}):
            with self.subTest(extra=extra):
                self.assertEqual(enviar(self.client, "post", "/api/productos/", {**VALIDO, **extra}).status_code, 400)
                url = f"/api/productos/{self.producto.pk}/"
                self.assertEqual(enviar(self.client, "patch", url, extra).status_code, 400)
        self.assertFalse(Producto.objects.filter(pk=999).exists())

    def test_editar_producto_inexistente_responde_404(self):
        self.assertEqual(enviar(self.client, "patch", "/api/productos/999999/", {"stock": 1}).status_code, 404)


class IntegridadYXssHU03Tests(TestCase):
    def setUp(self):
        self.admin = fabricas.administrador()
        self.producto = fabricas.producto("Teclado", "150000", stock=5)

    def test_cambiar_el_precio_no_altera_pedidos_ya_pagados(self):
        cliente = fabricas.cliente()
        fabricas.pedido(cliente, [(self.producto, 1)])
        self.client.force_login(self.admin)
        enviar(self.client, "patch", f"/api/productos/{self.producto.pk}/", {"precio": "999999"})

        self.assertEqual(ItemPedido.objects.get().precio_pactado, Decimal("150000"))

    def test_un_producto_retirado_no_se_puede_comprar(self):
        self.client.force_login(self.admin)
        enviar(self.client, "patch", f"/api/productos/{self.producto.pk}/", {"activo": False})
        self.client.force_login(fabricas.cliente())
        cuerpo = {"items": [{"id_producto": self.producto.pk, "cantidad": 1}], "envio": fabricas.ENVIO}
        self.assertEqual(enviar(self.client, "post", "/api/pedidos/", cuerpo).status_code, 404)

    def test_xss_en_el_nombre_se_muestra_escapado_en_la_tienda(self):
        self.client.force_login(self.admin)
        enviar(self.client, "post", "/api/productos/", {**VALIDO, "nombre": XSS})
        for url in ("/", "/gestion/productos/"):
            with self.subTest(url=url):
                html = self.client.get(url).content.decode()
                self.assertNotIn(XSS, html)
                self.assertIn("&lt;script&gt;", html)


class AuditoriaYCsrfHU03Tests(TestCase):
    def test_crear_y_editar_quedan_en_auditoria(self):
        admin = fabricas.administrador()
        self.client.force_login(admin)
        creado = enviar(self.client, "post", "/api/productos/", VALIDO).json()
        enviar(self.client, "patch", f"/api/productos/{creado['id']}/", {"stock": 9, "activo": False})

        eventos = EventoAuditoria.objects.filter(usuario=admin).order_by("id")
        self.assertEqual([e.tipo for e in eventos], ["PRODUCTO_CREADO", "PRODUCTO_EDITADO"])
        self.assertIn("stock: 3 -> 9", eventos[1].detalle)
        self.assertIn("activo: True -> False", eventos[1].detalle)

    def test_la_api_y_la_web_exigen_csrf(self):
        navegador = Client(enforce_csrf_checks=True)
        navegador.force_login(fabricas.administrador())
        self.assertEqual(enviar(navegador, "post", "/api/productos/", VALIDO).status_code, 403)
        self.assertEqual(navegador.post("/gestion/productos/nuevo/", VALIDO).status_code, 403)
        self.assertFalse(Producto.objects.exists())

    def test_positivo_el_administrador_crea_edita_y_retira_desde_la_web(self):
        self.client.force_login(fabricas.administrador())
        self.client.post("/gestion/productos/nuevo/", {**VALIDO, "activo": "on"})
        producto = Producto.objects.get()
        self.client.post(f"/gestion/productos/{producto.pk}/",
                         {"nombre": "Lámpara LED", "precio": "55000", "stock": "4", "activo": "on"})
        self.client.post(f"/gestion/productos/{producto.pk}/activo/", {"activo": "0"})

        producto.refresh_from_db()
        self.assertEqual((producto.nombre, producto.precio, producto.stock, producto.activo),
                         ("Lámpara LED", Decimal("55000"), 4, False))
