from django.urls import path
from . import views

urlpatterns = [
    path("tickets/<int:ticket_id>/tomar/", views.tomar_ticket, name="tomar_ticket"),
]
