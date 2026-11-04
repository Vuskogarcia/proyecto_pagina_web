from django.conf import settings
from django.db import models


class EventoAuditoria(models.Model):
    """Registro de eventos críticos de seguridad y negocio (guía §4: auditoría).

    Se guarda en la base de datos (no solo en la consola) para poder
    consultarlo después en /admin/. Nunca guarda contraseñas ni tokens.
    """

    LOGIN_OK = "LOGIN_OK"
    LOGIN_FALLIDO = "LOGIN_FALLIDO"
    LOGIN_BLOQUEADO = "LOGIN_BLOQUEADO"
    LOGOUT = "LOGOUT"
    REGISTRO = "REGISTRO"
    ACCESO_DENEGADO = "ACCESO_DENEGADO"
    CSRF_RECHAZADO = "CSRF_RECHAZADO"
    LIMITE_EXCEDIDO = "LIMITE_EXCEDIDO"
    ERROR_INTERNO = "ERROR_INTERNO"
    PEDIDO_CREADO = "PEDIDO_CREADO"
    TICKET_CREADO = "TICKET_CREADO"
    TICKET_TOMADO = "TICKET_TOMADO"
    TICKET_CONFLICTO = "TICKET_CONFLICTO"
    TIPOS = [
        (LOGIN_OK, "Inicio de sesión"),
        (LOGIN_FALLIDO, "Inicio de sesión fallido"),
        (LOGIN_BLOQUEADO, "Inicio de sesión bloqueado"),
        (LOGOUT, "Cierre de sesión"),
        (REGISTRO, "Registro de cuenta"),
        (ACCESO_DENEGADO, "Acceso denegado (401/403)"),
        (CSRF_RECHAZADO, "CSRF rechazado"),
        (LIMITE_EXCEDIDO, "Límite de peticiones excedido"),
        (ERROR_INTERNO, "Error interno (500)"),
        (PEDIDO_CREADO, "Pedido creado"),
        (TICKET_CREADO, "Ticket creado"),
        (TICKET_TOMADO, "Ticket tomado"),
        (TICKET_CONFLICTO, "Ticket ya asignado (409)"),
    ]

    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    tipo = models.CharField(max_length=20, choices=TIPOS, db_index=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    usuario_intentado = models.CharField(max_length=150, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    ruta = models.CharField(max_length=200, blank=True)
    detalle = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "evento de auditoría"
        verbose_name_plural = "eventos de auditoría"

    def __str__(self):
        return f"{self.fecha:%Y-%m-%d %H:%M:%S} {self.tipo} {self.usuario or self.usuario_intentado or '-'}"
