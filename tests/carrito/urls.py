from django.urls import path

from . import views

urlpatterns = [
    path("pedidos/", views.pedidos, name="pedidos"),
    path("pedidos/<id:pedido_id>/", views.ver_pedido, name="ver_pedido"),
]
