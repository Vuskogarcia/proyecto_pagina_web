from django.conf import settings
from django.db import models


class TicketSoporte(models.Model):
    """Entidad: ticket de soporte postventa, opcionalmente asociado a un pedido.

    Los campos 'agente' y 'estado' son el punto de concurrencia: dos agentes
    no deben poder tomar el mismo ticket (ver docs/problema-duro.md)."""

    ABIERTO = "ABIERTO"
    EN_PROCESO = "EN_PROCESO"
    CERRADO = "CERRADO"
    ESTADOS = [
        (ABIERTO, "Abierto"),
        (EN_PROCESO, "En proceso"),
        (CERRADO, "Cerrado"),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tickets"
    )
    pedido = models.ForeignKey(
        "carrito.Pedido",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    asunto = models.CharField(max_length=200, blank=True)
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ABIERTO)
    agente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_asignados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado_en"]

    def __str__(self):
        return f"{self.numero}: {self.asunto or self.descripcion[:40]}"

    @property
    def numero(self):
        """Número visible del ticket, formato TCK-00001 (HU-05, criterio 3)."""
        return f"TCK-{self.pk:05d}"


class RegistroAsignacion(models.Model):
    """Log de auditoría: cada asignación exitosa queda registrada (HU-08, criterio 4)."""

    ticket = models.ForeignKey(
        TicketSoporte, on_delete=models.CASCADE, related_name="registros"
    )
    agente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    asignado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ticket.numero} → {self.agente} ({self.asignado_en})"
