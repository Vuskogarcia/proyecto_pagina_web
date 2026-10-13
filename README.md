# SHOP-HUB

Plataforma web de venta en línea (catálogo, carrito, checkout, inventario) con un canal de soporte postventa integrado: cada ticket de soporte queda vinculado al pedido que lo originó, dando trazabilidad completa entre lo que el cliente compró y lo que está reclamando.

**Problema técnico central:** evitar que dos agentes tomen el mismo ticket de soporte al mismo tiempo (ver [`docs/problema-duro.md`](docs/problema-duro.md)).

---

## 1. El stack: qué es cada pieza

| Pieza | Versión | Qué resuelve | Qué pasaría sin ella |
| --- | --- | --- | --- |
| **Python** | 3.11+ | el lenguaje | — |
| **Django** | 5.x | servidor web, URLs, ORM, migraciones, panel `/admin/` y pruebas | habría que escribir el SQL, el ruteo y el servidor a mano |
| **PostgreSQL** | 15 | la base de datos real; soporta `SELECT ... FOR UPDATE` | no habría forma confiable de bloquear un ticket mientras se asigna |
| **psycopg2** | 2.9+ | el driver que conecta Django con PostgreSQL | Django no podría hablar con la base de datos |
| **python-dotenv** | 1.x | lee la configuración desde el archivo `.env` | habría que poner contraseñas en el código |
| **Docker Compose** | — | levanta PostgreSQL con un solo comando | cada integrante tendría que instalar y configurar Postgres a mano |
| **GitHub Actions** | — | corre las pruebas en cada push, en un computador que no es el tuyo | «en mi máquina funciona» seguiría siendo una defensa |

---

## 2. El árbol completo, comentado

```
proyecto_pagina_web/
│
├── README.md                    ← la entrada del proyecto (este archivo)
├── docker-compose.yml           ← levanta PostgreSQL con un comando
├── .gitignore                   ← qué NO se versiona (venv, .env, cachés)
├── .github/workflows/ci.yml     ← qué hace el servidor en cada push
│
├── database/                    ← scripts SQL del modelo E-R (esquema y datos de ejemplo)
├── docs/                        ← visión, historias, decisiones, problema duro
│   └── historias-implementadas.md   qué historia prueba cada test
│
└── tests/                       ← EL PROYECTO DJANGO
    ├── manage.py                    el punto de arranque (comandos de Django)
    ├── requirements.txt             qué librerías necesita
    ├── .env.example                 plantilla de configuración (copiar a .env)
    ├── config/                      configuración: settings.py y urls.py
    │
    ├── catalogo/                    módulo: productos e inventario
    ├── carrito/                     módulo: checkout y pedidos
    ├── soporte/                     módulo: tickets y asignación a agentes
    └── comun/                       los tres tipos de error y utilidades compartidas
```

### 2.1 Los módulos de dominio

La organización es **por tema del negocio**, no por tipo de archivo. Cuando cambian las reglas de los tickets, todo lo que hay que tocar está en `soporte/`.

Cada módulo repite los mismos papeles:

| Archivo | Papel | Qué hace |
| --- | --- | --- |
| `models.py` | **Entidad** | los datos que se guardan; cada objeto es una fila |
| `servicios.py` | **Servicio** | **las reglas del negocio** |
| `views.py` | **Controlador** | la puerta HTTP: recibe la petición y llama al servicio |
| `urls.py` | Rutas | qué URL llega a qué vista |
| `admin.py` | Panel | cómo se ve el módulo en `/admin/` |
| `migrations/` | Migraciones | los cambios de la base de datos, generados por Django |
| `pruebas/` | **Pruebas** | un archivo por historia de usuario |

| Módulo | Entidades | Reglas principales (`servicios.py`) |
| --- | --- | --- |
| `catalogo/` | `Producto` | `listar_catalogo`, `detalle_producto` |
| `carrito/` | `Pedido`, `ItemPedido` | `realizar_checkout`, `detalle_pedido` |
| `soporte/` | `TicketSoporte`, `RegistroAsignacion` | `crear_ticket`, `cola_sin_asignar`, `tomar_ticket` |

### 2.2 `comun/`: los tres errores del sistema

| Excepción | Responde | Cuándo |
| --- | --- | --- |
| `NoEncontrado` | 404 | el id no existe |
| `EstadoInvalido` | 409 | la operación no cabe en el estado actual (ej. ticket ya asignado, sin stock) |
| `DatosInvalidos` | 400 | lo que llegó está mal formado o incompleto |

Los servicios lanzan estas excepciones y el decorador `@api` (`comun/http.py`) las convierte en una respuesta JSON con su código HTTP.

---

## 3. El recorrido de una petición

```
HTTP            views.py           servicios.py          models.py         PostgreSQL
 │                 │                    │                    │                 │
 │  POST /api/...  │                    │                    │                 │
 ├────────────────►│                    │                    │                 │
 │                 │  llama al servicio │                    │                 │
 │                 ├───────────────────►│                    │                 │
 │                 │                    │ aplica LAS REGLAS  │                 │
 │                 │                    ├───────────────────►│  SELECT ...     │
 │                 │                    │                    ├────────────────►│
 │                 │                    │◄───────────────────┤                 │
 │                 │                    ├───────────────────►│  INSERT ...     │
 │                 │                    │                    ├────────────────►│
 │◄────────────────┤◄───────────────────┤                    │                 │
 │  JSON o error   │                    │                    │                 │
```

**El controlador no decide, el servicio decide, el modelo no piensa.** Cuando busques dónde vive una regla de negocio, empieza por `servicios.py`.

---

## 4. Cómo ejecutar la aplicación

### Requisitos

- Python 3.11 o más nuevo
- Docker Desktop (para PostgreSQL)
- Git

### 4.1 Levantar PostgreSQL

Desde la raíz del repositorio:

```bash
docker compose up -d db
```

Crea la base `ecommerce_db` con usuario `admin` y contraseña `adminpassword`.

### 4.2 Preparar el proyecto

Todo lo que sigue se ejecuta desde la carpeta `tests/`:

```bash
cd tests
python -m venv venv
venv\Scripts\activate          # Windows (en Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env         # Windows (en Linux/macOS: cp .env.example .env)
python manage.py migrate
python manage.py createsuperuser
```

> Si `activate` da un error de permisos en PowerShell, corre una vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 4.3 Arrancar el servidor

```bash
python manage.py runserver
```

- API: `http://127.0.0.1:8000/api/`
- Panel de administración: `http://127.0.0.1:8000/admin/`

### 4.4 Probar que responde

Primero crea un producto en `/admin/` (Productos → Añadir). Después, en **Git Bash**:

```bash
# HU-02: ver el catálogo
curl -s localhost:8000/api/productos/

# HU-04: comprar 2 unidades del producto 1 (cliente 1 = el superusuario)
curl -s -X POST localhost:8000/api/pedidos/ -H 'Content-Type: application/json' \
  -d '{"id_cliente": 1, "items": [{"id_producto": 1, "cantidad": 2}]}'

# HU-05: crear un ticket sobre ese pedido
curl -s -X POST localhost:8000/api/tickets/ -H 'Content-Type: application/json' \
  -d '{"id_cliente": 1, "id_pedido": 1, "asunto": "Paquete", "descripcion": "No llegó"}'

# HU-07: ver la cola de tickets sin asignar
curl -s localhost:8000/api/tickets/cola/

# HU-08: el agente 1 toma el ticket 1 (repítelo: la segunda vez responde 409)
curl -s -X POST localhost:8000/api/tickets/1/tomar/ -H 'Content-Type: application/json' \
  -d '{"id_agente": 1}'
```

En Windows usa **Git Bash** para que `curl` y las comillas se comporten igual.

### 4.5 Endpoints

| Método | Ruta | Historia | Respuestas |
| --- | --- | --- | --- |
| GET | `/api/productos/` | HU-02 | 200 |
| GET | `/api/productos/<id>/` | HU-02 | 200 · 404 |
| POST | `/api/pedidos/` | HU-04 | 201 · 400 · 404 · 409 (sin stock) |
| GET | `/api/pedidos/<id>/` | HU-04 | 200 · 404 |
| POST | `/api/tickets/` | HU-05 | 201 · 400 · 404 |
| GET | `/api/tickets/cola/` | HU-07 | 200 |
| GET | `/api/tickets/<id>/` | HU-05 | 200 · 404 |
| POST | `/api/tickets/<id>/tomar/` | HU-08 | 200 · 404 · 409 (ya asignado) |

---

## 5. Las pruebas

### 5.1 Dónde viven

Cada módulo tiene una carpeta `pruebas/` con **un archivo por historia de usuario**:

| Archivo de prueba | Historia | Cuántas |
| --- | --- | --- |
| `catalogo/pruebas/test_hu02_consultar_catalogo.py` | HU-02 Consultar catálogo | 5 |
| `carrito/pruebas/test_hu04_checkout.py` | HU-04 Checkout | 7 |
| `soporte/pruebas/test_hu05_crear_ticket.py` | HU-05 Crear ticket | 7 |
| `soporte/pruebas/test_hu07_cola_sin_asignar.py` | HU-07 Cola sin asignar | 3 |
| `soporte/pruebas/test_hu08_tomar_ticket.py` | HU-08 Tomar ticket (concurrencia) | 5 |
| | | **27** |

`comun/fabricas.py` **no tiene pruebas**: es una fábrica de datos de prueba que crea clientes, productos, pedidos y tickets ya listos, para no repetir las mismas líneas en cada test.

La relación criterio de aceptación → prueba está en [`docs/historias-implementadas.md`](docs/historias-implementadas.md).

### 5.2 Cómo se corren

| Qué | Comando (desde `tests/`) |
| --- | --- |
| Todas | `python manage.py test` |
| Un módulo | `python manage.py test soporte` |
| Una historia | `python manage.py test soporte.pruebas.test_hu08_tomar_ticket` |
| Con detalle | `python manage.py test -v 2` |

### 5.3 La anatomía

Toda prueba tiene tres partes, en el mismo orden:

```python
def test_criterio2_un_ticket_ya_tomado_responde_409(self):
    self.tomar(self.agente1)                       # ① PREPARAR el escenario

    respuesta = self.tomar(self.agente2)           # ② EJECUTAR una acción

    self.assertEqual(respuesta.status_code, 409)   # ③ VERIFICAR qué debió pasar
```

**Preparar, ejecutar, verificar.** El nombre de cada prueba dice qué criterio de aceptación comprueba.

### 5.4 La prueba de concurrencia

`HU08ConcurrenciaTests` lanza dos hilos que intentan tomar el mismo ticket al mismo tiempo, cada uno con su propia conexión a PostgreSQL. Verifica que exactamente uno lo consigue, el otro es rechazado y queda un solo registro de asignación. **Necesita PostgreSQL**: SQLite no soporta `SELECT ... FOR UPDATE`.

---

## 6. Comandos que vas a usar

| Comando | Qué hace |
| --- | --- |
| `docker compose up -d db` | levanta PostgreSQL |
| `docker compose down -v` | apaga PostgreSQL y **borra sus datos** |
| `python manage.py runserver` | arranca la aplicación |
| `python manage.py test` | corre todas las pruebas |
| `python manage.py makemigrations` | genera migraciones después de cambiar un `models.py` |
| `python manage.py migrate` | aplica las migraciones a la base de datos |
| `python manage.py createsuperuser` | crea un usuario para `/admin/` |
| `git log --oneline --graph` | la historia del proyecto en una pantalla |

---

## 7. Errores comunes al arrancar

| Síntoma | Causa casi siempre | Salida |
| --- | --- | --- |
| `connection refused` en el puerto 5432 | PostgreSQL no está corriendo | abre Docker Desktop y corre `docker compose up -d db` |
| `No se puede cargar el archivo ...\Activate.ps1` | PowerShell bloquea scripts | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `No module named django` | el entorno virtual no está activado | `venv\Scripts\activate` (aparece `(venv)` al inicio de la línea) |
| `relation ... does not exist` | faltan migraciones | `python manage.py migrate` |
| errores de migración tras actualizar el repo | tu base tiene un esquema viejo | `docker compose down -v`, `docker compose up -d db` y `python manage.py migrate` |
| `That port is already in use` | otro servidor corriendo | ciérralo, o `python manage.py runserver 8001` |
| `curl` se comporta raro en Windows | PowerShell tiene su propio `curl` | usa Git Bash |

---

## Ramas del repositorio

- `main`: rama estable / entregable del curso.
- `develop`: rama de integración de funcionalidades en desarrollo.

## Documentación adicional

- [Visión del producto](docs/vision-producto.md)
- [Historias de usuario (backlog)](docs/Historia%20de%20usuario/historias.md)
- [Historias implementadas y sus pruebas](docs/historias-implementadas.md)
- [Problema duro](docs/problema-duro.md)
- [Decisiones técnicas](docs/Decisiones-tecnicas.md)
- [Selección de la rebanada vertical](docs/rebanada.md)
