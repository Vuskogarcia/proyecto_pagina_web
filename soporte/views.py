from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from .models import TicketSoporte


@login_required
def tomar_ticket(request, ticket_id):
    """Un agente intenta tomar un ticket. Si otro agente ya lo tomó,
    devuelve un error claro en vez de sobrescribir la asignación."""
    ticket = TicketSoporte.objects.get(pk=ticket_id)

    try:
        ticket.tomar(agente=request.user)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=409)

    return JsonResponse(
        {"ticket_id": ticket.pk, "estado": ticket.estado, "agente": ticket.agente.username}
    )
