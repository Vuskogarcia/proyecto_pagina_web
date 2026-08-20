from django.urls import path
from . import views

urlpatterns = [
    path("checkout/", views.checkout_simulado, name="checkout_simulado"),
]
