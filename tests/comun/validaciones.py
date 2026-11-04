"""Validaciones de datos de entrada, independientes de HTTP.

Los servicios las usan para validar lo que reciben. Viven aparte de
`comun/http.py` para que la capa de negocio no dependa de la capa web
(antes `entero` estaba en http.py; ver docs/revision-codigo.md, RC-04).

ADL-04: validación por lista de permitidos (solo `int` o texto de dígitos
ASCII) y con cota superior. ADL-05: texto sin NUL ni surrogates sueltos.
"""

import re

from .excepciones import DatosInvalidos

# Mayor valor de un IntegerField en PostgreSQL; los ids de la aplicación
# están muy por debajo. Se usa como cota por defecto.
MAX_ENTERO = 2_147_483_647

_SOLO_DIGITOS = re.compile(r"-?[0-9]{1,19}")  # ASCII, sin espacios ni signos raros


def entero(valor, campo, obligatorio=True, maximo=MAX_ENTERO):
    """Convierte `valor` a entero en [1, maximo] o lanza DatosInvalidos.

    Lista de permitidos: un `int` (no bool) o un texto de dígitos ASCII.
    Se rechazan floats (1.9 se truncaba a 1), dígitos no ASCII ("١"),
    espacios y valores enormes.
    """
    if valor is None:
        if obligatorio:
            raise DatosInvalidos(f"El campo '{campo}' es obligatorio")
        return None
    if isinstance(valor, bool):
        raise DatosInvalidos(f"El campo '{campo}' debe ser un número entero")
    if isinstance(valor, int):
        numero = valor
    elif isinstance(valor, str) and _SOLO_DIGITOS.fullmatch(valor):
        numero = int(valor)
    else:
        raise DatosInvalidos(f"El campo '{campo}' debe ser un número entero")
    if numero < 1:
        raise DatosInvalidos(f"El campo '{campo}' debe ser mayor que 0")
    if numero > maximo:
        raise DatosInvalidos(f"El campo '{campo}' no puede ser mayor que {maximo}")
    return numero


def texto_seguro(valor, campo="texto"):
    """Lanza DatosInvalidos si el texto trae NUL o surrogates sueltos.

    PostgreSQL rechaza ambos en columnas de texto y, sin esta validación,
    el error llegaba a la base de datos y salía como 500 (H7, H8).
    """
    if "\x00" in valor:
        raise DatosInvalidos(f"El campo '{campo}' contiene caracteres no permitidos")
    try:
        valor.encode("utf-8")
    except UnicodeEncodeError:
        raise DatosInvalidos(f"El campo '{campo}' contiene caracteres no permitidos")
    return valor


def texto(valor, campo, obligatorio=True, maximo=None):
    """Texto recortado, validado con `texto_seguro` y con largo máximo."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obligatorio:
            raise DatosInvalidos(f"El campo '{campo}' es obligatorio")
        return ""
    if not isinstance(valor, str):
        raise DatosInvalidos(f"El campo '{campo}' debe ser texto")
    valor = texto_seguro(valor.strip(), campo)
    if maximo is not None and len(valor) > maximo:
        raise DatosInvalidos(f"El campo '{campo}' admite máximo {maximo} caracteres")
    return valor
