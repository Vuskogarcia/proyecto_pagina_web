# AI Decision Log · Auditoría de seguridad (Módulo 7)

> Registro de las recomendaciones de IA hechas durante la auditoría, y de lo que el equipo decidió sobre cada una.
> Puede integrarse en `docs/uso-ia.md` (sección 2) o mantenerse como anexo.
> **Las columnas de decisión y justificación humanas están vacías a propósito: solo el equipo puede llenarlas.**

| Dato | Valor |
| --- | --- |
| Fecha de la sesión | 2026-10-28 |
| Herramienta | Claude (Anthropic), interfaz claude.ai |
| Rol asignado a la IA | Auditor adversarial y mentor socrático (sin entregar parches) |
| Integrante responsable | `[DECISIÓN DEL EQUIPO]` |
| Código auditado | `main` @ `0040777` |
| Documento relacionado | `docs/seguridad-y-rnf.md` |

## 1. Fila para la tabla de `docs/uso-ia.md` (formato actual del equipo)

| Fecha | Integrante | Herramienta | Para qué se usó | Qué se revisó/ajustó manualmente |
| --- | --- | --- | --- | --- |
| 2026-10-28 | `[DECISIÓN DEL EQUIPO]` | Claude (claude.ai) | Auditoría de seguridad de la API: inventario de endpoints y fronteras de confianza, sondeos exploratorios (SQLite), diseño de 5 casos de prueba adversariales, clasificación de hallazgos. | `[PENDIENTE]` Reproducción de H1–H5 con pruebas propias, decisiones de diseño de las correcciones y verificación en PostgreSQL. |

**Recomendación al equipo:** añadir a esa tabla las columnas **Decisión** (ACEPTADA / MODIFICADA / RECHAZADA) y **Evidencia ejecutada**, que el formato actual no tiene.

## 2. Recomendaciones de la IA y decisiones humanas

Nivel de evidencia según `seguridad-y-rnf.md` §1: E0 lectura de código · E1 hecho del lenguaje · E2 sondeo de la IA · E3/E4 prueba del equipo.

| ID | Recomendación de la IA | Basada en | Postura de la IA (no vinculante) | Decisión humana | Justificación humana | Evidencia ejecutada por el equipo | Commit / PR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ADL-01 | Obtener la identidad del usuario de la sesión, no del cuerpo JSON. | H1, H2, H3 (E2) | Necesaria. La forma concreta depende del diseño de HU-01. | | | | |
| ADL-02 | Crear un tipo de error para «sin permiso» dentro de `ErrorDeNegocio`. | H1 (E2) | Depende de la decisión 403/404 (ADL-03). | | | | |
| ADL-03 | Responder igual ante un objeto ajeno y uno inexistente. | H10 (E2), H3 | Puede posponerse hasta corregir H3. | | | | |
| ADL-04 | Validar con lista de permitidos y cota superior en `entero()`. | H5 (E2), H6 (E1) | Ejecutar H6 antes de decidir. | | | | |
| ADL-05 | Rechazar NUL y surrogates sueltos con 400. | H7, H8 (hipótesis) | **No adoptar** sin ejecutar antes P4 en PostgreSQL. | | | | |
| ADL-06 | Añadir una red genérica de excepciones en `@api` con registro interno. | H4 (E2) | Capturarlo todo oculta errores si no hay `LOGGING`. | | | | |
| ADL-07 | Desactivar `DEBUG` por defecto y eliminar el `SECRET_KEY` de respaldo. | H11 (E0) | Bajo costo; revisar el impacto en el flujo de desarrollo. | | | | |
| ADL-08 | Rotar o purgar los secretos del historial de Git. | H12 (E2) | Solo procede si hubo un despliegue. Purgar el historial afecta a todo el equipo. | | | | |
| ADL-09 | Usar `django.test.TestCase`, `self.client` y `TransactionTestCase` en lugar de JUnit o RestAssured. | Stack real del proyecto (E0) | Coherente con el proyecto. | | | | |
| ADL-10 | Escribir primero una prueba roja con predicción explícita y aserciones sobre la base de datos, e incluir un caso positivo. | Método | Requisito para cerrar hallazgos (`seguridad-y-rnf.md` §7). | | | | |

## 3. Afirmaciones de la IA corregidas o retractadas

Para que la revisión humana sea transparente, se registran los errores y las imprecisiones de la propia IA:

| Turno | Afirmación original de la IA | Corrección | Motivo |
| --- | --- | --- | --- |
| 1 | Los errores 500 «muestran el traceback». | Pasa a ser hipótesis (H4b). | No se observó la respuesta HTTP: el cliente de pruebas lanza la excepción. |
| 1 | Los agentes demo «pueden iniciar sesión en `/admin/`». | Pasa a ser hipótesis (H14), probablemente comportamiento esperado. | No se ejecutó, y esos usuarios no tienen permisos asignados. |
| 1 | Prueba de ejemplo que afirma exactamente 403. | La IA recomienda modificarla (PI4). | Fija una decisión de diseño que el equipo aún no ha tomado. |
| 1–2 | Los sondeos `test_sondeo*.py` sirven como evidencia. | Se reclasifican como exploratorios (PI1). | No tienen aserciones; el «OK» del runner no prueba nada. |
| 3 | H13 (`text/plain` con `csrf_exempt`). | Clasificado como falso positivo *hoy*. | Es un juicio de la IA: **el equipo debe validarlo** y reclasificarlo con HU-01. |

## 4. Límites del uso de IA en esta auditoría

- Las ejecuciones de la IA se hicieron en su propio entorno: SQLite, Python 3.12.3, Django 6.1.2. **No** se ejecutó nada en PostgreSQL y **no** se revisaron los resultados del CI.
- Ninguna recomendación es una decisión. Según la política de `uso-ia.md`, las decisiones de diseño y de lógica de negocio corresponden al equipo.
- La IA no escribió correcciones ni pruebas definitivas para el repositorio. Las pruebas versionadas deben ser del equipo, según la buena práctica de `uso-ia.md` §3.
- Haber superado las pruebas registradas no permite declarar seguro el sistema (ver `seguridad-y-rnf.md` §0 y §6).

## 5. Implementación de las recomendaciones (sesión 2026-11-02)

> Esta sección la agregó Claude (Cowork) al implementar las correcciones a pedido de Kevin García.
> **No reemplaza la decisión humana:** las columnas «Decisión humana» y «Justificación humana» de la §2 siguen vacías para que el equipo las llene después de revisar el código.

| Dato | Valor |
| --- | --- |
| Fecha | 2026-11-02 |
| Herramienta | Claude (Cowork) |
| Solicitado por | Kevin García |
| Rama | `feature/seguridad-e-interfaz` (desde `feature/modulo5-6-calidad` @ `5eabc74`), **sin commit** |
| Ejecutado en | PostgreSQL 16 + Django 6.1.2 y Django 5.2.18 (Python 3.12) |
| Detalle | [`correcciones-seguridad.md`](correcciones-seguridad.md) · evidencia final en [`semana-13.md`](semana-13.md) |

Única decisión de diseño tomada por un integrante en la sesión: **ADL-03 → 404** (Kevin eligió responder igual ante un objeto ajeno y uno inexistente).

| ID | Qué se implementó | Prueba que lo verifica |
| --- | --- | --- |
| ADL-01 | Identidad desde la sesión (HU-01: registro, login, roles). El cuerpo ya no acepta `id_cliente` ni `id_agente` (400 si llegan). | `comun/pruebas/test_seguridad.py::ADL01*` |
| ADL-02 | Se mantiene `SinPermiso` (403, ya existía en módulos 5-6) y se agregan `NoAutenticado` (401) y `DemasiadosIntentos` (429). | `ADL01*`, `SesionYRegistroTests` |
| ADL-03 | Pedido o ticket ajeno → 404 con la misma forma que uno inexistente. | `ADL03*` |
| ADL-04 | `entero()` con lista de permitidos (int o dígitos ASCII) y cota; campos del JSON con lista de permitidos; ids de URL con cota (`<id:...>`). | `ADL04*`, `test_unitarias_seguridad.py` |
| ADL-05 | NUL y surrogates sueltos → 400 en todo el cuerpo JSON. **P4 se ejecutó primero en PostgreSQL:** ambos daban 500. | `ADL05*` |
| ADL-06 | Red genérica en `@api` + `LOGGING`: 500 genérico al cliente, traceback solo en el log `shophub`. | `ADL06*` |
| ADL-07 | `DEBUG=False` por defecto; sin `SECRET_KEY` de respaldo; clave de ejemplo rechazada con `DEBUG=False`. | `ADL07*` |
| ADL-08 | **No ejecutada** (purgar historial afecta a todo el equipo). Ver `correcciones-seguridad.md` §5. | — |
| ADL-09 | Todas las pruebas usan `django.test` (`TestCase`, `self.client`, `TransactionTestCase`). | — |
| ADL-10 | Pruebas escritas primero y vistas fallar (18 fallos + 2 errores de 25), con aserciones sobre la base de datos y casos positivos. | salida en `correcciones-seguridad.md` §2 |

## 6. Veredicto por hallazgo (H1–H14) · Módulo 7, Historia 07

> Agregado el 2026-11-11 por Claude Code, a pedido de Kevin García. **Solo se usó lo que se puede comprobar** en el código, en el historial de Git o con una prueba del repositorio. Donde no hay con qué comprobar, se dice.
> «Verificación técnica» indica qué se revisó: `git show 0040777:…` es el código auditado; una clase `…Tests` es una prueba que hoy corre en el CI.
> Las columnas de decisión humana de la §2 siguen siendo del equipo.

| Hallazgo | Problema (según §2 y `correcciones-seguridad.md`) | Veredicto | Verificación técnica hecha | Acción | Commit / PR |
| --- | --- | --- | --- | --- | --- |
| H1 | Un cliente podía actuar a nombre de otro o como agente (identidad en el cuerpo) | **Confirmado** | En `0040777`, `soporte/views.py:36` toma `id_agente` del cuerpo y no hay vista de login. Hoy: `ADL01IdentidadDesdeLaSesionTests` (401 sin sesión, 400 si llega `id_cliente`/`id_agente`, 403 a un cliente en la cola) | Identidad desde la sesión (HU-01) y rol de agente verificado en el servicio | `7afe94d` · PR #15 |
| H2 | Checkout a nombre de otro cliente | **Confirmado** | `0040777:carrito/views.py:13` pasa `datos.get("id_cliente")` al servicio. Sondeo en PostgreSQL: **201** con el `id_cliente` de otro (`correcciones-seguridad.md` §2.2). Hoy: `test_el_cuerpo_ya_no_puede_suplantar_a_otro_usuario` | Igual que H1 | `7afe94d` · PR #15 |
| H3 | Ticket creado a nombre de otro cliente | **Confirmado** | `0040777:soporte/views.py:14` toma `cliente_id` del cuerpo. Hoy: `ADL01…`, `ADL03ObjetosAjenosResponden404Tests` | Igual que H1, más 404 ante un pedido ajeno | `7afe94d` · PR #15 |
| H4 | Excepción no prevista → 500 sin manejo | **Confirmado** | `0040777` no tenía red genérica en `@api` ni `LOGGING`. Hoy: `ADL06RedGenericaDeExcepcionesTests` y `test_un_error_interno_no_muestra_detalles_aunque_pidan_debug` | Red genérica en `@api`, log `shophub`; ahora con id de seguimiento (Historia 06) | `7afe94d` · PR #15; `db4b6a1` (este PR) |
| H4b | El 500 «muestra el traceback» | **Confirmado por configuración, no por ejecución** | `git show 0040777:tests/config/settings.py` línea 23: `DEBUG` era `True` por defecto, y con `DEBUG=True` Django responde con la página técnica que incluye el traceback. La respuesta HTTP de entonces **no** se capturó (§3, turno 1). Hoy: `IdDeSeguimientoTests` comprueba que el 500 no trae traceback, rutas ni el mensaje | `DEBUG=False` por defecto (H11) y `handler500` propio | `7afe94d` · PR #15; `db4b6a1` |
| H5 | `entero()` aceptaba `1.9` y `"١"` | **Confirmado** | Sondeo en PostgreSQL: **201** con `cantidad: 1.9` y con `"١"` (§2.2 de `correcciones-seguridad.md`). Hoy: `ADL04ValidacionConListaDePermitidosYCotasTests`, `test_unitarias_seguridad.py` | Lista de permitidos: `int` o dígitos ASCII | `7afe94d` · PR #15 |
| H6 | Enteros sin cota superior | **Falso positivo como 500; se corrigió como regla de negocio** | Sondeo: `id_pedido: 10**20` → 404 y `cantidad: 10**30` → 409; **ninguno dio 500** (§2.2). Hoy: `test_id_enorme_en_la_url_responde_404_y_no_500` | Cota `MAX_ENTERO`, 1000 unidades y 50 ítems, convertidor `<id:…>` (defensa en profundidad) | `7afe94d` · PR #15 |
| H7 | NUL (`\x00`) en un texto llegaba a PostgreSQL | **Confirmado** | Sondeo en PostgreSQL: **500** (§2.2). Hoy: `ADL05TextoConNulYSurrogatesTests` | `texto_seguro()` en todo el JSON → 400 | `7afe94d` · PR #15 |
| H8 | Surrogate suelto (`\ud800`) llegaba a PostgreSQL | **Confirmado** | Sondeo en PostgreSQL: **500** (§2.2). Hoy: `ADL05…` | Igual que H7 | `7afe94d` · PR #15 |
| H9 | — | **No verificable** | El documento original de hallazgos no está en el repositorio (`correcciones-seguridad.md`, nota inicial) y ningún archivo describe H9. No se le asigna contenido para no inventarlo | El equipo debe recuperar la descripción original o marcarlo como retirado | — |
| H10 | Objeto ajeno respondía distinto que uno inexistente (enumeración) | **Confirmado** | Sondeo de la IA (E2, §2). No hay salida «antes» guardada por el equipo. Hoy: `ADL03ObjetosAjenosResponden404Tests`, `IdorTests` | 404 igual para ajeno e inexistente (ADL-03, decisión de Kevin) | `7afe94d` · PR #15 |
| H11 | `DEBUG=True` por defecto y `SECRET_KEY` de respaldo | **Confirmado** | `git show 0040777:tests/config/settings.py`: líneas 18 (`SECRET_KEY = os.getenv(` con valor de respaldo) y 23 (`DEBUG` por defecto `"True"`). Hoy: `ADL07ConfiguracionSeguraPorDefectoTests` | `DEBUG=False` por defecto; `SECRET_KEY` obligatoria | `7afe94d` · PR #15 |
| H12 | Claves `django-insecure-…` en el historial de Git | **Confirmado** | `git log --all -p -S django-insecure` con la regex de gitleaks: **3** claves, en `1a2b391`, `2c19daf` y `83705b3`. Hoy: `ClavesHistoricasRevocadasTests` las lee del historial y comprueba que `settings` las rechaza | Revocadas por huella SHA-256; no se purga el historial (DT-13 cerrada, [`rotacion-secret-key.md`](rotacion-secret-key.md)) | `a976c7a` (este PR) |
| H13 | `csrf_exempt` en la API | **Falso positivo en `0040777`; aplicable desde HU-01** | En `0040777` sí estaba `@csrf_exempt` (`comun/http.py:22`), pero no había inicio de sesión: la identidad venía en el cuerpo y no había cookie que un sitio externo pudiera aprovechar. Al agregar sesiones (HU-01) pasó a ser necesario. Hoy: `H13CsrfConSesionTests` (403 sin token, 201 con token) | Se quitó `csrf_exempt` | `7afe94d` · PR #15 |
| H14 | Los agentes entraban a `/admin/` | **Confirmado** | En `0040777`, `comun/fabricas.py:18` y `cargar_datos_demo.py:84` creaban los agentes con `is_staff=True`, que es lo que Django exige para entrar al admin. Hoy: `H14AgentesSinAccesoAlAdminTests` | Agente = grupo `agentes`, sin `is_staff` | `7afe94d` · PR #15 |

Resumen: **11 confirmados** (H1–H5, H7, H8, H10–H12, H14; H4b solo por configuración), **2 falsos positivos** con matiz (H6 como 500 y H13 en el código auditado) y **1 no verificable** (H9).
