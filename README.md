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
| **whitenoise** | 6.x | sirve el CSS de la interfaz cuando `DEBUG=False` | la interfaz saldría sin estilos en producción |
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
    ├── cuentas/                     módulo: registro, inicio de sesión y roles (HU-01)
    ├── catalogo/                    módulo: productos e inventario
    ├── carrito/                     módulo: checkout y pedidos
    ├── soporte/                     módulo: tickets y asignación a agentes
    ├── web/                         la interfaz web (plantillas + CSS, sin JavaScript)
    └── comun/                       errores, validaciones, roles y cabeceras de seguridad
```

### 2.1 Los módulos de dominio

La organización es **por tema del negocio**, no por tipo de archivo. Cuando cambian las reglas de los tickets, todo lo que hay que tocar está en `soporte/`.

Cada módulo repite los mismos papeles:

| Archivo | Papel | Qué hace |
| --- | --- | --- |
| `models.py` | **Entidad** | los datos que se guardan; cada objeto es una fila |
| `servicios.py` | **Servicio** | **las reglas del negocio** |
| `serializadores.py` | Presentación | convierte las entidades en diccionarios para el JSON |
| `views.py` | **Controlador** | la puerta HTTP: recibe la petición y llama al servicio |
| `urls.py` | Rutas | qué URL llega a qué vista |
| `admin.py` | Panel | cómo se ve el módulo en `/admin/` |
| `migrations/` | Migraciones | los cambios de la base de datos, generados por Django |
| `pruebas/` | **Pruebas** | un archivo por historia de usuario, más pruebas unitarias y de casos borde |

| Módulo | Entidades | Reglas principales (`servicios.py`) |
| --- | --- | --- |
| `catalogo/` | `Producto` | `listar_catalogo`, `detalle_producto` |
| `carrito/` | `Pedido`, `ItemPedido` | `realizar_checkout`, `detalle_pedido` |
| `soporte/` | `TicketSoporte`, `RegistroAsignacion` | `crear_ticket`, `cola_sin_asignar`, `tomar_ticket`, `ticket_visible_para` |
| `cuentas/` | (usa `auth.User` y el grupo `agentes`) | `autenticar` (con límite de intentos), `registrar_cliente` |
| `web/` | — | no tiene reglas: sus vistas llaman a los servicios de los otros módulos |

### 2.2 `comun/`: los errores del sistema

| Excepción | Responde | Cuándo |
| --- | --- | --- |
| `NoEncontrado` | 404 | el id no existe |
| `EstadoInvalido` | 409 | la operación no cabe en el estado actual (ej. ticket ya asignado, sin stock) |
| `DatosInvalidos` | 400 | lo que llegó está mal formado o incompleto |
| `SinPermiso` | 403 | el usuario existe pero su rol no le permite la operación (ej. un cliente tomando un ticket) |
| `NoAutenticado` | 401 | la operación requiere iniciar sesión |
| `DemasiadosIntentos` | 429 | se superó el límite de intentos de inicio de sesión |

Los servicios lanzan estas excepciones y el decorador `@api` (`comun/http.py`) las convierte en una respuesta JSON con su código HTTP. Además, `@api` exige sesión (y el rol de agente donde corresponde) y atrapa cualquier error no previsto: al cliente le devuelve un 500 genérico y el detalle queda en el log. Las validaciones de entrada (`entero`, `texto`) están en `comun/validaciones.py`, separadas de HTTP. Funcionan con **lista de permitidos**: solo enteros de verdad, con cota, y texto sin caracteres que PostgreSQL rechaza. El detalle está en [`docs/seguridad/`](docs/seguridad/semana-13.md).

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
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
#   ↑ pega el resultado en SECRET_KEY= dentro de .env (sin SECRET_KEY no arranca)
python manage.py migrate
python manage.py createsuperuser
```

> Si `activate` da un error de permisos en PowerShell, corre una vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 4.3 Cargar datos de ejemplo

```bash
python manage.py cargar_datos_demo
```

Llena las tablas de Django con los mismos datos de `database/02_seed.sql`: 5 productos (uno agotado), 3 clientes (`ana`, `luis`, `maria`), 2 agentes (`carlos`, `diana`, en el grupo `agentes`), 3 pedidos y 3 tickets (uno abierto, uno en proceso y uno cerrado). La clave de todos los usuarios de ejemplo es `demo12345`: **solo para la demo local**.

Si ya hay datos, no hace nada. Para borrarlos y cargarlos de nuevo: `python manage.py cargar_datos_demo --reset`.

> Las tablas que crean los scripts de `database/` (`producto`, `pedido`, `cliente`…) **no son las que usa Django**. Django usa las suyas, con el nombre de la app adelante: `catalogo_producto`, `carrito_pedido`, `soporte_ticketsoporte`, `auth_user`.

### 4.4 Arrancar el servidor

```bash
python manage.py runserver
```

- **Interfaz web: `http://127.0.0.1:8000/`**. Entra como `ana` (cliente) o `carlos` (agente). Ver [`docs/interfaz.md`](docs/interfaz.md).
- API: `http://127.0.0.1:8000/api/`
- Panel de administración: `http://127.0.0.1:8000/admin/`

### 4.5 Probar la API

La API usa la **sesión** del usuario (ya no recibe `id_cliente` ni `id_agente` en el cuerpo) y exige token **CSRF** en cada POST. Con los datos de ejemplo cargados (paso 4.3), en **Git Bash**:

```bash
# Catálogo: es público
curl -s localhost:8000/api/productos/

# 1) Pedir la cookie CSRF y 2) entrar como ana (las cookies quedan en cookies.txt)
curl -s -c cookies.txt localhost:8000/api/sesion/ > /dev/null
TOKEN=$(grep csrftoken cookies.txt | awk '{print $7}')
curl -s -b cookies.txt -c cookies.txt -H "X-CSRFToken: $TOKEN" -H 'Content-Type: application/json' \
  -X POST localhost:8000/api/sesion/ -d '{"usuario": "ana", "clave": "demo12345"}'
TOKEN=$(grep csrftoken cookies.txt | awk '{print $7}')   # el token rota al iniciar sesión

# HU-04: comprar a nombre de la sesión
curl -s -b cookies.txt -H "X-CSRFToken: $TOKEN" -H 'Content-Type: application/json' \
  -X POST localhost:8000/api/pedidos/ -d '{"items": [{"id_producto": 1, "cantidad": 1}]}'

# HU-05: radicar una PQR sobre uno de MIS pedidos (usa el id que devolvió el paso anterior)
curl -s -b cookies.txt -H "X-CSRFToken: $TOKEN" -H 'Content-Type: application/json' \
  -X POST localhost:8000/api/tickets/ -d '{"tipo": "RECLAMO", "id_pedido": 4, "asunto": "Paquete", "descripcion": "No llegó"}'
```

Para probar la cola (HU-07) y tomar tickets (HU-08), repite el inicio de sesión como `carlos`. Es más cómodo hacerlo desde la interfaz web.

### 4.6 Endpoints

| Método | Ruta | Historia | Acceso | Respuestas |
| --- | --- | --- | --- | --- |
| GET · POST · DELETE | `/api/sesion/` | HU-01 | público | 200 · 204 · 401 · 429 |
| POST | `/api/registro/` | HU-01 | público | 201 · 400 |
| GET | `/api/productos/` | HU-02 | público | 200 |
| GET | `/api/productos/<id>/` | HU-02 | público | 200 · 404 |
| GET | `/api/pedidos/` | HU-04 | sesión | 200 (mis pedidos) |
| POST | `/api/pedidos/` | HU-04 | sesión | 201 · 400 · 401 · 404 · 409 (sin stock) |
| GET | `/api/pedidos/<id>/` | HU-04, HU-09 | dueño o agente | 200 · 401 · 404 |
| GET | `/api/tickets/` | HU-06 | sesión | 200 (mis tickets) |
| POST | `/api/tickets/` | HU-05 | sesión | 201 · 400 · 401 · 404 |
| GET | `/api/tickets/cola/?orden=antiguos` o `recientes` | HU-07 | agente | 200 · 401 · 403 |
| GET | `/api/tickets/<id>/` | HU-05 | dueño o agente | 200 · 401 · 404 |
| POST | `/api/tickets/<id>/tomar/` | HU-08 | agente | 200 · 400 · 401 · 403 · 404 · 409 (ya asignado) |

Un pedido o ticket **ajeno responde 404**, igual que uno inexistente (ADL-03). Cualquier campo del cuerpo que no esté en la lista de permitidos responde 400.

---

## 5. Las pruebas

### 5.1 Dónde viven

Cada módulo tiene una carpeta `pruebas/` con tres tipos de archivo:

- `test_huXX_*.py`: **integración/funcionales**. Un archivo por historia de usuario, que recorre HTTP → servicio → base de datos y verifica cada criterio de aceptación.
- `test_unitarias_*.py`: **unitarias**. Prueban reglas del servicio o del modelo llamándolas directamente, sin HTTP (las de modelo y validación ni siquiera tocan la base de datos).
- `test_casos_borde_*.py`: **casos borde** de punta a punta (repetidos, límites de stock, JSON mal formado, roles, estados cerrados…).

| Archivo de prueba | Tipo | Historia | Cuántas |
| --- | --- | --- | --- |
| `catalogo/pruebas/test_hu02_consultar_catalogo.py` | integración | HU-02 Consultar catálogo | 3 |
| `catalogo/pruebas/test_unitarias_catalogo.py` | unitaria | HU-02 | 5 |
| `carrito/pruebas/test_hu04_checkout.py` | integración | HU-04 Checkout | 3 |
| `carrito/pruebas/test_unitarias_checkout.py` | unitaria | HU-04 | 8 |
| `carrito/pruebas/test_casos_borde_checkout.py` | casos borde | HU-04 | 7 |
| `soporte/pruebas/test_hu05_crear_ticket.py` | integración | HU-05 Crear ticket | 3 |
| `soporte/pruebas/test_hu07_cola_sin_asignar.py` | integración | HU-07 Cola sin asignar | 3 |
| `soporte/pruebas/test_hu08_tomar_ticket.py` | integración | HU-08 Tomar ticket (concurrencia) | 3 |
| `soporte/pruebas/test_unitarias_soporte.py` | unitaria | HU-05, HU-07, HU-08 | 9 |
| `soporte/pruebas/test_casos_borde_soporte.py` | casos borde | HU-05, HU-07, HU-08 | 8 |
| `comun/pruebas/test_unitarias_validaciones.py` | unitaria | validaciones compartidas | 10 |
| `comun/pruebas/test_unitarias_seguridad.py` | unitaria | validación, roles, carrito en sesión | 10 |
| `comun/pruebas/test_seguridad.py` | seguridad | hallazgos de la auditoría (ADL-01 a ADL-07, H13, H14) y HU-01 | 25 |
| `comun/pruebas/test_ataques_simulados.py` | seguridad | ataques simulados de la semana 13: SQLi, XSS, IDOR, divulgación, fuerza bruta | 11 |
| `cuentas/pruebas/test_auditoria_y_limites.py` | seguridad | registro de eventos críticos y límite de peticiones | 9 |
| `web/pruebas/test_interfaz.py` | integración (web) | HU-01 y HU-04 a HU-09 desde la interfaz | 15 |
| `catalogo/pruebas/test_datos_demo.py` | integración | comando `cargar_datos_demo` | 2 |
| | | | **134** |

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
| `python manage.py cargar_datos_demo` | carga datos de ejemplo (`--reset` para recargarlos) |
| `git log --oneline --graph` | la historia del proyecto en una pantalla |

---

## 7. Errores comunes al arrancar

| Síntoma | Causa casi siempre | Salida |
| --- | --- | --- |
| `ImproperlyConfigured: Falta SECRET_KEY` | el `.env` no tiene `SECRET_KEY` | genera una (paso 4.2) y pégala en `tests/.env` |
| `SECRET_KEY es de ejemplo o muy corta` | `DEBUG` está apagado y la clave es la de ejemplo | pon `DEBUG=True` en tu `.env` local o usa una clave real |
| la página sale sin estilos con `DEBUG=False` | faltan los estáticos | `python manage.py collectstatic` |
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
- [Definición de Terminado](docs/definicion-de-terminado.md)
- [Revisión de código (SOLID/GRASP) y refactorizaciones](docs/revision-codigo.md)
- [Registro de deuda técnica](docs/deuda-tecnica.md)
- [Seguridad, semana 13: evidencia y checklist](docs/seguridad/semana-13.md)
- [Modelo de amenazas](docs/seguridad/modelo-amenazas.md)
- [Correcciones de seguridad y RNF](docs/seguridad/correcciones-seguridad.md)
- [AI Decision Log de la auditoría de seguridad](docs/seguridad/ai-decision-log-seguridad.md)
- [Interfaz web: paleta y pantallas](docs/interfaz.md)
