"""Los tipos de error del sistema.

Cada excepción lleva el código HTTP que le corresponde. Los servicios las
lanzan cuando una regla de negocio no se cumple, y el decorador `api`
(comun/http.py) las convierte en una respuesta JSON con ese código.
"""


class ErrorDeNegocio(Exception):
    """Base de los errores esperados del sistema."""

    status = 500


class NoEncontrado(ErrorDeNegocio):
    """El id solicitado no existe."""

    status = 404


class EstadoInvalido(ErrorDeNegocio):
    """La operación no cabe en el estado actual (ej. ticket ya asignado)."""

    status = 409


class DatosInvalidos(ErrorDeNegocio):
    """Lo que llegó en la petición está mal formado o incompleto."""

    status = 400


class SinPermiso(ErrorDeNegocio):
    """El usuario existe pero su rol no le permite la operación (ej. un cliente
    intentando tomar un ticket, que es tarea de un agente)."""

    status = 403


class NoAutenticado(ErrorDeNegocio):
    """La operación requiere iniciar sesión (HU-01, ADL-01)."""

    status = 401


class DemasiadosIntentos(ErrorDeNegocio):
    """Se superó el límite de intentos de inicio de sesión."""

    status = 429
