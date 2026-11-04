"""Roles de usuario (HU-01).

- cliente: cualquier usuario registrado (rol por defecto).
- agente: miembro del grupo "agentes"; lo asigna un administrador en /admin/.
- administrador: superusuario de Django.

El rol de agente ya no depende de `is_staff` (H14): ser agente no da acceso
al panel de administración.
"""

GRUPO_AGENTES = "agentes"

CLIENTE = "cliente"
AGENTE = "agente"
ADMINISTRADOR = "administrador"


def es_agente(usuario):
    if not getattr(usuario, "is_authenticated", False):
        return False
    # Se memoriza en el objeto para no repetir la consulta en la misma petición.
    if not hasattr(usuario, "_es_agente"):
        usuario._es_agente = usuario.groups.filter(name=GRUPO_AGENTES).exists()
    return usuario._es_agente


def es_administrador(usuario):
    """Administrador = superusuario de Django (HU-01 criterio 2, HU-03)."""
    return bool(getattr(usuario, "is_authenticated", False) and usuario.is_superuser)


def rol(usuario):
    if getattr(usuario, "is_superuser", False):
        return ADMINISTRADOR
    if es_agente(usuario):
        return AGENTE
    return CLIENTE
