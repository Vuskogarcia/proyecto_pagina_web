from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError

from catalogo.models import Producto


class Pedido(models.Model):
    """Representa un carrito que luego se convierte en checkout simulado."""

    ESTADOS = [
        ("abierto", "Abierto"),
        ("confirmado", "Confirmado"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pedidos"
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default="abierto")
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pedido #{self.pk} ({self.estado})"

    def total(self):
        return sum(item.subtotal() for item in self.items.all())

    @transaction.atomic
    def confirmar(self):
        """Checkout simulado: descuenta stock de forma atómica. select_for_update
        evita que dos checkouts concurrentes dejen el stock en negativo."""
        if self.estado == "confirmado":
            return

        for item in self.items.select_related("producto"):
            producto = Producto.objects.select_for_update().get(pk=item.producto_id)
            if not producto.hay_disponible(item.cantidad):
                raise ValidationError(
                    f"Stock insuficiente para {producto.nombre}"
                )
            producto.stock -= item.cantidad
            producto.save()

        self.estado = "confirmado"
        self.save()


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)

    def subtotal(self):
        return self.producto.precio * self.cantidad
