from decimal import Decimal

from django.conf import settings
from django.db import models

from catalogo.models import Producto


class Pedido(models.Model):
    """Entidad: el pedido que resulta del checkout."""

    PENDIENTE = "PENDIENTE"
    CONFIRMADO = "CONFIRMADO"
    CANCELADO = "CANCELADO"
    ESTADOS = [
        (PENDIENTE, "Pendiente"),
        (CONFIRMADO, "Confirmado"),
        (CANCELADO, "Cancelado"),
    ]

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos"
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default=PENDIENTE)
    creado_en = models.DateTimeField(auto_now_add=True)
    # Datos de envío (HU-04 criterio 3). Son datos personales: solo los ven
    # el dueño del pedido y los agentes (ver pedido_visible_para).
    envio_nombre = models.CharField("destinatario", max_length=150, blank=True)
    envio_direccion = models.CharField("dirección", max_length=200, blank=True)
    envio_ciudad = models.CharField("ciudad", max_length=100, blank=True)
    envio_telefono = models.CharField("teléfono", max_length=20, blank=True)

    class Meta:
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.codigo} ({self.estado})"

    @property
    def codigo(self):
        """Identificador visible del pedido, formato PED-00001 (HU-04, criterio 4)."""
        return f"PED-{self.pk:05d}"

    def total(self):
        return sum((item.subtotal() for item in self.items.all()), start=Decimal("0"))


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    # Precio al momento de la compra: si el producto cambia de precio,
    # el pedido conserva lo que el cliente pagó.
    precio_pactado = models.DecimalField(max_digits=12, decimal_places=2)

    def subtotal(self):
        return self.precio_pactado * self.cantidad
