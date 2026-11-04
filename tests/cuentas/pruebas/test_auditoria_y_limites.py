"""Registro de eventos críticos (guía §4) y límite de peticiones (guía §5,
disponibilidad). Cada prueba consulta la tabla de auditoría en PostgreSQL."""

import json

from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from carrito.models import Pedido
from comun import fabricas
from cuentas.models import EventoAuditoria as E
from soporte.models import TicketSoporte


def post_json(cliente_http, url, datos=None, **extra):
    return cliente_http.post(url, data=json.dumps(datos or {}), content_type="application/json", **extra)


def tipos():
    return list(E.objects.order_by("id").values_list("tipo", flat=True))


class RegistroDeEventosCriticosTests(TestCase):
    def setUp(self):
        cache.clear()
        self.cliente = fabricas.cliente("ana@example.com")

    def test_login_fallido_exitoso_y_salida_quedan_registrados_sin_la_clave(self):
        post_json(self.client, "/api/sesion/", {"usuario": "ana@example.com", "clave": "clave-mala-secreta"})
        post_json(self.client, "/api/sesion/", {"usuario": "ana@example.com", "clave": "clave123"})
        self.client.delete("/api/sesion/")

        self.assertEqual(tipos(), [E.LOGIN_FALLIDO, E.LOGIN_OK, E.LOGOUT])
        fallido = E.objects.get(tipo=E.LOGIN_FALLIDO)
        self.assertEqual((fallido.usuario_intentado, fallido.ip), ("ana@example.com", "127.0.0.1"))
        guardado = " ".join(str(v) for v in E.objects.values_list("detalle", "usuario_intentado", "ruta"))
        self.assertNotIn("clave-mala-secreta", guardado)
        self.assertNotIn("clave123", guardado)

    def test_operaciones_de_negocio_y_conflicto_409_quedan_registradas(self):
        producto = fabricas.producto(stock=5)
        self.client.force_login(self.cliente)
        post_json(self.client, "/api/pedidos/", {"items": [{"id_producto": producto.pk, "cantidad": 1}]})
        post_json(self.client, "/api/tickets/", {"descripcion": "No llegó"})
        ticket = TicketSoporte.objects.get()
        for agente in (fabricas.agente("agente1"), fabricas.agente("agente2")):
            self.client.force_login(agente)
            post_json(self.client, f"/api/tickets/{ticket.pk}/tomar/")

        self.assertEqual(tipos(), [E.PEDIDO_CREADO, E.TICKET_CREADO, E.TICKET_TOMADO, E.TICKET_CONFLICTO])
        self.assertIn(Pedido.objects.get().codigo, E.objects.get(tipo=E.PEDIDO_CREADO).detalle)
        self.assertEqual(E.objects.get(tipo=E.TICKET_CONFLICTO).usuario.username, "agente2")

    def test_accesos_denegados_csrf_y_error_interno_quedan_registrados(self):
        self.client.get("/api/tickets/cola/")  # 401
        self.client.force_login(self.cliente)
        self.client.get("/api/tickets/cola/")  # 403
        self.client.get("/agente/")  # 403 web
        navegador = Client(enforce_csrf_checks=True)
        navegador.force_login(self.cliente)
        post_json(navegador, "/api/tickets/", {"descripcion": "x"})  # sin token

        self.assertEqual(tipos(), [E.ACCESO_DENEGADO] * 3 + [E.CSRF_RECHAZADO])

    def test_un_pedido_revertido_no_deja_evento(self):
        # Sin stock: el checkout se revierte completo, incluido su evento.
        producto = fabricas.producto(stock=0)
        self.client.force_login(self.cliente)
        respuesta = post_json(self.client, "/api/pedidos/", {"items": [{"id_producto": producto.pk, "cantidad": 1}]})
        self.assertEqual(respuesta.status_code, 409)
        self.assertFalse(E.objects.filter(tipo=E.PEDIDO_CREADO).exists())

    def test_el_admin_solo_puede_leer_el_registro(self):
        admin = fabricas.cliente("admin")
        admin.is_staff = admin.is_superuser = True
        admin.save()
        self.client.force_login(admin)
        self.assertEqual(self.client.get("/admin/cuentas/eventoauditoria/").status_code, 200)
        self.assertEqual(self.client.get("/admin/cuentas/eventoauditoria/add/").status_code, 403)


@override_settings(LIMITE_ESCRITURAS_POR_MINUTO=3, LIMITE_REGISTROS_POR_HORA=2)
class LimiteDePeticionesTests(TestCase):
    def setUp(self):
        cache.clear()
        self.cliente = fabricas.cliente()

    def test_api_cuarta_escritura_en_el_minuto_responde_429_y_no_crea_nada(self):
        self.client.force_login(self.cliente)
        codigos = [post_json(self.client, "/api/tickets/", {"descripcion": f"#{i}"}).status_code
                   for i in range(4)]

        self.assertEqual(codigos, [201, 201, 201, 429])
        self.assertEqual(TicketSoporte.objects.count(), 3)
        self.assertEqual(self.client.get("/api/tickets/").status_code, 200)  # leer sigue permitido
        self.assertTrue(E.objects.filter(tipo=E.LIMITE_EXCEDIDO).exists())

    def test_el_limite_es_por_usuario(self):
        self.client.force_login(self.cliente)
        for i in range(3):
            post_json(self.client, "/api/tickets/", {"descripcion": f"#{i}"})
        self.client.force_login(fabricas.cliente("otro"))
        self.assertEqual(post_json(self.client, "/api/tickets/", {"descripcion": "x"}).status_code, 201)

    def test_web_tambien_limita_y_muestra_pagina_429(self):
        self.client.force_login(self.cliente)
        producto = fabricas.producto()
        codigos = [self.client.post("/carrito/agregar/", {"id_producto": producto.pk}).status_code
                   for _ in range(4)]
        self.assertEqual(codigos, [302, 302, 302, 429])

    def test_registro_limitado_por_ip(self):
        codigos = [
            post_json(self.client, "/api/registro/",
                      {"email": f"n{i}@example.com", "clave": "Una-clave-larga-2026"}).status_code
            for i in range(3)
        ]
        self.assertEqual(codigos, [201, 201, 429])
