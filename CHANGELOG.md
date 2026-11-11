# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Versionado [semántico](https://semver.org/lang/es/).

## [1.0.0-rc1] · fecha del tag: pendiente (después de fusionar el PR y con el CI en verde)

Primer *release candidate* de SHOP-HUB: tienda en línea con soporte postventa, donde cada PQR queda ligada al pedido que la originó. El alcance está congelado desde el 2026-11-11 y la fecha de corte es el 2026-11-13 ([`docs/triage-rc.md`](docs/triage-rc.md) §3).

### Funcionalidad incluida (historias de usuario HU-01 a HU-10)

- **HU-01** Registro, inicio y cierre de sesión con roles: cliente, agente de soporte (grupo `agentes`) y administrador (superusuario).
- **HU-02** Catálogo público con detalle de producto; los agotados se muestran marcados.
- **HU-03** Gestión del catálogo e inventario (solo administradores): crear, editar, activar y desactivar productos.
- **HU-04** Carrito editable en sesión, datos de envío y checkout transaccional con bloqueo de filas; código de pedido `PED-00001`.
- **HU-05** Radicar una PQR (petición, queja o reclamo), opcionalmente ligada a un pedido propio.
- **HU-06** Consultar el estado de mis PQR.
- **HU-07** Cola de PQR sin asignar para los agentes, ordenable por fecha.
- **HU-08** Tomar una PQR con control de concurrencia: dos agentes a la vez → uno 200, el otro 409.
- **HU-09** El agente ve el pedido asociado a la PQR.
- **HU-10** Responder y cambiar el estado: Abierto → En proceso → Resuelto → Cerrado.
- Interfaz web con plantillas Django (para computador) y API JSON en `/api/`.

### Seguridad (Módulo 7, semanas 13 y 14)

- Identidad desde la sesión, nunca desde el cuerpo; CSRF obligatorio; recurso ajeno = 404; validación por lista de permitidos con cotas; texto sin NUL ni surrogates; red genérica de errores; `DEBUG=False` por defecto; cabeceras CSP, `X-Frame-Options`, `nosniff`, COOP y `Permissions-Policy`; límite de intentos de login y de escrituras; auditoría de eventos críticos (semana 13, PR #15).
- **Nuevo en este RC:**
  - Contraseñas con **Argon2id** (t=3, m=64 MiB, p=4; RFC 9106). Los hashes PBKDF2 existentes siguen sirviendo y se convierten a Argon2id al iniciar sesión. Parámetros configurables con `ARGON2_TIME_COST`, `ARGON2_MEMORY_COST` y `ARGON2_PARALLELISM` (Historias 04 y 10).
  - Cuerpo mayor a 64 KB → **413** también en la web, con la página propia `413.html` (Historia 01).
  - Regresión de **ReDoS**: entradas de 50 000 caracteres rechazadas con 400 en menos de 1 s; revisión estática de cuantificadores anidados (Historia 03).
  - Las 3 `SECRET_KEY` que quedaron en el historial de Git están **revocadas**: `settings.py` no arranca con ninguna. Procedimiento de rotación documentado; DT-13 cerrada (Historia 05).
  - Los errores 500 llevan un **identificador de seguimiento (UUID)**: `id_error` en el JSON, código visible en la página 500 y cabecera `X-Error-Id`. El mismo id queda en el log junto al traceback (Historia 06).
  - Veredicto verificable de los hallazgos H1–H14 de la auditoría (Historia 07).

### Cambios que rompen el contrato de la API

- `POST /api/tickets/`: un `asunto` de **más de 200 caracteres** responde **400**. Antes se recortaba en silencio. Un `asunto` que no es texto también responde 400.
- `GET /api/tickets/cola/?orden=<valor>`: un orden distinto de `antiguos` o `recientes` responde **400**. Antes se ignoraba y respondía 200. La web conserva el orden por defecto.
- Las respuestas 500 de la API traen un campo nuevo, `id_error`, y la cabecera `X-Error-Id`.

### Corregido

- La cola de PQR empata por `id` cuando dos tickets tienen la misma fecha de creación. Antes salían en orden arbitrario y una prueba fallaba de forma intermitente.

### Rendimiento (Historias 08, 09 y 10)

- Pruebas de carga con k6 en [`docs/rendimiento/`](docs/rendimiento/): catálogo, login + checkout y registro, con umbrales fijados antes de medir. Todos se cumplen en la configuración final (2026-11-11, waitress + PostgreSQL 15). Por ejemplo, p95 del catálogo 36 ms, del login 369 ms, del checkout 303 ms y del registro 152 ms, con 0 % de errores. Detalle en [`resultados-2026-11-11.md`](docs/rendimiento/resultados-2026-11-11.md).
- La suite de pruebas pasó de 176,7 s a unos 15 s en el mismo equipo: Argon2id usa costo mínimo solo durante `manage.py test`.

### Documentación

- [`docs/seguridad-y-rnf.md`](docs/seguridad-y-rnf.md): registro único de seguridad y RNF por historia, con el checklist OWASP Top 10.
- [`docs/triage-rc.md`](docs/triage-rc.md): triage y política de congelación.
- [`docs/seguridad/rotacion-secret-key.md`](docs/seguridad/rotacion-secret-key.md): decisión sobre DT-13 y procedimiento de rotación.

### Para la siguiente versión (no incluido en el RC)

Detalle y justificación en [`docs/triage-rc.md`](docs/triage-rc.md) §2.2.

- **Antes del tag (equipo):** llenar la decisión humana en el AI Decision Log y resolver las etiquetas `[DECISIÓN DEL EQUIPO]` de `uso-ia.md` (PROC-01).
- DT-12: caché compartida para los límites. **Obligatoria antes de desplegar con más de un proceso.**
- DT-07: quitar el N+1 de `Pedido.total()` y del serializador del pedido.
- DT-04: mover el proyecto Django de `tests/` a `app/`.
- DT-06, DT-08, DT-10: mantenibilidad y documentación.
- Límite de peticiones para las lecturas (GET) en el proxy o la infraestructura.
- H9: recuperar la descripción del hallazgo o darlo por retirado.
- Fuera de alcance de 1.x: MFA, recuperación de contraseña y verificación de email (DT-14), y alertas automáticas.
