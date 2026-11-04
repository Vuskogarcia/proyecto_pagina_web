"""Pruebas de seguridad: una clase por recomendación del AI Decision Log
(docs/seguridad/ai-decision-log-seguridad.md).

Método (ADL-10): cada prueba se escribió ANTES de la corrección y se vio
fallar (prueba roja). Cada una afirma también sobre la base de datos (que
no se creó / no cambió nada) y trae al menos un caso positivo, para que un
"OK" no pueda deberse a que el endpoint rechaza todo.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from django.core.cache import cache
from django.test import Client, TestCase

from carrito.models import Pedido
from comun import fabricas
from soporte.models import TicketSoporte

DIR_PROYECTO = Path(__file__).resolve().parents[2]


def post_json(cliente_http, url, datos=None, cuerpo_crudo=None, **extra):
    cuerpo = cuerpo_crudo if cuerpo_crudo is not None else json.dumps(datos or {})
    return cliente_http.post(url, data=cuerpo, content_type="application/json", **extra)


class ADL01IdentidadDesdeLaSesionTests(TestCase):
    """H1-H3: la identidad venía en el cuerpo JSON; cualquiera podía comprar,
    crear tickets o tomarlos a nombre de otro usuario."""

    def setUp(self):
        self.victima = fabricas.cliente("victima")
        self.atacante = fabricas.cliente("atacante")
        self.agente = fabricas.agente("agente1")
        self.producto = fabricas.producto(stock=5)

    def test_sin_sesion_la_api_protegida_responde_401_y_no_cambia_nada(self):
        items = [{"id_producto": self.producto.pk, "cantidad": 1}]
        self.assertEqual(post_json(self.client, "/api/pedidos/", {"items": items, "envio": fabricas.ENVIO}).status_code, 401)
        self.assertEqual(
            post_json(self.client, "/api/tickets/", {"descripcion": "x"}).status_code, 401
        )
        ticket = fabricas.ticket(self.victima)
        self.assertEqual(post_json(self.client, f"/api/tickets/{ticket.pk}/tomar/").status_code, 401)
        self.assertEqual(self.client.get("/api/tickets/cola/").status_code, 401)

        self.assertFalse(Pedido.objects.exists())
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 5)
        ticket.refresh_from_db()
        self.assertIsNone(ticket.agente)

    def test_el_cuerpo_ya_no_puede_suplantar_a_otro_usuario(self):
        self.client.force_login(self.atacante)
        items = [{"id_producto": self.producto.pk, "cantidad": 1}]

        r1 = post_json(self.client, "/api/pedidos/", {"id_cliente": self.victima.pk, "items": items, "envio": fabricas.ENVIO})
        r2 = post_json(
            self.client, "/api/tickets/", {"id_cliente": self.victima.pk, "descripcion": "x"}
        )

        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r2.status_code, 400)
        self.assertFalse(Pedido.objects.exists())
        self.assertFalse(TicketSoporte.objects.exists())

    def test_positivo_el_pedido_y_el_ticket_quedan_a_nombre_del_usuario_en_sesion(self):
        self.client.force_login(self.atacante)
        items = [{"id_producto": self.producto.pk, "cantidad": 2}]

        pedido = post_json(self.client, "/api/pedidos/", {"items": items, "envio": fabricas.ENVIO})
        ticket = post_json(self.client, "/api/tickets/", {"descripcion": "Llegó roto"})

        self.assertEqual(pedido.status_code, 201)
        self.assertEqual(ticket.status_code, 201)
        self.assertEqual(Pedido.objects.get().cliente, self.atacante)
        self.assertEqual(TicketSoporte.objects.get().cliente, self.atacante)

    def test_tomar_ticket_usa_el_agente_en_sesion(self):
        ticket = fabricas.ticket(self.victima)
        otro_agente = fabricas.agente("agente2")
        self.client.force_login(self.agente)

        # Intentar asignárselo a otro agente por el cuerpo: rechazado.
        rechazo = post_json(
            self.client, f"/api/tickets/{ticket.pk}/tomar/", {"id_agente": otro_agente.pk}
        )
        self.assertEqual(rechazo.status_code, 400)
        ticket.refresh_from_db()
        self.assertIsNone(ticket.agente)

        exito = post_json(self.client, f"/api/tickets/{ticket.pk}/tomar/")
        self.assertEqual(exito.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.agente, self.agente)

    def test_la_cola_es_solo_para_agentes(self):
        fabricas.ticket(self.victima)
        self.client.force_login(self.atacante)
        self.assertEqual(self.client.get("/api/tickets/cola/").status_code, 403)

        self.client.force_login(self.agente)
        respuesta = self.client.get("/api/tickets/cola/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.json()["tickets"]), 1)


class ADL03ObjetosAjenosResponden404Tests(TestCase):
    """H10: un objeto ajeno respondía distinto que uno inexistente, lo que
    permitía enumerar pedidos y tickets. Decisión del equipo: 404 en ambos."""

    def setUp(self):
        self.duenio = fabricas.cliente("duenio")
        self.intruso = fabricas.cliente("intruso")
        self.pedido = fabricas.pedido(self.duenio, [(fabricas.producto(), 1)])
        self.ticket = fabricas.ticket(self.duenio, pedido_obj=self.pedido)

    def test_pedido_y_ticket_ajenos_se_ven_igual_que_inexistentes(self):
        self.client.force_login(self.intruso)
        for url_ajena, url_inexistente in [
            (f"/api/pedidos/{self.pedido.pk}/", "/api/pedidos/999999/"),
            (f"/api/tickets/{self.ticket.pk}/", "/api/tickets/999999/"),
        ]:
            with self.subTest(url=url_ajena):
                ajena = self.client.get(url_ajena)
                inexistente = self.client.get(url_inexistente)
                self.assertEqual(ajena.status_code, 404)
                self.assertEqual(inexistente.status_code, 404)
                self.assertEqual(ajena.json().keys(), inexistente.json().keys())

    def test_crear_ticket_con_pedido_ajeno_responde_404_y_no_crea_nada(self):
        self.client.force_login(self.intruso)
        respuesta = post_json(
            self.client, "/api/tickets/", {"descripcion": "x", "id_pedido": self.pedido.pk}
        )
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(TicketSoporte.objects.count(), 1)

    def test_positivo_el_duenio_y_los_agentes_si_ven_el_pedido_y_el_ticket(self):
        for usuario in (self.duenio, fabricas.agente("agente1")):
            self.client.force_login(usuario)
            with self.subTest(usuario=usuario.username):
                self.assertEqual(self.client.get(f"/api/pedidos/{self.pedido.pk}/").status_code, 200)
                self.assertEqual(self.client.get(f"/api/tickets/{self.ticket.pk}/").status_code, 200)


class ADL04ValidacionConListaDePermitidosYCotasTests(TestCase):
    """H5/H6: entero() aceptaba floats (1.9 -> 1), dígitos no ASCII y números
    sin cota; en PostgreSQL un id enorme terminaba en un 500."""

    def setUp(self):
        self.cliente = fabricas.cliente()
        self.producto = fabricas.producto(stock=5)
        self.client.force_login(self.cliente)

    def checkout(self, id_producto, cantidad):
        return post_json(
            self.client,
            "/api/pedidos/",
            {"items": [{"id_producto": id_producto, "cantidad": cantidad}], "envio": fabricas.ENVIO},
        )

    def test_valores_fuera_de_la_lista_de_permitidos_responden_400(self):
        for id_producto, cantidad in [
            (self.producto.pk, 1.9),  # float truncado
            (self.producto.pk, "١"),  # dígito árabe: int("١") == 1
            (self.producto.pk, " 1"),  # espacios
            (10**30, 1),  # id enorme
            (self.producto.pk, 10**30),  # cantidad enorme
            (self.producto.pk, 1001),  # supera la cota de negocio por item
        ]:
            with self.subTest(id_producto=id_producto, cantidad=cantidad):
                self.assertEqual(self.checkout(id_producto, cantidad).status_code, 400)
        self.assertFalse(Pedido.objects.exists())

    def test_id_enorme_en_la_url_responde_404_y_no_500(self):
        self.assertEqual(self.client.get("/api/productos/99999999999999999999/").status_code, 404)
        self.assertEqual(self.client.get("/api/pedidos/99999999999999999999/").status_code, 404)

    def test_campos_desconocidos_en_el_cuerpo_responden_400(self):
        respuesta = post_json(
            self.client,
            "/api/pedidos/",
            {"items": [{"id_producto": self.producto.pk, "cantidad": 1}], "envio": fabricas.ENVIO, "precio": "1"},
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(Pedido.objects.exists())

    def test_positivo_entero_como_numero_o_como_texto_de_digitos(self):
        self.assertEqual(self.checkout(self.producto.pk, 1).status_code, 201)
        self.assertEqual(self.checkout(str(self.producto.pk), "2").status_code, 201)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 2)


class ADL05TextoConNulYSurrogatesTests(TestCase):
    """H7/H8: PostgreSQL no acepta NUL (\\x00) ni surrogates sueltos en un
    campo de texto; llegaban hasta la base de datos y producían un 500."""

    def setUp(self):
        self.cliente = fabricas.cliente()
        self.client.force_login(self.cliente)

    def test_nul_y_surrogate_suelto_responden_400_y_no_crean_ticket(self):
        for cuerpo in [
            json.dumps({"descripcion": "antes\x00despues"}),
            '{"descripcion": "roto \\ud800"}',
            '{"asunto": "\\udfff", "descripcion": "ok"}',
        ]:
            with self.subTest(cuerpo=cuerpo):
                respuesta = post_json(self.client, "/api/tickets/", cuerpo_crudo=cuerpo)
                self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(TicketSoporte.objects.exists())

    def test_positivo_tildes_y_emoji_si_se_aceptan(self):
        respuesta = post_json(self.client, "/api/tickets/", {"descripcion": "Llegó roto 📦 ñandú"})
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(TicketSoporte.objects.get().descripcion, "Llegó roto 📦 ñandú")


class ADL06RedGenericaDeExcepcionesTests(TestCase):
    """H4: un error no previsto salía como 500 de Django (con traceback si
    DEBUG=True). Ahora: JSON genérico al cliente y detalle solo en el log."""

    def test_error_inesperado_responde_500_generico_y_queda_en_el_log(self):
        with mock.patch(
            "catalogo.servicios.listar_catalogo", side_effect=RuntimeError("detalle-interno-secreto")
        ), self.assertLogs("shophub", level="ERROR") as log:
            respuesta = self.client.get("/api/productos/")

        self.assertEqual(respuesta.status_code, 500)
        self.assertEqual(respuesta["Content-Type"], "application/json")
        self.assertNotIn("detalle-interno-secreto", respuesta.content.decode())
        self.assertIn("detalle-interno-secreto", "\n".join(log.output))

    def test_positivo_los_errores_de_negocio_conservan_su_codigo(self):
        self.assertEqual(self.client.get("/api/productos/999/").status_code, 404)


class ADL07ConfiguracionSeguraPorDefectoTests(TestCase):
    """H11: DEBUG era True por defecto y había un SECRET_KEY de respaldo."""

    def cargar_settings(self, **variables):
        entorno = {k: v for k, v in os.environ.items() if k not in ("DEBUG", "SECRET_KEY")}
        entorno.update(variables, ENV_FILE=os.devnull, DJANGO_SETTINGS_MODULE="config.settings")
        return subprocess.run(
            [sys.executable, "-c", "from django.conf import settings; print(settings.DEBUG)"],
            cwd=DIR_PROYECTO,
            env=entorno,
            capture_output=True,
            text=True,
        )

    def test_sin_secret_key_no_arranca(self):
        resultado = self.cargar_settings()
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn("SECRET_KEY", resultado.stderr)

    def test_secret_key_de_ejemplo_no_se_acepta_en_produccion(self):
        resultado = self.cargar_settings(SECRET_KEY="django-insecure-algo")
        self.assertNotEqual(resultado.returncode, 0)

    def test_positivo_con_clave_propia_debug_queda_apagado_por_defecto(self):
        resultado = self.cargar_settings(SECRET_KEY="x" * 60)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
        self.assertEqual(resultado.stdout.strip(), "False")


class H13CsrfConSesionTests(TestCase):
    """H13: era falso positivo mientras no había sesiones. Con login (HU-01)
    las peticiones que cambian datos deben llevar token CSRF."""

    def test_sin_token_csrf_responde_403_json_y_con_token_201(self):
        cliente = fabricas.cliente()
        navegador = Client(enforce_csrf_checks=True)
        navegador.force_login(cliente)

        sin_token = post_json(navegador, "/api/tickets/", {"descripcion": "x"})
        self.assertEqual(sin_token.status_code, 403)
        self.assertEqual(sin_token["Content-Type"], "application/json")
        self.assertFalse(TicketSoporte.objects.exists())

        token = navegador.get("/api/sesion/").cookies["csrftoken"].value
        con_token = post_json(navegador, "/api/tickets/", {"descripcion": "x"}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(con_token.status_code, 201)


class H14AgentesSinAccesoAlAdminTests(TestCase):
    """H14: los agentes eran is_staff y podían entrar a /admin/. El rol de
    agente ahora es el grupo 'agentes', sin acceso al panel de administración."""

    def test_agente_no_entra_al_admin_pero_si_toma_tickets(self):
        agente = fabricas.agente()
        self.client.force_login(agente)
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        ticket = fabricas.ticket(fabricas.cliente())
        self.assertEqual(post_json(self.client, f"/api/tickets/{ticket.pk}/tomar/").status_code, 200)


class SesionYRegistroTests(TestCase):
    """HU-01 (base de ADL-01): registro, inicio de sesión y límite de intentos."""

    def setUp(self):
        cache.clear()
        self.usuario = fabricas.cliente("ana@example.com")

    def entrar(self, clave):
        return post_json(self.client, "/api/sesion/", {"usuario": "ana@example.com", "clave": clave})

    def test_login_correcto_y_mensaje_igual_para_usuario_o_clave_incorrectos(self):
        mala_clave = self.entrar("incorrecta")
        no_existe = post_json(self.client, "/api/sesion/", {"usuario": "nadie@x.com", "clave": "x"})
        self.assertEqual(mala_clave.status_code, 401)
        self.assertEqual(mala_clave.json(), no_existe.json())

        bien = self.entrar("clave123")
        self.assertEqual(bien.status_code, 200)
        self.assertEqual(bien.json()["rol"], "cliente")

    def test_tras_5_intentos_fallidos_se_bloquea_aunque_la_clave_sea_correcta(self):
        for _ in range(5):
            self.assertEqual(self.entrar("incorrecta").status_code, 401)
        self.assertEqual(self.entrar("clave123").status_code, 429)

    def test_registro_crea_cliente_y_no_permite_elegir_rol(self):
        datos = {"email": "nuevo@example.com", "clave": "Una-clave-larga-2026", "nombre": "Nuevo"}
        con_rol = post_json(self.client, "/api/registro/", {**datos, "rol": "agente"})
        self.assertEqual(con_rol.status_code, 400)

        debil = post_json(self.client, "/api/registro/", {**datos, "clave": "123"})
        self.assertEqual(debil.status_code, 400)

        ok = post_json(self.client, "/api/registro/", datos)
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(ok.json()["rol"], "cliente")


class CabecerasDeSeguridadTests(TestCase):
    def test_respuestas_llevan_csp_y_cabeceras_basicas(self):
        respuesta = self.client.get("/api/productos/")
        self.assertIn("default-src 'self'", respuesta["Content-Security-Policy"])
        self.assertEqual(respuesta["X-Frame-Options"], "DENY")
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        self.assertIn("Referrer-Policy", respuesta)
