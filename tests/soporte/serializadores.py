"""Convierte las entidades de soporte en diccionarios listos para JSON.

Separado de servicios.py para que el servicio solo tenga reglas de negocio
(responsabilidad única; ver docs/revision-codigo.md, RC-03).
"""


def respuesta_a_dict(respuesta):
    return {
        "id": respuesta.pk,
        "autor": respuesta.autor.get_full_name() or respuesta.autor.username,
        "mensaje": respuesta.mensaje,
        "fecha": respuesta.creado_en.isoformat(),
    }


def a_dict(ticket, con_respuestas=False):
    datos = {
        "id": ticket.pk,
        "numero": ticket.numero,
        "id_cliente": ticket.cliente_id,
        "cliente": ticket.cliente.username,
        "id_pedido": ticket.pedido_id,
        "pedido": ticket.pedido.codigo if ticket.pedido else None,
        "tipo": ticket.tipo,
        "asunto": ticket.asunto,
        "descripcion": ticket.descripcion,
        "estado": ticket.estado,
        "agente": ticket.agente.username if ticket.agente else None,
        "fecha": ticket.creado_en.isoformat(),
    }
    if con_respuestas:
        datos["respuestas"] = [
            respuesta_a_dict(r) for r in ticket.respuestas.select_related("autor")
        ]
    return datos
