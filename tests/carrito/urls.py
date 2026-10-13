from django.urls import path

from . import views

urlpatterns = [
    path("pedidos/", views.checkout, name="checkout"),
    path("pedidos/<int:pedido_id>/", views.ver_pedido, name="ver_pedido"),
]
