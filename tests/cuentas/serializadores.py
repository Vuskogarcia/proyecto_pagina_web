from comun.roles import rol


def a_dict(usuario):
    return {
        "id": usuario.pk,
        "usuario": usuario.username,
        "nombre": usuario.get_full_name() or usuario.username,
        "rol": rol(usuario),
    }
