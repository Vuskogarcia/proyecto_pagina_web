# Correcciones de seguridad y requisitos no funcionales

Implementación de las recomendaciones del [AI Decision Log](ai-decision-log-seguridad.md) (auditoría del 2026-10-28) y de la interfaz web.

> **Advertencia (igual que en la auditoría):** que estas pruebas pasen **no** permite declarar seguro el sistema. Demuestran que los hallazgos registrados ya no se reproducen. Nada más.

> **Sobre los IDs H1–H14:** el documento con la descripción detallada de cada hallazgo no estaba en el repositorio. La relación H → corrección se reconstruyó a partir del AI Decision Log, y **el equipo debe confirmarla**.

## 1. Resumen

| Hallazgo | Problema | Corrección | Respuesta ahora |
| --- | --- | --- | --- |
| H1–H3 | La identidad (`id_cliente`, `id_agente`) venía en el cuerpo JSON: cualquiera compraba, creaba tickets o los tomaba a nombre de otro | Sesión de Django (HU-01). `@api` exige sesión; los servicios reciben `request.user` | 401 sin sesión · 400 si el cuerpo trae `id_cliente` o `id_agente` |
| H1 (rol) | Un cliente podía actuar como agente | Rol de agente = grupo `agentes`; `SinPermiso` | 403 |
| H10 | Un objeto ajeno respondía distinto que uno inexistente (enumeración) | `pedido_visible_para`, `ticket_visible_para` y pedido ajeno en `crear_ticket` | 404 igual que si no existiera |
| H5 | `entero()` aceptaba `1.9` (como 1) y `"١"` (dígito árabe) | Lista de permitidos: `int` o dígitos ASCII | 400 |
| H6 | Enteros sin cota | Cota `MAX_ENTERO`, máximo 1000 unidades por producto, máximo 50 ítems; convertidor `<id:...>` en las URL | 400 · 404 |
| H7, H8 | NUL (`\x00`) y surrogates sueltos llegaban a PostgreSQL | `texto_seguro()` revisa todo el JSON | 400 (antes 500) |
| H4 / H4b | Excepción no prevista → 500 de Django (con traceback si `DEBUG=True`) | Red genérica en `@api` + `LOGGING` | 500 con JSON genérico; el detalle va solo al log |
| H11 | `DEBUG=True` por defecto y `SECRET_KEY` de respaldo | `DEBUG=False` por defecto; `SECRET_KEY` obligatoria; con `DEBUG=False` se rechaza una clave de ejemplo o corta | no arranca sin clave |
| H12 | Claves `django-insecure-…` en el historial de Git | **No se purgó** (ver §5) | — |
| H13 | `csrf_exempt` en la API | Se quitó: con sesiones, CSRF es obligatorio | 403 en JSON sin token |
| H14 | Los agentes eran `is_staff` y entraban a `/admin/` | Los agentes ya no son `is_staff` | `/admin/` redirige al login |

## 2. Evidencia

### 2.1 Pruebas en rojo antes de corregir (ADL-10)

`comun/pruebas/test_seguridad.py` se escribió antes que las correcciones. En PostgreSQL, sobre `feature/modulo5-6-calidad`:

```
Ran 25 tests
FAILED (failures=18, errors=2)
```

Algunas pasaban «por la razón equivocada»: por ejemplo, la de NUL respondía 400 porque faltaba `id_cliente`, no por el NUL. Por eso se hizo además el sondeo de §2.2, que aísla cada caso con el contrato viejo.

### 2.2 Sondeo con el código anterior en PostgreSQL

Cada caso en su propia transacción (PostgreSQL aborta la transacción tras el primer error de base de datos):

| Caso | Antes | Después |
| --- | --- | --- |
| H7: NUL en `descripcion` | **500** (página HTML de error) | 400 |
| H8: surrogate suelto `\ud800` | **500** | 400 |
| H5: `cantidad: 1.9` | **201** (compró 1) | 400 |
| H5: `cantidad: "١"` | **201** | 400 |
| H2: checkout con `id_cliente` de otro | **201** | 400 (401 sin sesión) |
| H6: `id_pedido: 10**20` en el cuerpo | 404 | 400 |
| H6: `cantidad: 10**30` | 409 | 400 |
| H6: id de 20 dígitos en la URL | 404 | 404 |

H6 **no** provocó un 500 con Django 6.1 + PostgreSQL: Django ya maneja los enteros fuera de rango en las búsquedas. La cota se dejó como defensa en profundidad y como regla de negocio.

### 2.3 Después de corregir

> Esta tabla es de la primera entrega (114 pruebas). La ejecución final de la semana 13, con 134 pruebas en PostgreSQL en el equipo de Kevin, está en [`semana-13.md`](semana-13.md).

| Entorno | Resultado |
| --- | --- |
| PostgreSQL 16 + Django 6.1.2 | 114 pruebas OK |
| PostgreSQL 16 + Django 5.2.18 | 114 pruebas OK |
| SQLite + Django 6.1.2 | 114 pruebas OK |
| `HTTPS=true manage.py check --deploy` | solo W021 (HSTS preload, decisión consciente) |
| CI simulado (sin `.env`, `SECRET_KEY` aleatoria) | `makemigrations --check` y pruebas OK |

## 3. Requisitos no funcionales implementados

| RNF | Cómo se cumple | Dónde |
| --- | --- | --- |
| Autenticación | Sesión de Django; `login()` rota el id de sesión (evita la fijación de sesión) | `cuentas/` |
| Autorización por rol | cliente (por defecto) · agente (grupo `agentes`) · administrador (superusuario) | `comun/roles.py`, `@api(acceso=...)`, `web/views.py` |
| Contraseñas | Mínimo 10 caracteres y validadores de Django (comunes, numéricas, parecidas al usuario) | `settings.AUTH_PASSWORD_VALIDATORS` |
| Fuerza bruta | 5 intentos fallidos por usuario + IP → bloqueo de 15 min (429). Mismo mensaje si el usuario no existe | `cuentas/servicios.py` |
| CSRF | Activo en la API y la web; respuesta JSON en `/api/` | `comun/http.py::fallo_csrf` |
| XSS | Escape automático de plantillas + CSP estricta sin `unsafe-inline` (la interfaz no usa JS ni CSS en línea) | `comun/middleware.py` |
| Clickjacking | `X-Frame-Options: DENY` + `frame-ancestors 'none'` | `settings.py` |
| Cabeceras | `nosniff`, `Referrer-Policy: same-origin`, COOP, `Permissions-Policy`, `Cache-Control: no-store` en la API | `settings.py`, middleware |
| Cookies | `HttpOnly`, `SameSite=Lax`, sesión de 8 h; `Secure` y HSTS con `HTTPS=true` | `settings.py` |
| Redirección abierta | `next` solo acepta URLs del mismo sitio | `web/views.py::_destino_seguro` |
| Tamaño de entrada | Cuerpo máximo de 64 KB (413); descripción ≤ 5000 y asunto ≤ 200 caracteres | `settings.py`, `soporte/servicios.py` |
| Registro y auditoría | Log `shophub`: errores 500 con traceback; 401/403/429, logins fallidos y CSRF rechazado como advertencias | `settings.LOGGING` |
| Configuración segura | `DEBUG=False` por defecto, `SECRET_KEY` obligatoria, sin contraseña de BD en el código | `settings.py` |
| Disponibilidad de estáticos | whitenoise sirve CSS e ícono con `DEBUG=False` | `settings.py` |
| Accesibilidad | Contraste AA (texto marino sobre coral: 5,8:1), foco visible, enlace «Saltar al contenido», etiquetas en todos los campos, tablas con `caption` y `scope` | `web/` |
| Plataforma objetivo | Interfaz solo para computador (ancho mínimo 1024 px); no hay versión móvil | `estilos.css` |

## 4. Cambios de contrato de la API (rompen clientes viejos)

1. Hay que iniciar sesión: `POST /api/sesion/ {"usuario", "clave"}`. Antes, `GET /api/sesion/` entrega la cookie `csrftoken`, que se envía en la cabecera `X-CSRFToken` de cada POST.
2. `POST /api/pedidos/` recibe solo `{"items": [...]}`.
3. `POST /api/tickets/` recibe `{"descripcion", "asunto"?, "id_pedido"?, "tipo"?}`.
4. `POST /api/tickets/<id>/tomar/` va sin cuerpo.
5. Cualquier campo no listado → 400.
6. Rutas nuevas: `GET /api/pedidos/` (mis pedidos), `GET /api/tickets/` (mis tickets, HU-06), `POST /api/registro/`, `DELETE /api/sesion/` y `GET /api/tickets/cola/?orden=recientes`.

## 5. Pendiente: decisiones del equipo

- **ADL-08 (historial de Git):** las claves `django-insecure-…` de los commits `1a2b391` y siguientes siguen en el historial. No se purgó porque reescribir la historia afecta a todos los integrantes. Si nunca hubo un despliegue, basta con no reutilizarlas: el código ya no trae ninguna. Si lo hubo, hay que rotar la clave en ese entorno.
- **Tu `.env` local** todavía tiene `SECRET_KEY=cambia-esto-…`. Funciona porque `DEBUG=True`, pero se recomienda generar una propia (ver `.env.example`).
- **Límite de intentos en memoria:** usa la caché local de cada proceso. Con varios procesos o servidores, configura una caché compartida (Redis o la de base de datos).
- **HSTS preload** desactivado a propósito: es difícil de revertir.
- Siguen sin hacerse la recuperación de contraseña, la verificación de email, HU-10 (responder o cerrar tickets) y DT-03 (estado *Resuelto*).
- Llenar las columnas de decisión humana del AI Decision Log y la fila de `uso-ia.md`.
