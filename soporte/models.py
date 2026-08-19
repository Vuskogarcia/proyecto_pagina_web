from django.conf import settings
from django.db import models, transaction


class TicketSoporte(models.Model):
    """Ticket de soporte. El campo 'agente' y 'estado' son el punto
    de concurrencia: dos agentes no deben poder tomar el mismo ticket."""

    ESTADOS = [
        ("sin_asignar", "Sin asignar"),
        ("asignado", "Asignado"),
        ("cerrado", "Cerrado"),
    ]

    asunto = models.CharField(max_length=200)
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default="sin_asignar")
    agente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_asignados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket #{self.pk}: {self.asunto}"

    @transaction.atomic
    def tomar(self, agente):
        """Bloqueo pesimista: bloquea la fila del ticket hasta confirmar
        la asignación, evitando que dos agentes lo tomen a la vez."""
        ticket = TicketSoporte.objects.select_for_update().get(pk=self.pk)
        if ticket.estado != "sin_asignar":
            raise ValueError("El ticket ya fue asignado")

        ticket.estado = "asignado"
        ticket.agente = agente
        ticket.save()

        RegistroAsignacion.objects.create(ticket=ticket, agente=agente)
        return ticket


class RegistroAsignacion(models.Model):
    """Log de auditoría: cada asignación exitosa queda registrada."""

    ticket = models.ForeignKey(
        TicketSoporte, on_delete=models.CASCADE, related_name="registros"
    )
    agente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    asignado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket #{self.ticket_id} → {self.agente} ({self.asignado_en})"
