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
