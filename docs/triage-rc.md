# Triage del Release Candidate `v1.0.0-rc1`

Módulo 7, Historia 11. Fecha del triage: **2026-11-11**. Rama: `feature/modulo7-rnf-y-rc`.

Fuentes: [`deuda-tecnica.md`](deuda-tecnica.md) (deudas DT-xx), [`seguridad/modelo-amenazas.md`](seguridad/modelo-amenazas.md) §5 (riesgos aceptados), el [AI Decision Log](seguridad/ai-decision-log-seguridad.md) §6 (veredictos H1–H14) y lo encontrado al cerrar las Historias 01–10 en este PR.

## 1. Criterios

**Severidad**

| Severidad | Significa |
| --- | --- |
| **Crítica** | Pérdida o exposición de datos, o el sistema no arranca. Bloquea el RC. |
| **Alta** | Rompe un criterio de aceptación o un control de seguridad del checklist. Bloquea el RC. |
| **Media** | No rompe nada hoy, pero limita el despliegue, la escala o el mantenimiento. |
| **Baja** | Claridad, estilo u orden. |

**Decisión**

| Decisión | Significa |
| --- | --- |
| **Incluir** | Entra en `v1.0.0-rc1`: ya está corregido en este PR, o hay que hacerlo antes de crear el tag. |
| **Diferir** | Queda para la versión siguiente (`1.0.0` o `1.1.0`) con su condición de revisión. |
| **Fuera de alcance** | No es objetivo de la versión 1.x del curso. Se documenta el riesgo aceptado. |

## 2. Defectos y deudas

### 2.1 Corregidos en este PR (incluidos)

| ID | Descripción | Severidad | Decisión | Justificación / evidencia |
| --- | --- | --- | --- | --- |
| DEF-01 | `test_la_cola_se_puede_ordenar_de_la_mas_nueva_a_la_mas_antigua` fallaba de forma intermitente: dos tickets con el mismo `creado_en` salían en orden arbitrario | Media | **Incluir** ✅ | Prueba intermitente: resta confianza al CI. Se desempató por `id` (commit `f46e85b`). Antes del cambio, la suite completa falló en 2 de 3 ejecuciones locales válidas, con 1 fallo cada vez; en la que se inspeccionó, el fallo era esta prueba. (El mensaje del commit dice «1 de 3»: lo correcto es esto.) |
| DEF-02 | La web respondía 400 (no 413) ante un cuerpo mayor a 64 KB | Media | **Incluir** ✅ | Historia 01. `LimiteDeCuerpoMiddleware` (commit `dc9478c`), prueba `test_m7_h01_tamano_cuerpo.py`. |
| DEF-03 | Un `asunto` de más de 200 caracteres se recortaba en silencio, y un `?orden=` desconocido se ignoraba (200) | Media | **Incluir** ✅ | Historia 03: lista de permitidos y largo máximo dan 400 (commit `135080b`). **Cambia el contrato de la API** (ver `CHANGELOG.md`). |
| DT-13 | Claves `django-insecure-…` en el historial de Git | Alta | **Incluir** ✅ | Historia 05: revocadas por huella SHA-256 (commit `a976c7a`), decisión en [`seguridad/rotacion-secret-key.md`](seguridad/rotacion-secret-key.md). |
| — | Contraseñas con PBKDF2 en vez de Argon2id | Media | **Incluir** ✅ | Historias 04 y 10 (commits `52464a9`, `b58080b`). |
| — | Los errores 500 no traían un identificador para rastrearlos | Media | **Incluir** ✅ | Historia 06 (commit `db4b6a1`). |

### 2.2 Abiertos

| ID | Descripción | Severidad | Decisión | Justificación |
| --- | --- | --- | --- | --- |
| PROC-01 | Columnas «Decisión humana» y «Justificación humana» vacías en el AI Decision Log (§2); etiquetas `[DECISIÓN DEL EQUIPO]` y `[PENDIENTE]` en `uso-ia.md` | Alta (proceso) | **Incluir: tarea del equipo antes del tag** | La política de `uso-ia.md` dice que el documento no es definitivo mientras haya etiquetas sin resolver, y las decisiones de diseño son del equipo, no de la IA. No es código: no lo puede cerrar este PR. |
| H9 | Hallazgo de la auditoría sin descripción en el repositorio | Baja | **Diferir** (equipo) | No se puede verificar ni corregir lo que no está escrito ([AI Decision Log §6](seguridad/ai-decision-log-seguridad.md#6-veredicto-por-hallazgo-h1h14--módulo-7-historia-07)). El equipo debe recuperarlo o darlo por retirado. |
| DT-07 | N+1 consultas en `Pedido.total()` y en el serializador del pedido | Media | **Diferir** | Medido bajo carga: checkout p95 de 302,60 ms contra un umbral de 800 ms ([resultados](rendimiento/resultados-2026-11-11.md)). No es el cuello de botella hoy. Revisar si los pedidos crecen a muchos ítems o si el p95 del checkout pasa de 800 ms. |
| DT-12 | Límites de login y de peticiones en la caché en memoria de cada proceso | Media | **Diferir**, con condición de despliegue | `v1.0.0-rc1` se despliega con **un solo proceso** (así se midió: waitress, 1 proceso, 8 hilos). Pasa a **bloqueante** si se usan varios procesos o servidores: hay que configurar una caché compartida (Redis o la de base de datos). |
| A7 (amenazas) | Las lecturas (GET) no tienen límite de peticiones | Media | **Diferir** | Se mitiga en el proxy o la infraestructura (no existe aún). El catálogo aguantó 73 peticiones/s con p95 < 40 ms, sin errores. |
| DT-04 | El proyecto Django vive en `tests/` | Media | **Diferir** | Renombrar la carpeta toca el CI, la cobertura, todas las rutas de la documentación y los comandos del README. Es un riesgo alto para un cambio sin valor funcional, justo en la congelación. Va primero en la siguiente iteración. |
| DT-06 | Las excepciones del dominio conocen el código HTTP | Baja | **Diferir** | Mantenibilidad. No cambia el comportamiento. |
| DT-08 | Pruebas que verifican varios escenarios en un mismo método | Baja | **Diferir** | Claridad de las pruebas. Las pruebas nuevas de este PR usan `subTest`. |
| DT-10 | `Decisiones-tecnicas.md` desactualizado (todo en «Pendiente») | Baja | **Diferir** | Documento del equipo con responsables por nombre: lo actualiza el equipo. |
| DT-05 | La cola solo se ordena por fecha, no por estado | Baja | **Fuera de alcance** | La cola solo contiene tickets abiertos sin asignar, así que ordenar por estado no cambia nada. Se revisa si la cola llega a mostrar otros estados. |
| DT-14 | Sin MFA, recuperación de contraseña ni verificación de email | Media | **Fuera de alcance** (1.x) | Requiere un servicio de correo, que no existe (el sistema no hace peticiones salientes). Control compensatorio: bloqueo tras 5 intentos fallidos y contraseña de mínimo 10 caracteres con hash Argon2id. Riesgo residual en [modelo de amenazas](seguridad/modelo-amenazas.md) A1. |
| A09 | Sin alertas automáticas sobre el registro de auditoría | Baja | **Fuera de alcance** (1.x) | El registro existe (tabla `EventoAuditoria` y log con `id_error`). Las alertas dependen de la plataforma de despliegue. |
| — | HSTS preload desactivado (`check --deploy` W021) | Baja | **Fuera de alcance** | Decisión consciente y documentada: el preload es difícil de revertir. |

Resumen: **0 abiertos críticos o altos de código**. El único abierto de severidad alta es de proceso (PROC-01) y lo cierra el equipo antes del tag.

## 3. Política de congelación de alcance

| Dato | Valor |
| --- | --- |
| Inicio de la congelación | **2026-11-11**, al abrir el PR de `feature/modulo7-rnf-y-rc` |
| **Fecha de corte** | **2026-11-13, 23:59 (America/Bogota)**. Propuesta en este triage; el equipo puede moverla, y si lo hace la anota aquí con su fecha |
| Versión | `v1.0.0-rc1` |

Durante la congelación:

1. **Solo entran correcciones** de defectos de severidad Crítica o Alta, y lo marcado «Incluir: tarea del equipo» (PROC-01). No entran funcionalidades nuevas, refactorizaciones (DT-04, DT-06) ni cambios de contrato de la API.
2. Cada corrección entra por PR con el CI en verde: pruebas contra PostgreSQL, cobertura ≥ 85 %, bandit, pip-audit y gitleaks. Además debe tener una prueba que falle sin el cambio.
3. Un defecto nuevo se clasifica con la tabla de la §1 y se agrega a la §2.2 **antes** de corregirlo. Si es Media o Baja, se difiere.
4. Después de la fecha de corte, si el CI de `main` está en verde, se crea el tag `v1.0.0-rc1` sobre el commit de merge (ver `CHANGELOG.md`). Todo lo que llegue después va a la versión siguiente.
5. Si aparece un defecto Crítico después del tag, se corrige y se publica `v1.0.0-rc2`. El tag `rc1` no se mueve.
