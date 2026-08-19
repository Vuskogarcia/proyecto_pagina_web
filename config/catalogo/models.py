from django.db import models


class Producto(models.Model):
    """Producto disponible en el catálogo de la tienda."""

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

    def hay_disponible(self, cantidad):
        return self.stock >= cantidad
