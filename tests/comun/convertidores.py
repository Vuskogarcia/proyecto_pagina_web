"""Convertidor de rutas para ids: `<id:pedido_id>`.

Como `<int:...>` pero con cota (ADL-04): un id con más dígitos de los que
caben en la base de datos no llega a la consulta; Django responde 404.
"""

from .validaciones import MAX_ENTERO


class IdConverter:
    regex = "[1-9][0-9]{0,9}"

    def to_python(self, valor):
        numero = int(valor)
        if numero > MAX_ENTERO:
            raise ValueError("id fuera de rango")  # Django lo convierte en 404
        return numero

    def to_url(self, valor):
        return str(int(valor))
