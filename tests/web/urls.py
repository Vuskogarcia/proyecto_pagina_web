from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("productos/<id:producto_id>/", views.producto, name="producto"),
    # Cuentas (HU-01)
    path("entrar/", views.entrar, name="entrar"),
    path("salir/", views.salir, name="salir"),
    path("registro/", views.registro, name="registro"),
    # Carrito y pedidos (HU-04)
    path("carrito/", views.carrito, name="carrito"),
    path("carrito/agregar/", views.carrito_agregar, name="carrito_agregar"),
    path("carrito/actualizar/", views.carrito_actualizar, name="carrito_actualizar"),
    path("carrito/quitar/", views.carrito_quitar, name="carrito_quitar"),
    path("carrito/pagar/", views.carrito_pagar, name="carrito_pagar"),
    path("pedidos/", views.mis_pedidos, name="pedidos"),
    path("pedidos/<id:pedido_id>/", views.pedido, name="pedido"),
    # PQR (HU-05, HU-06)
    path("pqr/", views.mis_pqr, name="pqr_lista"),
    path("pqr/nueva/", views.nueva_pqr, name="pqr_nueva"),
    path("pqr/<id:ticket_id>/", views.pqr, name="pqr"),
    # Panel del agente (HU-07, HU-08)
    path("agente/", views.cola, name="cola"),
    path("agente/tickets/<id:ticket_id>/tomar/", views.tomar, name="tomar"),
    path("agente/mis-tickets/", views.mis_asignados, name="asignados"),
]
