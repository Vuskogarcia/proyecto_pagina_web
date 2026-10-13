from django.db import models


class Producto(models.Model):
    """Entidad: producto del catálogo de la tienda."""

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    # Permite retirar un producto del catálogo sin borrarlo (y sin romper pedidos viejos).
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def agotado(self):
        return self.stock == 0

    def hay_disponible(self, cantidad):
        return self.stock >= cantidad
