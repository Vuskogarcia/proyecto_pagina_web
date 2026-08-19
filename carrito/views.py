from django.core.exceptions import ValidationError
from django.http import JsonResponse

from catalogo.models import Producto
from .models import Pedido, ItemPedido


def checkout_simulado(request):
    """Esqueleto andante: checkout simple, sin login. Recibe producto_id
    y cantidad como parámetros GET, para poder probarlo fácil desde el navegador."""
    producto_id = request.GET.get("producto_id")
    cantidad = int(request.GET.get("cantidad", 1))

    producto = Producto.objects.get(pk=producto_id)
    pedido = Pedido.objects.create()
    ItemPedido.objects.create(pedido=pedido, producto=producto, cantidad=cantidad)

    try:
        pedido.confirmar()
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse(
        {"pedido_id": pedido.pk, "estado": pedido.estado, "total": str(pedido.total())}
    )
