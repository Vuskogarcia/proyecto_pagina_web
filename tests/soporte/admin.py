from django.contrib import admin

from .models import RegistroAsignacion, TicketSoporte


@admin.register(TicketSoporte)
class TicketSoporteAdmin(admin.ModelAdmin):
    list_display = ("numero", "cliente", "pedido", "estado", "agente", "creado_en")
    list_filter = ("estado",)


@admin.register(RegistroAsignacion)
class RegistroAsignacionAdmin(admin.ModelAdmin):
    list_display = ("ticket", "agente", "asignado_en")
