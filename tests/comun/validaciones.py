"""Validaciones de datos de entrada, independientes de HTTP.

Los servicios las usan para validar lo que reciben. Viven aparte de
`comun/http.py` para que la capa de negocio no dependa de la capa web
(antes `entero` estaba en http.py; ver docs/revision-codigo.md, RC-04).
"""

from .excepciones import DatosInvalidos


def entero(valor, campo, obligatorio=True):
    """Convierte `valor` a entero positivo o lanza DatosInvalidos."""
    if valor is None:
        if obligatorio:
            raise DatosInvalidos(f"El campo '{campo}' es obligatorio")
        return None
    if isinstance(valor, bool):
        raise DatosInvalidos(f"El campo '{campo}' debe ser un número entero")
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise DatosInvalidos(f"El campo '{campo}' debe ser un número entero")
    if numero < 1:
        raise DatosInvalidos(f"El campo '{campo}' debe ser mayor que 0")
    return numero
