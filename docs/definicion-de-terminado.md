# Definición de Terminado (DoD)

Una historia de usuario está **terminada** solo cuando cumple **todos** los
puntos de esta lista. Si falta uno, la historia sigue "en progreso", aunque el
código funcione en la máquina de alguien.

## La lista

| # | Criterio | Cómo se comprueba |
| --- | --- | --- |
| D1 | Todos los criterios de aceptación de la historia están implementados (o el pendiente está registrado en `deuda-tecnica.md`) | tabla de la historia en `historias-implementadas.md` |
| D2 | La lógica vive en `servicios.py`; la vista solo traduce HTTP ↔ servicio | revisión de código |
| D3 | Las entradas se validan y cada error responde con su código (400 / 403 / 404 / 409) y un mensaje claro en JSON | pruebas de casos borde |
| D4 | Hay **pruebas unitarias** de las reglas (servicio y modelo, sin HTTP) | archivos `test_unitarias_*.py` |
| D5 | Hay **pruebas de integración/funcionales** por cada criterio de aceptación (petición HTTP → base de datos) | archivos `test_huXX_*.py` |
| D6 | Los casos borde relevantes de la historia tienen prueba | archivos `test_casos_borde_*.py` |
| D7 | `python manage.py test` pasa completo contra PostgreSQL y el CI de GitHub Actions está en verde | pestaña *Actions* del PR |
| D8 | `makemigrations --check` no detecta migraciones faltantes | paso del CI |
| D9 | El cambio entró por Pull Request y **otro integrante** lo revisó y dejó al menos un comentario técnico | conversación del PR + `revision-codigo.md` |
| D10 | README y `historias-implementadas.md` están actualizados (endpoint, respuestas, pruebas) | revisión del PR |
| D11 | Se puede demostrar con los datos de `cargar_datos_demo` | guion de demo del README §4.5 |

## Aplicación a las historias implementadas

El *Walking Skeleton* es **HU-02** (consultar catálogo, ver `rebanada.md`).
Después de él se terminaron **4 historias**: HU-04, HU-05, HU-07 y HU-08.

| Criterio | HU-02 (skeleton) | HU-04 Checkout | HU-05 Crear ticket | HU-07 Cola | HU-08 Tomar ticket |
| --- | --- | --- | --- | --- | --- |
| D1 Criterios de aceptación | ✅ 4/4 | ⚠️ 3/4 (falta criterio 1: carrito editable → DT-02) | ✅ 4/4 | ⚠️ 3/4 (orden por estado → DT-05) | ✅ 4/4 |
| D2 Lógica en el servicio | ✅ | ✅ | ✅ | ✅ | ✅ |
| D3 Validación y errores | ✅ 404 | ✅ 400/404/409 | ✅ 400/404 | ✅ | ✅ 400/403/404/409 |
| D4 Pruebas unitarias | ✅ | ✅ | ✅ | ✅ (servicio vía cola) | ✅ |
| D5 Pruebas de integración | ✅ 3 | ✅ 3 | ✅ 3 | ✅ 3 | ✅ 3 (incluye concurrencia) |
| D6 Casos borde | ✅ | ✅ 7 | ✅ | ✅ | ✅ 7 (compartidos con HU-05/07) |
| D7 CI en verde | ✅ | ✅ | ✅ | ✅ | ✅ |
| D8 Migraciones | ✅ | ✅ | ✅ | ✅ | ✅ |
| D9 Revisión por par | ⏳ | ⏳ | ⏳ | ⏳ | ⏳ |
| D10 Documentación | ✅ | ✅ | ✅ | ✅ | ✅ |
| D11 Demostrable | ✅ | ✅ | ✅ | ✅ | ✅ |

⏳ **D9 queda pendiente hasta que Esteban revise el PR de esta rama** y deje sus
observaciones (ver `revision-codigo.md`, sección "Cómo revisamos").

Los criterios marcados ⚠️ no bloquean la demo: el pendiente está registrado y
priorizado en `deuda-tecnica.md`.
