from django.urls import path

from . import views

urlpatterns = [
    path("productos/", views.listar_productos, name="listar_productos"),
    path("productos/<id:producto_id>/", views.ver_producto, name="ver_producto"),
    path("gestion/productos/", views.gestion_productos, name="gestion_productos"),
]
