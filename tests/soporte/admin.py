from django.contrib import admin

from .models import RegistroAsignacion, RespuestaTicket, TicketSoporte


@admin.register(TicketSoporte)
class TicketSoporteAdmin(admin.ModelAdmin):
    list_display = ("numero", "tipo", "cliente", "pedido", "estado", "agente", "creado_en")
    list_filter = ("estado", "tipo")


@admin.register(RegistroAsignacion)
class RegistroAsignacionAdmin(admin.ModelAdmin):
    list_display = ("ticket", "agente", "asignado_en")


@admin.register(RespuestaTicket)
class RespuestaTicketAdmin(admin.ModelAdmin):
    list_display = ("ticket", "autor", "creado_en")
    search_fields = ("ticket__id", "autor__username", "mensaje")
