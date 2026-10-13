from django.urls import path

from . import views

urlpatterns = [
    path("tickets/", views.crear_ticket, name="crear_ticket"),
    path("tickets/cola/", views.cola_sin_asignar, name="cola_sin_asignar"),
    path("tickets/<int:ticket_id>/", views.ver_ticket, name="ver_ticket"),
    path("tickets/<int:ticket_id>/tomar/", views.tomar_ticket, name="tomar_ticket"),
]
