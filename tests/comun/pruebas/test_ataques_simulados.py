"""Pruebas de seguridad básicas con ataques simulados (guía Módulo 7, semana 13, §6).

Una clase por ataque de la guía, con su ejemplo literal cuando aplica:

| Ataque                      | Ejemplo de la guía              | Resultado esperado          |
| --------------------------- | ------------------------------- | --------------------------- |
| Inyección SQL               | ' OR 1=1 --                     | bloqueado                   |
| XSS                         | <script>alert(1)</script>       | neutralizado                |
| IDOR                        | /usuario/1002 (aquí: pedidos)   | autorizado (404 si ajeno)   |
| Divulgación de información  | /error?debug=true               | sin datos sensibles         |
| Fuerza bruta de login       | múltiples intentos              | limitado (429)              |

Deben correr contra PostgreSQL (la base real del proyecto): ver
docs/seguridad/semana-13.md para la evidencia ejecutada.
"""

import json
import os
import re
import uuid
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from carrito.models import Pedido
from catalogo.models import Producto
from comun import fabricas
from soporte.models import TicketSoporte

SQLI = "' OR 1=1 --"
XSS = "<script>alert(1)</script>"
DIR_PROYECTO = Path(__file__).resolve().parents[2]


def post_json(cliente_http, url, datos):
    return cliente_http.post(url, data=json.dumps(datos), content_type="application/json")


class InyeccionSqlTests(TestCase):
    """Ejemplo de la guía: ' OR 1=1 --  →  debe ser bloqueado."""

    def setUp(self):
        cache.clear()
        self.cliente = fabricas.cliente("ana@example.com")
        self.producto = fabricas.producto()

    def test_login_con_or_1_1_no_entra(self):
        for usuario, clave in [(SQLI, "x"), ("ana@example.com", SQLI), (f"ana@example.com{SQLI}", "x")]:
            with self.subTest(usuario=usuario, clave=clave):
                respuesta = post_json(self.client, "/api/sesion/", {"usuario": usuario, "clave": clave})
                self.assertEqual(respuesta.status_code, 401)
        self.assertFalse(self.client.get("/api/sesion/").json()["autenticado"])

    def test_la_carga_se_guarda_como_texto_y_no_se_ejecuta(self):
        self.client.force_login(self.cliente)
        carga = f"{SQLI}; DROP TABLE soporte_ticketsoporte; --"
        respuesta = post_json(self.client, "/api/tickets/", {"asunto": SQLI, "descripcion": carga})

        self.assertEqual(respuesta.status_code, 201)
        ticket = TicketSoporte.objects.get()  # la tabla sigue existiendo
        self.assertEqual(ticket.descripcion, carga)  # guardado literal, sin ejecutarse
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_la_carga_en_parametros_y_urls_no_cambia_la_consulta(self):
        self.client.force_login(fabricas.agente())
        fabricas.ticket(self.cliente)

        cola = self.client.get("/api/tickets/cola/", {"orden": f"creado_en{SQLI}"})
        # Orden fuera de la lista de permitidos: 400 (antes se ignoraba y daba 200).
        self.assertEqual(cola.status_code, 400)
        self.assertEqual(len(self.client.get("/api/tickets/cola/").json()["tickets"]), 1)
        self.assertEqual(self.client.get(f"/api/productos/1{SQLI}/").status_code, 404)
        self.assertEqual(Producto.objects.count(), 1)

    def test_el_codigo_no_arma_sql_a_mano(self):
        """Guardia estática: toda consulta pasa por el ORM (parametrizada).

        Si alguien agrega SQL crudo, esta prueba falla y obliga a revisarlo."""
        prohibido = re.compile(r"\.raw\(|\.extra\(|cursor\(\)|RawSQL\(")
        excluidas = {"venv", ".venv", "migrations", "pruebas", "staticfiles", "__pycache__", ".git"}
        hallazgos = []
        # os.walk podando carpetas: no recorre el venv (miles de archivos).
        for raiz, carpetas, archivos in os.walk(DIR_PROYECTO):
            carpetas[:] = [c for c in carpetas if c not in excluidas]
            for nombre in archivos:
                if not nombre.endswith(".py"):
                    continue
                ruta = Path(raiz) / nombre
                for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
                    if prohibido.search(linea):
                        hallazgos.append(f"{ruta.relative_to(DIR_PROYECTO)}:{numero}")
        self.assertEqual(hallazgos, [])


class XssTests(TestCase):
    """Ejemplo de la guía: <script>alert(1)</script>  →  debe ser neutralizado."""

    def setUp(self):
        self.cliente = fabricas.cliente()
        self.agente = fabricas.agente()
        self.ticket = fabricas.ticket(self.cliente, descripcion=XSS)
        self.ticket.asunto = XSS
        self.ticket.save()

    def test_el_agente_y_el_cliente_ven_el_script_escapado(self):
        for usuario, url in [(self.agente, "/agente/"), (self.agente, f"/pqr/{self.ticket.pk}/"),
                             (self.cliente, "/pqr/"), (self.cliente, f"/pqr/{self.ticket.pk}/")]:
            with self.subTest(usuario=usuario.username, url=url):
                self.client.force_login(usuario)
                html = self.client.get(url).content.decode()
                self.assertNotIn(XSS, html)
                self.assertIn("&lt;script&gt;", html)

    def test_la_csp_impide_ejecutar_scripts_en_linea(self):
        politica = self.client.get("/")["Content-Security-Policy"]
        self.assertIn("script-src 'self'", politica)
        self.assertNotIn("unsafe-inline", politica)


class IdorTests(TestCase):
    """Ejemplo de la guía: /usuario/1002  →  debe estar autorizado.

    El proyecto no expone usuarios por id; el equivalente son pedidos y
    tickets. Un intruso que recorre ids consecutivos no ve nada ajeno."""

    def test_recorrer_ids_consecutivos_no_revela_pedidos_ni_tickets_ajenos(self):
        victima, intruso = fabricas.cliente("victima"), fabricas.cliente("intruso")
        producto = fabricas.producto()
        ajenos = [fabricas.pedido(victima, [(producto, 1)]) for _ in range(3)]
        propio = fabricas.pedido(intruso, [(producto, 1)])
        ticket_ajeno = fabricas.ticket(victima)
        self.client.force_login(intruso)

        codigos = {p.pk: self.client.get(f"/api/pedidos/{p.pk}/").status_code for p in ajenos + [propio]}
        self.assertEqual(codigos, {**{p.pk: 404 for p in ajenos}, propio.pk: 200})
        for url in (f"/api/tickets/{ticket_ajeno.pk}/", f"/pqr/{ticket_ajeno.pk}/",
                    f"/pedidos/{ajenos[0].pk}/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)


class DivulgacionDeInformacionTests(TestCase):
    """Ejemplo de la guía: /error?debug=true  →  no revelar datos sensibles."""

    SENSIBLE = re.compile(r"Traceback|File \"|SECRET_KEY|DATABASES|settings\.py|URLconf|"
                          r"psycopg2|django\.db|Django Version|adminpassword", re.IGNORECASE)

    def test_debug_true_en_la_url_no_activa_nada(self):
        for url in ["/error?debug=true", "/api/productos/?debug=true", "/api/pedidos/999/?debug=true",
                    "/api/no-existe/?debug=1"]:
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertIn(respuesta.status_code, (200, 401, 404))
                self.assertNotRegex(respuesta.content.decode(), self.SENSIBLE)

    def test_un_error_interno_no_muestra_detalles_aunque_pidan_debug(self):
        with mock.patch("catalogo.servicios.listar_catalogo",
                        side_effect=RuntimeError("password=adminpassword en psycopg2")), \
                self.assertLogs("shophub", level="ERROR"):
            respuesta = self.client.get("/api/productos/?debug=true")
        self.assertEqual(respuesta.status_code, 500)
        # Solo el mensaje genérico y el id de seguimiento (Historia 06), nada más.
        cuerpo = respuesta.json()
        self.assertEqual(set(cuerpo), {"error", "id_error"})
        self.assertEqual(cuerpo["error"], "Error interno del servidor")
        self.assertEqual(str(uuid.UUID(cuerpo["id_error"])), cuerpo["id_error"])
        self.assertNotRegex(respuesta.content.decode(), self.SENSIBLE)

    def test_el_login_no_revela_si_el_usuario_existe(self):
        cache.clear()
        fabricas.cliente("ana@example.com")
        existe = post_json(self.client, "/api/sesion/", {"usuario": "ana@example.com", "clave": "mala"})
        no_existe = post_json(self.client, "/api/sesion/", {"usuario": "nadie@example.com", "clave": "mala"})
        self.assertEqual((existe.status_code, existe.json()), (no_existe.status_code, no_existe.json()))


class FuerzaBrutaTests(TestCase):
    """Ejemplo de la guía: múltiples intentos  →  debe limitar intentos."""

    def setUp(self):
        cache.clear()
        fabricas.cliente("ana@example.com")

    def test_api_y_web_bloquean_tras_5_intentos(self):
        for _ in range(5):
            post_json(self.client, "/api/sesion/", {"usuario": "ana@example.com", "clave": "mala"})
        bloqueado = post_json(self.client, "/api/sesion/", {"usuario": "ana@example.com", "clave": "clave123"})
        self.assertEqual(bloqueado.status_code, 429)

        web = self.client.post("/entrar/", {"usuario": "ana@example.com", "clave": "clave123"})
        self.assertEqual(web.status_code, 200)  # no redirige: sigue en el formulario
        self.assertContains(web, "Demasiados intentos")
        self.assertNotIn("_auth_user_id", self.client.session)
