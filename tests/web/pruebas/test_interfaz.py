"""Pruebas de la interfaz web: flujo del cliente, del agente y control de acceso
por rol (HU-01 criterios 3 y 4, HU-04 criterio 1, HU-05, HU-06, HU-07, HU-08).

La web usa los mismos servicios que la API, así que estas pruebas se centran
en lo propio de la web: sesión, rol, CSRF en formularios y que lo ajeno no
se pueda ver."""

from django.core.cache import cache
from django.test import Client, TestCase

from carrito.models import Pedido
from comun import fabricas
from soporte.models import TicketSoporte


class AccesoPorRolTests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente()
        self.agente = fabricas.agente()

    def test_anonimo_ve_el_catalogo_pero_las_rutas_protegidas_piden_entrar(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        for url in ["/carrito/", "/pedidos/", "/pqr/", "/pqr/nueva/", "/agente/"]:
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 302)
                self.assertTrue(respuesta["Location"].startswith("/entrar/?next="))

    def test_cliente_no_entra_al_panel_de_agente_y_agente_no_usa_el_carrito(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get("/agente/").status_code, 403)

        self.client.force_login(self.agente)
        self.assertEqual(self.client.get("/carrito/").status_code, 403)
        self.assertEqual(self.client.get("/agente/").status_code, 200)

    def test_el_menu_muestra_solo_las_opciones_del_rol(self):
        self.client.force_login(self.cliente)
        html = self.client.get("/").content.decode()
        self.assertIn("Mis PQR", html)
        self.assertNotIn("Cola de PQR", html)

        self.client.force_login(self.agente)
        html = self.client.get("/agente/").content.decode()
        self.assertIn("Cola de PQR", html)
        self.assertNotIn("Mis pedidos", html)


class FlujoClienteTests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente()
        self.teclado = fabricas.producto("Teclado", "150000", stock=5)
        self.mouse = fabricas.producto("Mouse", "60000", stock=5)
        self.client.force_login(self.cliente)

    def test_agregar_cambiar_quitar_y_pagar_el_carrito(self):
        # HU-04 criterio 1: el carrito se edita antes de pagar.
        self.client.post("/carrito/agregar/", {"id_producto": self.teclado.pk, "cantidad": 1})
        self.client.post("/carrito/agregar/", {"id_producto": self.mouse.pk, "cantidad": 1})
        self.client.post("/carrito/actualizar/", {"id_producto": self.teclado.pk, "cantidad": 2})
        self.client.post("/carrito/quitar/", {"id_producto": self.mouse.pk})

        carrito = self.client.get("/carrito/")
        self.assertContains(carrito, "$300.000")  # 2 x 150.000
        self.assertNotContains(carrito, "Mouse")

        respuesta = self.client.post("/carrito/pagar/")
        pedido = Pedido.objects.get()
        self.assertRedirects(respuesta, f"/pedidos/{pedido.pk}/")
        self.assertEqual(pedido.cliente, self.cliente)
        self.teclado.refresh_from_db()
        self.assertEqual(self.teclado.stock, 3)
        self.assertNotContains(self.client.get("/carrito/"), "Teclado")  # quedó vacío

    def test_pagar_sin_stock_no_crea_pedido_y_conserva_el_carrito(self):
        self.client.post("/carrito/agregar/", {"id_producto": self.teclado.pk, "cantidad": 5})
        self.teclado.stock = 1
        self.teclado.save()

        respuesta = self.client.post("/carrito/pagar/", follow=True)
        self.assertContains(respuesta, "Stock insuficiente")
        self.assertFalse(Pedido.objects.exists())
        self.assertContains(self.client.get("/carrito/"), "Teclado")

    def test_radicar_pqr_sobre_mi_pedido_y_verla_en_mis_pqr(self):
        pedido = fabricas.pedido(self.cliente, [(self.teclado, 1)])
        respuesta = self.client.post(
            "/pqr/nueva/",
            {"tipo": "RECLAMO", "pedido": pedido.pk, "asunto": "Tecla suelta",
             "descripcion": "La tecla Enter llegó suelta"},
        )
        ticket = TicketSoporte.objects.get()
        self.assertRedirects(respuesta, f"/pqr/{ticket.pk}/")
        self.assertEqual((ticket.cliente, ticket.pedido, ticket.tipo), (self.cliente, pedido, "RECLAMO"))
        self.assertContains(self.client.get("/pqr/"), ticket.numero)  # HU-06

    def test_no_se_puede_radicar_pqr_sobre_pedido_ajeno(self):
        ajeno = fabricas.pedido(fabricas.cliente("otro"), [(self.teclado, 1)])
        respuesta = self.client.post(
            "/pqr/nueva/", {"tipo": "QUEJA", "pedido": ajeno.pk, "asunto": "x", "descripcion": "x"}
        )
        self.assertEqual(respuesta.status_code, 200)  # el formulario vuelve con error
        self.assertFalse(TicketSoporte.objects.exists())

    def test_lo_ajeno_responde_404(self):
        otro = fabricas.cliente("otro")
        pedido_ajeno = fabricas.pedido(otro, [(self.teclado, 1)])
        ticket_ajeno = fabricas.ticket(otro)
        self.assertEqual(self.client.get(f"/pedidos/{pedido_ajeno.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/pqr/{ticket_ajeno.pk}/").status_code, 404)

    def test_el_contenido_del_usuario_se_escapa(self):
        fabricas.ticket(self.cliente, descripcion="<script>alert('xss')</script>")
        html = self.client.get(f"/pqr/{TicketSoporte.objects.get().pk}/").content.decode()
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;", html)


class FlujoAgenteTests(TestCase):
    def setUp(self):
        self.cliente = fabricas.cliente()
        self.agente1 = fabricas.agente("agente1")
        self.agente2 = fabricas.agente("agente2")
        self.ticket = fabricas.ticket(self.cliente)

    def test_el_segundo_agente_ve_el_aviso_de_ticket_ya_asignado(self):
        self.client.force_login(self.agente1)
        self.assertRedirects(self.client.post(f"/agente/tickets/{self.ticket.pk}/tomar/"),
                             f"/pqr/{self.ticket.pk}/")

        self.client.force_login(self.agente2)
        respuesta = self.client.post(f"/agente/tickets/{self.ticket.pk}/tomar/", follow=True)
        self.assertContains(respuesta, "El ticket ya fue asignado")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.agente, self.agente1)

    def test_el_agente_ve_el_pedido_asociado_al_ticket(self):
        # HU-09: desde el ticket se ve qué compró el cliente.
        pedido = fabricas.pedido(self.cliente, [(fabricas.producto("Monitor"), 1)])
        ticket = fabricas.ticket(self.cliente, pedido_obj=pedido)
        self.client.force_login(self.agente1)
        self.assertContains(self.client.get(f"/pqr/{ticket.pk}/"), "Monitor")


class SeguridadWebTests(TestCase):
    def setUp(self):
        cache.clear()
        self.cliente = fabricas.cliente("ana@example.com")

    def test_los_formularios_exigen_csrf(self):
        navegador = Client(enforce_csrf_checks=True)
        navegador.force_login(self.cliente)
        producto = fabricas.producto()
        respuesta = navegador.post("/carrito/agregar/", {"id_producto": producto.pk})
        self.assertEqual(respuesta.status_code, 403)
        self.assertContains(respuesta, "El formulario expiró", status_code=403)

    def test_entrar_no_redirige_a_sitios_externos(self):
        respuesta = self.client.post(
            "/entrar/?next=https://malicioso.example/",
            {"usuario": "ana@example.com", "clave": "clave123", "next": "https://malicioso.example/"},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta["Location"], "/")

    def test_registro_crea_cliente_y_entra(self):
        respuesta = self.client.post(
            "/registro/",
            {"nombre": "Nuevo", "email": "nuevo@example.com",
             "clave": "Una-clave-larga-2026", "clave2": "Una-clave-larga-2026"},
        )
        self.assertRedirects(respuesta, "/")
        self.assertContains(self.client.get("/"), "Mis PQR")

    def test_salir_solo_por_post(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get("/salir/").status_code, 405)
        self.client.post("/salir/")
        self.assertEqual(self.client.get("/pedidos/").status_code, 302)
