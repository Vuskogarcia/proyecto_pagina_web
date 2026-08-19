# SHOP-HUB

Plataforma web de venta en línea (catálogo, carrito, checkout, inventario) con un canal de soporte postventa integrado: cada ticket de soporte queda vinculado al pedido que lo originó, dando trazabilidad completa entre lo que el cliente compró y lo que está reclamando.

## Stack

- **Backend:** Python 3.x + Django
- **Base de datos:** PostgreSQL
- **Gestión de dependencias:** pip / `requirements.txt`

## Requisitos previos

- Python 3.11+ instalado
- PostgreSQL 14+ instalado y corriendo
- `pip` y `venv` disponibles
- Git

## 1. Clonar el repositorio

```bash
git clone https://github.com/<org>/shop-hub.git
cd shop-hub
```

## 2. Crear y activar entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate   # En Windows: venv\Scripts\activate
```

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

## 4. Configurar variables de entorno

Copia el archivo de ejemplo y completa los valores según tu entorno local:

```bash
cp .env.example .env
```

Variables mínimas esperadas en `.env`:

```
DEBUG=True
SECRET_KEY=<genera-una-clave-secreta>
DATABASE_URL=postgres://<usuario>:<password>@localhost:5432/shophub_db
ALLOWED_HOSTS=localhost,127.0.0.1
```

> Si tu equipo usa nombres de variables distintos, ajusta esta lista para que coincida exactamente con `.env.example`.

## 5. Crear la base de datos

```bash
# Desde psql o tu cliente de PostgreSQL preferido
createdb shophub_db
```

## 6. Aplicar migraciones

```bash
python manage.py migrate
```

## 7. Crear superusuario (para acceder al panel de administración)

```bash
python manage.py createsuperuser
```

## 8. Ejecutar el servidor de desarrollo

```bash
python manage.py runserver
```

La aplicación quedará disponible en `http://127.0.0.1:8000/`
El panel de administración en `http://127.0.0.1:8000/admin/`

## 9. Ejecutar pruebas

```bash
python manage.py test
```

## Estructura del proyecto

```
shop-hub/
├── <app_catalogo>/       # Catálogo de productos e inventario
├── <app_ventas>/         # Carrito y checkout
├── <app_soporte>/        # Tickets de soporte postventa
├── shophub/               # Configuración del proyecto Django
├── requirements.txt
├── .env.example
├── manage.py
└── README.md
```

> Ajusta los nombres de las apps anteriores a los reales del proyecto.

## Ramas del repositorio

- `main`: rama estable / entregable del curso.
- `develop`: rama de integración de funcionalidades en desarrollo.

## Documentación adicional

- [Visión del Producto](docs/vision-producto-shophub.md)

## Problema técnico central del MVP

Prevención de asignación concurrente del mismo ticket de soporte a dos agentes distintos, y consistencia entre el estado del pedido y el estado del ticket asociado.
