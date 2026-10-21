# Registro de deuda técnica

Cada deuda tiene un origen, un impacto, un esfuerzo estimado y una prioridad.

- **Impacto:** Alto = rompe una regla del negocio o un criterio de aceptación; Medio = dificulta mantener o escalar; Bajo = estético o de claridad.
- **Esfuerzo:** S (< 2 h) · M (medio día) · L (1 día o más).
- **Prioridad:** P1 = antes de la entrega final · P2 = siguiente iteración · P3 = cuando haya tiempo.

| ID | Deuda | Origen | Impacto | Esfuerzo | Prioridad | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| DT-01 | La identidad (`id_cliente`, `id_agente`) llega en el cuerpo de la petición; no hay login ni roles (HU-01) | RC-12 | Alto | L | **P1** | Abierta |
| DT-02 | HU-04 criterio 1: no existe carrito editable (agregar/quitar antes de pagar); el checkout recibe todo en una petición | DoD D1 | Alto | M | **P1** | Abierta |
| DT-03 | Falta el estado **Resuelto** en `TicketSoporte` (lo piden HU-06 y HU-10) | RC-02 | Alto | S | **P1** | Abierta |
| DT-04 | El proyecto Django vive en `tests/`; renombrar a `app/` o `backend/` | RC-09 | Medio | S | P2 | Abierta |
| DT-05 | HU-07 criterio 3: la cola solo se ordena por fecha, no por estado | DoD D1 | Medio | S | P2 | Abierta |
| DT-06 | Las excepciones del dominio conocen el código HTTP; mover el mapeo excepción → status al decorador `@api` | RC-05 | Medio | S | P2 | Abierta |
| DT-07 | N+1 consultas en `Pedido.total()` / serializador si no hay `prefetch_related` | RC-07 | Medio | S | P2 | Abierta |
| DT-08 | Pruebas que verifican varios escenarios en un solo método (HU-04 criterio 3, HU-05 reglas) | RC-08 | Bajo | S | P3 | Abierta |
| DT-09 | SECRET_KEY y contraseña de BD por defecto en `settings.py` | RC-10 | Medio | S | P2 | Abierta |
| DT-10 | `Decisiones-tecnicas.md` desactualizado (todo en "Pendiente") | RC-11 | Bajo | S | P3 | Abierta |
| DT-11 | No hay interfaz gráfica: la demo usa `curl` y `/admin/` | Visión del producto | Medio | L | P2 | Abierta |
| — | Un cliente podía tomar tickets | RC-01 | Alto | S | — | ✅ Pagada |
| — | Serialización mezclada con reglas de negocio | RC-03 | Medio | S | — | ✅ Pagada |
| — | Servicios dependían de `comun/http.py` | RC-04 | Medio | S | — | ✅ Pagada |
| — | `Pedido.total()` sumaba con entero en vez de `Decimal` | RC-06 | Bajo | S | — | ✅ Pagada |

## Por qué este orden

1. **P1** son las que rompen criterios de aceptación ya comprometidos o la
   seguridad básica: sin DT-01 cualquiera puede actuar como otro usuario, y
   DT-02/DT-03 dejan historias incompletas.
2. **P2** no rompen nada hoy, pero encarecen cada cambio futuro (acoplamiento,
   rendimiento, nombres).
3. **P3** son de claridad y se pagan "de paso" cuando se toque ese archivo.

Cuando una deuda se paga se marca ✅ y se enlaza el PR que la cerró.
