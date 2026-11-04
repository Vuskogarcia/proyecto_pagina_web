from django.contrib import admin

from .models import EventoAuditoria


@admin.register(EventoAuditoria)
class EventoAuditoriaAdmin(admin.ModelAdmin):
    """Solo lectura: un registro de auditoría no se edita ni se borra a mano."""

    list_display = ("fecha", "tipo", "usuario", "usuario_intentado", "ip", "ruta", "detalle")
    list_filter = ("tipo", "fecha")
    search_fields = ("usuario__username", "usuario_intentado", "ip", "detalle")
    date_hierarchy = "fecha"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
