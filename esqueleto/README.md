# Walking Skeleton — proyecto_pagina_web

Esqueleto funcional de punta a punta (request → backend → base de datos →
respuesta), siguiendo el concepto de "walking skeleton" de Alistair Cockburn /
Martin Fowler: simple en funcionalidad, pero completo en arquitectura.

## Cómo correrlo

```bash
python -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser   # opcional, para entrar a /admin/

python manage.py runserver
```

Por defecto usa SQLite (cero configuración). Para conectar a PostgreSQL,
define estas variables de entorno antes de correr los comandos de arriba:

```bash
export DB_ENGINE=postgres
export DB_NAME=proyecto_pagina_web
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_HOST=localhost
export DB_PORT=5432
```

## Endpoints disponibles

- `GET /carrito/checkout/?producto_id=1&cantidad=2`
  Checkout simulado: descuenta stock de forma atómica con `select_for_update`.

- `GET /soporte/tomar-ticket/?ticket_id=1&agente_id=1`
  Asignación de ticket con bloqueo pesimista — este es el "problema duro"
  declarado en `problema-duro.md` (concurrencia sobre asignación de tickets).

- `/admin/` — panel de administración de Django para ver los datos guardados.

## Correr el test de concurrencia (evidencia del problema duro)

```bash
python manage.py test soporte
```

Este test simula dos agentes intentando tomar el mismo ticket al mismo
tiempo con hilos concurrentes, y verifica:
1. Solo uno de los dos obtiene el ticket.
2. El otro recibe un error 409 ("ticket ya asignado").
3. Queda exactamente un registro en `Asignacion` (log auditable).

## Qué cambió respecto a los archivos que ya tenías

- `config/urls.py` no incluía las rutas de `carrito` ni `soporte` — sin esto
  ningún endpoint era alcanzable por HTTP.
- `config/settings.py` no tenía la sección `DATABASES` (y estaba cortado a
  media línea) — se agregó, configurable por variables de entorno.
- `carrito/views.py` no validaba `producto_id`/`cantidad` en la frontera —
  se agregó, devolviendo 400/404 en vez de un error 500.
- Se agregó la app `soporte` completa (modelos, vista, test de concurrencia)
  para cubrir el problema duro que ya habían declarado en `problema-duro.md`.
- Se quitó el campo `usuario` de `Pedido` por ahora (no había login en el
  esqueleto); cuando agreguen autenticación real, se vuelve a añadir como
  `ForeignKey(settings.AUTH_USER_MODEL)`.

## Pendiente para completar la evidencia que piden

- [ ] Conectar esto a un pipeline de CI (GitHub Actions) que corra
      `python manage.py test` en cada push a `main`.
- [ ] Decidir si el diagrama de dominio en `docs/models/` necesita
      actualizarse con las entidades `Agente`, `Ticket`, `Asignacion`.
