"""Rutas del proyecto.

- /api/...  API JSON (catálogo, pedidos, soporte, sesión).
- /admin/   panel de administración de Django (solo superusuarios).
- /         interfaz web (app `web`).
"""

from django.contrib import admin
from django.urls import include, path, register_converter

from comun.convertidores import IdConverter

register_converter(IdConverter, "id")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("cuentas.urls")),
    path("api/", include("catalogo.urls")),
    path("api/", include("carrito.urls")),
    path("api/", include("soporte.urls")),
    path("", include("web.urls")),
]
