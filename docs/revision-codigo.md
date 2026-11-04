# Revisión de código: defectos, code smells y refactorizaciones

Revisión del código de `tests/` (catálogo, carrito, soporte y comun) contra
principios **SOLID** y **GRASP**. Cada observación tiene un argumento técnico,
una evidencia (archivo) y una decisión: *corregido*, *refactorizado* o
*registrado como deuda*.

## Cómo revisamos

1. Todo cambio entra por Pull Request hacia `develop` o `main`; nadie fusiona
   su propio PR sin la aprobación del otro integrante.
2. El revisor deja comentarios en las líneas del PR usando el formato
   **Observación → Principio afectado → Riesgo → Propuesta**.
3. El autor responde cada comentario: lo corrige, o lo registra en
   `deuda-tecnica.md` con su prioridad.
4. Las observaciones importantes se copian a este archivo para que quede
   constancia.

## Observaciones

| ID | Tipo | Observación | Principio | Decisión |
| --- | --- | --- | --- | --- |
| RC-01 | **Defecto** | `tomar_ticket` no verificaba el rol: un **cliente** podía asignarse un ticket | Regla de negocio de HU-08 / *Experto en información* (GRASP) | ✅ Corregido |
| RC-02 | Inconsistencia | `TicketSoporte` no tiene el estado **Resuelto** que piden HU-06 y HU-10 | — | 📋 Deuda DT-03 |
| RC-03 | Code smell | `a_dict()` (serializar a JSON) vivía en `servicios.py` junto a las reglas de negocio | **S** de SOLID (responsabilidad única) / *Alta cohesión* (GRASP) | ✅ Refactorizado |
| RC-04 | Code smell | Los servicios importaban `entero` desde `comun/http.py`: la capa de negocio dependía de la capa web | **D** de SOLID (inversión de dependencias) / *Bajo acoplamiento* (GRASP) | ✅ Refactorizado |
| RC-05 | Code smell | `ErrorDeNegocio` lleva el código HTTP (`status`) dentro de la excepción del dominio | **D** de SOLID / *Variaciones protegidas* (GRASP) | 📋 Deuda DT-06 |
| RC-06 | Defecto latente | `Pedido.total()` sumaba con `start=0` (entero) en vez de `Decimal` | Correctitud de tipos monetarios | ✅ Corregido |
| RC-07 | Rendimiento | `Pedido.total()` y `a_dict` recorren `items.all()`: N+1 consultas si no hay `prefetch_related` | *Bajo acoplamiento* con el ORM | 📋 Deuda DT-07 |
| RC-08 | Code smell (pruebas) | Una sola prueba verifica 6 escenarios distintos (`test_criterio3_datos_invalidos...` de HU-04): si falla el primero, los demás no se ejecutan | Pruebas FIRST / una razón para fallar | 📋 Deuda DT-08 (los nuevos casos borde ya usan `subTest`) |
| RC-09 | Nombres | El proyecto Django está en una carpeta llamada `tests/`; confunde código de producción con pruebas | Claridad / *Creador* | 📋 Deuda DT-04 |
| RC-10 | Seguridad | `settings.py` trae SECRET_KEY y contraseña de la base de datos por defecto en el código | Configuración segura | 📋 Deuda DT-09 |
| RC-11 | Documentación | `settings.py` hablaba de `esqueleto/.env` (carpeta que ya no existe); `Decisiones-tecnicas.md` tiene todo en "Pendiente" | — | ✅ Corregido el comentario; doc → DT-10 |
| RC-12 | Diseño | La identidad del usuario llega en el cuerpo (`id_cliente`, `id_agente`): cualquiera puede hacerse pasar por otro | Seguridad / HU-01 | 📋 Deuda DT-01 |

## Detalle de los cambios hechos

### RC-01 · Un cliente podía tomar tickets (defecto corregido)

**Argumento.** HU-08 dice "Como **agente** de servicio al cliente, quiero
tomar un ticket". El servicio solo comprobaba que el usuario existiera.
Con `{"id_agente": <id de un cliente>}` el ticket quedaba asignado a un
cliente, y salía de la cola de los agentes de verdad.

**Cómo se corrigió (prueba primero).**
1. Se escribió `test_un_cliente_no_puede_tomar_tickets` → **falló** (rojo),
   lo que demostró el defecto.
2. Se agregó la excepción `SinPermiso` (403) en `comun/excepciones.py` y la
   validación `if not agente.is_staff` en `soporte/servicios.py`.
3. La prueba pasó (verde) y las 17 pruebas previas siguieron en verde.

### RC-03 y RC-04 · Refactorizaciones sin cambio de comportamiento

| Antes | Después |
| --- | --- |
| `catalogo/servicios.py`, `carrito/servicios.py`, `soporte/servicios.py` tenían `a_dict()` | Cada módulo tiene `serializadores.py`; la vista llama `serializadores.a_dict(...)` |
| `entero()` en `comun/http.py` | `entero()` en `comun/validaciones.py`; `http.py` queda solo con lo de HTTP |

**Cómo se garantizó que el comportamiento observable no cambió:**
las 17 pruebas de integración existentes (que verifican el JSON exacto que
devuelve cada endpoint) se corrieron **antes y después** del refactor contra
PostgreSQL, sin tocar ninguna prueba: 17/17 en verde en ambos casos. Recién
después se agregaron las pruebas nuevas.
