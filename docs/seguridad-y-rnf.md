# Seguridad y requisitos no funcionales · registro único (Módulo 7)

Registro central de las 12 historias del Módulo 7 (semanas 13 y 14). Cada historia dice **qué mecanismo** la cumple, **con qué evidencia** (archivo de prueba, comando y resultado) y **qué riesgo queda**. El detalle vive en [`seguridad/`](seguridad/) y [`rendimiento/`](rendimiento/): aquí se enlaza, no se copia.

| Dato | Valor |
| --- | --- |
| Versión | `1.0.0-rc1` ([`CHANGELOG.md`](../CHANGELOG.md)) · rama `feature/modulo7-rnf-y-rc` |
| Última verificación completa | 2026-11-11, PostgreSQL 15.19, Python 3.12.10, Django 6.1.2: **205 pruebas OK, cobertura 93 %** ([evidencia](seguridad/evidencia/modulo7-ejecucion-postgresql.txt)) |
| Documentos de seguridad | [modelo de amenazas](seguridad/modelo-amenazas.md) · [semana 13](seguridad/semana-13.md) · [correcciones](seguridad/correcciones-seguridad.md) · [AI Decision Log](seguridad/ai-decision-log-seguridad.md) · [rotación de la SECRET_KEY](seguridad/rotacion-secret-key.md) |
| Documentos de rendimiento | [instrucciones](rendimiento/instrucciones.md) · [resultados 2026-11-11](rendimiento/resultados-2026-11-11.md) · [Argon2id](rendimiento/argon2.md) |
| Release | [triage del RC](triage-rc.md) · [CHANGELOG](../CHANGELOG.md) |

## 0. Advertencia

Que todas las pruebas pasen **no** permite declarar seguro el sistema. Demuestra que los ataques y escenarios probados aquí están controlados, nada más. Lo que queda abierto está en el §5 y en el §6.

## 1. Niveles de evidencia

Son los niveles que usa el [AI Decision Log](seguridad/ai-decision-log-seguridad.md) (§2).

| Nivel | Qué es | Ejemplo |
| --- | --- | --- |
| **E0** | Lectura de código o de configuración | `git show 0040777:tests/config/settings.py` muestra `DEBUG` en `True` por defecto |
| **E1** | Hecho documentado del lenguaje o del framework | Django muestra el traceback cuando `DEBUG=True` |
| **E2** | Sondeo exploratorio sin aserciones (de la IA o manual) | Sondeo de H5: `cantidad: 1.9` → 201 |
| **E3** | Prueba automatizada versionada, con aserciones, que pasa | `comun/pruebas/test_m7_h03_redos.py` |
| **E4** | E3 ejecutada en PostgreSQL (el motor real) y en el CI | La suite completa, en local y en GitHub Actions |

## 2. Cómo reproducir y resultado

```bash
docker compose up -d db
cd tests
pip install -r requirements-dev.txt
coverage run manage.py test -v 2 && coverage report --fail-under=85
python manage.py makemigrations --check --dry-run
HTTPS=true python manage.py check --deploy --fail-level ERROR
cd .. && bandit -r tests -x tests/venv,tests/.venv,tests/staticfiles --severity-level medium
pip-audit -r tests/requirements.txt
```

| Verificación (2026-11-11, igual que el CI: sin `.env` y con `SECRET_KEY` aleatoria) | Resultado |
| --- | --- |
| Pruebas en PostgreSQL 15.19 | **205 OK**, ninguna saltada, en 12,6 s |
| Cobertura | **93 %** (umbral 85 %) |
| `makemigrations --check` | sin cambios |
| `check --deploy` | solo W021 (HSTS preload, decisión consciente) |
| bandit (media o alta) | 0 hallazgos |
| pip-audit | sin vulnerabilidades conocidas |
| gitleaks | No se ejecutó localmente en esta sesión. En el CI del PR #16 (run `42969051443`): **no leaks found**. En ese mismo run: 205 pruebas OK, cobertura 93 % y `test_m7_h05_claves_revocadas` ejecutada, no saltada |

Salida completa: [`seguridad/evidencia/modulo7-ejecucion-postgresql.txt`](seguridad/evidencia/modulo7-ejecucion-postgresql.txt).

## 3. Historias

Los archivos de prueba están en `tests/`. Para correr solo una historia: `cd tests && python manage.py test <módulo>`.

### Historia 01 · Cuerpo demasiado grande → 413

| | |
| --- | --- |
| Mecanismo | `DATA_UPLOAD_MAX_MEMORY_SIZE = 64 KB`. `comun.middleware.LimiteDeCuerpoMiddleware` corta por `Content-Length` **antes** de que la sesión, el CSRF o la vista lean el cuerpo: JSON 413 en `/api/` y la página `413.html` en la web. `@api` conserva su propio 413 como segunda capa. Antes, la web respondía 400. |
| Evidencia | `comun/pruebas/test_m7_h01_tamano_cuerpo.py` · `python manage.py test comun.pruebas.test_m7_h01_tamano_cuerpo` · **5 OK** (E4). Cubre registro, login, PQR, checkout y alta de producto con más de 64 KB → 413, sin crear nada ni registrar eventos de negocio; el límite exacto (64 KB pasa, un byte más da 413); y un caso positivo. |
| Riesgo residual | El middleware decide por la cabecera `Content-Length`. Con un cuerpo *chunked* (sin esa cabecera), lo que llega a Django depende del servidor WSGI, y ese caso **no** se probó. En producción conviene limitar el tamaño también en el servidor o el proxy (en waitress, `max_request_body_size`). |

### Historia 02 · sin enunciado

El pedido de esta iteración no describe la Historia 02, y ningún archivo del repositorio la define. **No se le asignó contenido para no inventarlo.** El equipo debe indicar el enunciado. Los controles ya existentes de la semana 13 (checklist en [`semana-13.md`](seguridad/semana-13.md) §1) pueden cubrirla.

### Historia 03 · ReDoS (denegación de servicio por expresiones regulares)

| | |
| --- | --- |
| Mecanismo | Se valida el largo **antes** de aplicar la regex (`texto(..., maximo=…)`). Las regex no tienen cuantificadores anidados. Hay lista de permitidos para `?orden=`. Cambios de comportamiento: `asunto` de más de 200 caracteres → 400 (antes se recortaba) y `?orden=` desconocido → 400 (antes se ignoraba). |
| Evidencia | `comun/pruebas/test_m7_h03_redos.py` · `python manage.py test comun.pruebas.test_m7_h03_redos` · **10 OK** (E4). Envía 50 000 caracteres + `"!"` al teléfono de envío, al email de registro, al usuario del login, al asunto, a la descripción y a `?orden=`: 400, nada creado y menos de 1 s. Una revisión estática (AST + `re._parser`) encuentra las **5** regex del proyecto y comprueba que ninguna tiene cuantificadores anidados; el detector se valida con `(a+)+`, `(a*)*b`, etc. Además mide cada regex y `validate_email` de Django directamente con la carga. |
| Riesgo residual | La revisión estática solo ve regex literales en el código del proyecto; una regex armada en tiempo de ejecución no la detectaría. `validate_email` es de Django: se mide, no se revisa. |

### Historia 04 · Contraseñas con Argon2id

| | |
| --- | --- |
| Mecanismo | `argon2-cffi`. `PASSWORD_HASHERS` pone primero `comun.hashers.Argon2idPasswordHasher` y después PBKDF2: los hashes viejos siguen sirviendo y Django los convierte a Argon2id al iniciar sesión. Los parámetros salen de settings o del entorno (§ Historia 10). Solo durante `manage.py test` el costo es mínimo, para que la suite no se vuelva lenta: pasó de 176,7 s (172 pruebas, PBKDF2) a 14,6 s (194 pruebas) en el mismo equipo. |
| Evidencia | `cuentas/pruebas/test_m7_h04_argon2.py` · `python manage.py test cuentas.pruebas.test_m7_h04_argon2` · **7 OK** (E4). Comprueba: el hash empieza por `argon2$argon2id$`; la misma clave da dos hashes con sal distinta; `check_password` y el login aceptan la correcta y rechazan las incorrectas; la clave no aparece en `auth_user`, en la auditoría ni en el log; un hash PBKDF2 entra y queda convertido a Argon2id; en otro proceso, fuera de las pruebas, los parámetros son `m=65536,t=3,p=4` y se pueden cambiar por entorno. |
| Riesgo residual | Un hash PBKDF2 sigue en la base hasta que su dueño vuelve a iniciar sesión. Una cuenta que nunca vuelve conserva PBKDF2, que sigue siendo aceptable pero es más débil frente a GPU. |

### Historia 05 · Secretos: DT-13 cerrada y rotación

| | |
| --- | --- |
| Mecanismo | **Decisión: revocar, no purgar** ([`rotacion-secret-key.md`](seguridad/rotacion-secret-key.md) §1). `settings.py` guarda la huella SHA-256 de las 3 claves del historial (commits `1a2b391`, `2c19daf` y `83705b3`) y no arranca con ninguna, con o sin `DEBUG`. Procedimiento de rotación: revocar, generar, actualizar `.env` y CI, verificar (mismo archivo, §2). El CI hace checkout con todo el historial. |
| Evidencia | `comun/pruebas/test_m7_h05_claves_revocadas.py` · `python manage.py test comun.pruebas.test_m7_h05_claves_revocadas` · **5 OK** (E4). Lee las claves del historial real de Git, sin copiarlas al código, con la regex de gitleaks. Comprueba: hay exactamente 3; las 3 están en la lista de revocadas; `settings` falla con cada una con `DEBUG=False` (y también con `True`) sin repetir la clave en el error; una clave nueva arranca. |
| Riesgo residual | Si alguna clave se usó en un entorno desplegado, lo firmado con ella mientras estuvo activa pudo ser forjable. El repositorio no muestra un despliegue. En un clon superficial la prueba se salta y lo dice. |

### Historia 06 · Identificador de seguimiento en los errores 500

| | |
| --- | --- |
| Mecanismo | `comun.http._respuesta_500`, usado por `@api` y por el `handler500` nuevo de la web, genera un UUID. Ese id va en la respuesta (campo `id_error` del JSON, código visible en `500.html` y cabecera `X-Error-Id`), en el log `shophub` junto al traceback y en el evento de auditoría `ERROR_INTERNO`. Si la plantilla 500 también falla, se responde texto plano con el id. |
| Evidencia | `comun/pruebas/test_m7_h06_id_error.py` · `python manage.py test comun.pruebas.test_m7_h06_id_error` · **6 OK** (E4). Comprueba: la respuesta trae un UUID válido; el mismo id está en el registro del log con `Traceback`, el tipo y el mensaje real, y en la auditoría (sin el mensaje); la respuesta no trae el mensaje, el traceback, rutas, `settings`, `psycopg2` ni el tipo de excepción; cada error tiene su propio id; las respuestas normales no llevan id. |
| Riesgo residual | Django también registra el error en `django.request`, sin el id; para cruzar los dos registros se usan la hora y la ruta. No hay alertas automáticas sobre el log (A09). |

### Historia 07 · Veredicto de los hallazgos H1–H14

| | |
| --- | --- |
| Mecanismo | Tabla de veredictos en el [AI Decision Log §6](seguridad/ai-decision-log-seguridad.md#6-veredicto-por-hallazgo-h1h14--módulo-7-historia-07). Por cada hallazgo: veredicto, verificación técnica hecha (código auditado `0040777`, sondeos guardados y la prueba que hoy lo cubre), acción y commit o PR. |
| Evidencia | **11 confirmados**, **2 falsos positivos con matiz** (H6 como 500; H13 en el código auditado) y **1 no verificable** (H9). Cada fila cita un `git show`/`git grep` reproducible o una clase de prueba de la suite (E0 a E4 según la fila). |
| Riesgo residual | H9 no tiene descripción en el repositorio. Las columnas de decisión humana de la §2 del log siguen vacías: le tocan al equipo ([triage](triage-rc.md), PROC-01). |

### Historias 08 y 09 · Pruebas de carga con k6

| | |
| --- | --- |
| Mecanismo | Scripts en [`rendimiento/k6/`](rendimiento/k6/): catálogo, login + checkout y registro. Manejan la sesión y el token CSRF (que se relee después del login, porque Django lo rota). El registro usa un email único por iteración (VU, iteración, timestamp y UUID). Los umbrales están en `config.js` y se fijaron antes de medir. El diseño respeta los límites de la aplicación ([instrucciones §2](rendimiento/instrucciones.md#2-cómo-respetan-los-scripts-los-límites-de-la-aplicación)). |
| Evidencia | `bash docs/rendimiento/medir.sh final <escenario>` contra waitress + PostgreSQL 15.19 (2026-11-11). Configuración final: catálogo p50/p95/p99 = 20/36/43 ms; login 204/369/554 ms; checkout 178/303/387 ms; registro 83/152/208 ms. **0 % de errores** y todos los umbrales cumplidos ([resultados](rendimiento/resultados-2026-11-11.md) §2; salida cruda en [`rendimiento/resultados/2026-11-11/`](rendimiento/resultados/2026-11-11/)). |
| Punto 8 (cuello de botella) | **No hizo falta:** la línea base ya cumplía todos los umbrales ([resultados](rendimiento/resultados-2026-11-11.md) §4). DT-07 queda medida y diferida. |
| Riesgo residual | k6 y el servidor corren en la misma máquina; 60 s por escenario; un solo proceso; no se buscó el punto de quiebre. Para medir el registro se subió el límite de registros por IP (solo en el servidor de la prueba). |

### Historia 10 · Parámetros de Argon2id medidos

| | |
| --- | --- |
| Mecanismo | Se midieron tres configuraciones: Django por defecto (t=2, 100 MiB, p=8), **RFC 9106 segunda recomendada (t=3, 64 MiB, p=4)** y OWASP mínima (t=2, 19 MiB, p=1). Se midió el costo de un hash, el registro bajo carga (dos corridas cada una) y login + checkout. Se eligió la del RFC 9106. |
| Evidencia | [`rendimiento/argon2.md`](rendimiento/argon2.md): tabla de parámetros, p50/p95/p99 y errores, y la justificación. Registro p95: 150–156 ms (A), 149–164 ms (B), 72–74 ms (C), 0 errores en todas. El valor por defecto lo verifica `ParametrosDeProduccionTests`. |
| Riesgo residual | La ventaja de B sobre A en el login viene de una sola corrida de A. El pico de memoria (≈ 64 MiB × logins simultáneos) está calculado, no medido. |

### Historia 11 · Triage del release candidate

| | |
| --- | --- |
| Mecanismo | [`triage-rc.md`](triage-rc.md): defectos y deudas con severidad, decisión (incluir, diferir o fuera de alcance) y justificación, y la política de congelación con fecha de corte **2026-11-13**. |
| Evidencia | 6 incluidos (corregidos en este PR), 1 de proceso para el equipo antes del tag (PROC-01), 8 diferidos y 4 fuera de alcance. Ninguno crítico o alto de código queda abierto. |
| Riesgo residual | La fecha de corte es una propuesta del triage: el equipo la confirma. |

### Historia 12 · Notas de la versión `1.0.0-rc1`

| | |
| --- | --- |
| Mecanismo | [`CHANGELOG.md`](../CHANGELOG.md): lo incluido, los cambios que rompen la API y lo que queda para la versión siguiente. El tag `v1.0.0-rc1` se crea **después** de fusionar el PR y con el CI de `main` en verde. |
| Evidencia | El tag todavía no existe, a propósito. Comando (desde `main` actualizado): `git tag -a v1.0.0-rc1 -m "SHOP-HUB 1.0.0-rc1" && git push origin v1.0.0-rc1`. |
| Riesgo residual | PROC-01 (decisión humana en el AI Decision Log) debe cerrarse antes del tag. |

## 4. Checklist OWASP Top 10 (2021)

Detalle de amenazas y controles: [modelo de amenazas](seguridad/modelo-amenazas.md) §3 y §4.

- [x] **A01 Control de acceso roto.** Identidad desde la sesión, rol verificado en el servidor y recurso ajeno = 404. Pruebas: `ADL01*`, `ADL03*`, `IdorTests`, `H14*`.
- [x] **A02 Fallos criptográficos.** Contraseñas con **Argon2id** (Historia 04); claves históricas revocadas (Historia 05); HTTPS, HSTS y cookies `Secure` con `HTTPS=true`. ⚠️ Depende de servir el sitio por HTTPS.
- [x] **A03 Inyección.** Solo ORM, con una guardia estática contra SQL crudo y pruebas `' OR 1=1 --`; ReDoS controlado (Historia 03). Pruebas: `InyeccionSqlTests`, `test_m7_h03_redos.py`.
- [x] **A04 Diseño inseguro.** Modelo de amenazas; reglas en los servicios; lista de permitidos; límites de tamaño (Historia 01) y de frecuencia.
- [x] **A05 Configuración incorrecta.** `DEBUG=False` por defecto, `SECRET_KEY` obligatoria y no revocada, cabeceras de seguridad, `check --deploy` en el CI y páginas 403, 404, 413, 429 y 500 propias.
- [x] **A06 Componentes vulnerables.** `pip-audit` en el CI (sin vulnerabilidades conocidas el 2026-11-11, incluido `argon2-cffi`).
- [x] **A07 Identificación y autenticación.** Bloqueo tras 5 intentos, contraseña de mínimo 10 caracteres, Argon2id y rotación de sesión. ⚠️ Sin MFA (DT-14, fuera de alcance de 1.x).
- [x] **A08 Integridad de software y datos.** CSRF, transacciones con bloqueo de filas y CI con quality gates (pruebas, cobertura, bandit, pip-audit y gitleaks).
- [x] **A09 Registro y monitoreo.** `EventoAuditoria` y log con **id de seguimiento** en cada 500 (Historia 06). ⚠️ Sin alertas automáticas.
- [ ] **A10 SSRF.** **No aplica:** el sistema no hace peticiones salientes.

## 5. Riesgo residual global

Detalle y decisión en [`triage-rc.md`](triage-rc.md) §2.2:

- DT-12: los límites viven en la memoria de cada proceso. Es **bloqueante** si se despliega con más de un proceso.
- Las lecturas (GET) no tienen límite de peticiones: se mitiga en el proxy.
- Sin MFA, sin recuperación de contraseña y sin alertas automáticas (fuera de alcance de 1.x).
- H9 sin descripción; Historia 02 sin enunciado.

## 6. Lo que las pruebas no demuestran

- No prueban ataques que no se escribieron: una prueba verde solo cubre su escenario.
- Las cotas de tiempo (1 s en ReDoS) y los umbrales de carga son de esta máquina y de este momento. Otra máquina da otros números.
- La carga se generó desde la misma máquina que el servidor, con un solo proceso y durante 60 s.
- gitleaks no se ejecutó localmente en esta sesión: su resultado (sin secretos) es el del CI del PR #16.
- Las decisiones de diseño marcadas como del equipo (AI Decision Log §2, `uso-ia.md`) siguen pendientes.

## 7. Criterio para cerrar un hallazgo

Un hallazgo o una historia de seguridad se da por cerrado solo si cumple todo esto (ADL-10):

1. Hay una prueba versionada que **fallaría** sin la corrección: se vio fallar, o el comportamiento anterior está documentado con un sondeo reproducible.
2. La prueba afirma también sobre el estado (la base de datos, el log o la auditoría), no solo sobre el código HTTP.
3. Hay al menos un **caso positivo**, para que un «OK» no pueda deberse a que el sistema rechaza todo.
4. Pasa en **PostgreSQL** y en el CI (nivel E4).
5. El cambio está enlazado a un commit o PR y, si cambia el contrato, aparece en el `CHANGELOG.md`.
