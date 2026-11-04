"""Interfaz web de SHOP-HUB (plantillas Django).

Las vistas solo coordinan: leen el formulario, llaman al MISMO servicio que
usa la API y muestran el resultado. Así las reglas de negocio y las
correcciones de seguridad aplican igual en la web y en la API.

- La identidad sale siempre de la sesión (ADL-01).
- Los formularios POST llevan token CSRF ({% csrf_token %}).
- Un recurso ajeno se muestra como inexistente (404, ADL-03).
"""

import logging
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from carrito import carrito_sesion
from carrito import servicios as pedidos
from catalogo import servicios as catalogo
from comun.excepciones import DemasiadosIntentos, ErrorDeNegocio, EstadoInvalido, NoEncontrado
from comun.limites import limite_escritura, limite_registro
from comun.roles import es_administrador, es_agente
from cuentas import auditoria
from cuentas import servicios as cuentas
from cuentas.models import EventoAuditoria
from soporte import servicios as soporte

from .formularios import EntrarForm, EnvioForm, PqrForm, ProductoForm, RegistroForm

logger = logging.getLogger("shophub")


# --- Control de acceso (HU-01, criterios 3 y 4) ---------------------------

def _solo(condicion):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not condicion(request.user):
                logger.warning("Web: acceso denegado a %s usuario=%s", request.path, request.user.pk)
                auditoria.registrar(EventoAuditoria.ACCESO_DENEGADO, request, detalle="403 web")
                return render(request, "403.html", status=403)
            if request.method == "POST":
                try:
                    limite_escritura(request)
                except DemasiadosIntentos as error:
                    auditoria.registrar(EventoAuditoria.LIMITE_EXCEDIDO, request, detalle="web")
                    return render(request, "429.html", {"mensaje": str(error)}, status=429)
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador


solo_clientes = _solo(lambda u: not es_agente(u))
solo_agentes = _solo(es_agente)
solo_administradores = _solo(es_administrador)
autenticado = _solo(lambda u: True)


def _destino_seguro(request, por_defecto):
    """Evita redirecciones abiertas: `next` solo puede apuntar a este sitio."""
    destino = request.POST.get("next") or request.GET.get("next")
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return destino
    return por_defecto


def _obtener_o_404(funcion, *args):
    try:
        return funcion(*args)
    except NoEncontrado:
        raise Http404


# --- Catálogo (HU-02) ------------------------------------------------------

@require_GET
def inicio(request):
    if request.user.is_authenticated and es_agente(request.user):
        return redirect("web:cola")
    return render(request, "web/catalogo.html", {"productos": catalogo.listar_catalogo()})


@require_GET
def producto(request, producto_id):
    item = _obtener_o_404(catalogo.detalle_producto, producto_id)
    return render(request, "web/producto.html", {"producto": item})


# --- Cuentas (HU-01) -------------------------------------------------------

@require_http_methods(["GET", "POST"])
def entrar(request):
    if request.user.is_authenticated:
        return redirect("web:inicio")
    formulario = EntrarForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            cuenta = cuentas.autenticar(
                request,
                formulario.cleaned_data["usuario"],
                formulario.cleaned_data["clave"],
                ip=cuentas.ip_de(request),
            )
        except ErrorDeNegocio as error:
            formulario.add_error(None, str(error))
        else:
            login(request, cuenta)
            messages.success(request, f"Hola, {cuenta.get_full_name() or cuenta.username}.")
            por_defecto = "web:cola" if es_agente(cuenta) else "web:inicio"
            return redirect(_destino_seguro(request, por_defecto))
    return render(request, "web/entrar.html", {"form": formulario, "next": request.GET.get("next", "")})


@require_POST
def salir(request):
    if request.user.is_authenticated:
        auditoria.registrar(EventoAuditoria.LOGOUT, request)
    logout(request)
    messages.info(request, "Cerraste sesión.")
    return redirect("web:inicio")


@require_http_methods(["GET", "POST"])
def registro(request):
    if request.user.is_authenticated:
        return redirect("web:inicio")
    formulario = RegistroForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            limite_registro(request)
            cuenta = cuentas.registrar_cliente(datos["email"], datos["clave"], datos["nombre"])
        except ErrorDeNegocio as error:
            formulario.add_error(None, str(error))
        else:
            login(request, cuenta, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Tu cuenta quedó creada. ¡Bienvenido a SHOP-HUB!")
            return redirect("web:inicio")
    return render(request, "web/registro.html", {"form": formulario})


# --- Carrito y checkout (HU-04) -------------------------------------------

@solo_clientes
@require_GET
def carrito(request):
    return render(request, "web/carrito.html", carrito_sesion.resumen(request.session))


@solo_clientes
@require_POST
def carrito_agregar(request):
    try:
        carrito_sesion.agregar(request.session, request.POST.get("id_producto"),
                               request.POST.get("cantidad", "1"))
    except ErrorDeNegocio as error:
        messages.error(request, str(error))
        return redirect(_destino_seguro(request, "web:inicio"))
    messages.success(request, "Producto añadido al carrito.")
    return redirect(_destino_seguro(request, "web:carrito"))


@solo_clientes
@require_POST
def carrito_actualizar(request):
    try:
        carrito_sesion.cambiar_cantidad(request.session, request.POST.get("id_producto"),
                                        request.POST.get("cantidad"))
    except ErrorDeNegocio as error:
        messages.error(request, str(error))
    return redirect("web:carrito")


@solo_clientes
@require_POST
def carrito_quitar(request):
    try:
        carrito_sesion.quitar(request.session, request.POST.get("id_producto"))
    except ErrorDeNegocio as error:
        messages.error(request, str(error))
    else:
        messages.info(request, "Producto quitado del carrito.")
    return redirect("web:carrito")


@solo_clientes
@require_http_methods(["GET", "POST"])
def carrito_pagar(request):
    """HU-04 criterio 3: antes de pagar, el cliente ingresa los datos de envío."""
    resumen = carrito_sesion.resumen(request.session)
    if not resumen["lineas"]:
        messages.info(request, "Tu carrito está vacío.")
        return redirect("web:carrito")
    inicial = {"nombre": request.user.get_full_name()}
    formulario = EnvioForm(request.POST or None, initial=inicial)
    if request.method == "POST" and formulario.is_valid():
        try:
            pedido = carrito_sesion.pagar(request.session, request.user, formulario.cleaned_data)
        except ErrorDeNegocio as error:
            formulario.add_error(None, f"No se pudo completar el pago: {error}")
        else:
            messages.success(request, f"¡Listo! Tu pedido {pedido.codigo} quedó confirmado.")
            return redirect("web:pedido", pedido_id=pedido.pk)
    return render(request, "web/pagar.html", {"form": formulario, **resumen})


@solo_clientes
@require_GET
def mis_pedidos(request):
    return render(request, "web/pedidos.html", {"pedidos": pedidos.pedidos_de(request.user)})


@autenticado
@require_GET
def pedido(request, pedido_id):
    item = _obtener_o_404(pedidos.pedido_visible_para, pedido_id, request.user)
    return render(request, "web/pedido.html", {"pedido": item})


# --- PQR del cliente (HU-05, HU-06) ---------------------------------------

@solo_clientes
@require_GET
def mis_pqr(request):
    return render(request, "web/pqr_lista.html", {"tickets": soporte.tickets_de(request.user)})


@solo_clientes
@require_http_methods(["GET", "POST"])
def nueva_pqr(request):
    mis = list(pedidos.pedidos_de(request.user))
    inicial = {"tipo": "PETICION", "pedido": request.GET.get("pedido") or ""}
    formulario = PqrForm(request.POST or None, initial=inicial, pedidos=mis)
    if request.method == "POST" and formulario.is_valid():
        datos = formulario.cleaned_data
        try:
            ticket = soporte.crear_ticket(
                request.user.pk, datos["descripcion"], pedido_id=datos["pedido"],
                asunto=datos["asunto"], tipo=datos["tipo"],
            )
        except ErrorDeNegocio as error:
            formulario.add_error(None, str(error))
        else:
            messages.success(request, f"Radicamos tu solicitud {ticket.numero}. Te responderemos pronto.")
            return redirect("web:pqr", ticket_id=ticket.pk)
    return render(request, "web/pqr_nueva.html", {"form": formulario})


@autenticado
@require_GET
def pqr(request, ticket_id):
    ticket = _obtener_o_404(soporte.ticket_visible_para, ticket_id, request.user)
    asignado_a_mi = ticket.agente_id == request.user.pk
    return render(request, "web/pqr_detalle.html", {
        "ticket": ticket,
        "respuestas": ticket.respuestas.select_related("autor"),
        "asignado_a_mi": asignado_a_mi,
        "estados_siguientes": soporte.estados_siguientes(ticket) if asignado_a_mi else [],
    })


# --- Panel del agente (HU-07, HU-08, HU-09) -------------------------------

@solo_agentes
@require_GET
def cola(request):
    orden = request.GET.get("orden", "antiguos")
    if orden not in soporte.ORDENES_COLA:
        orden = "antiguos"
    return render(request, "web/agente_cola.html",
                  {"tickets": soporte.cola_sin_asignar(orden), "orden": orden})


@solo_agentes
@require_POST
def tomar(request, ticket_id):
    try:
        ticket = soporte.tomar_ticket(ticket_id, request.user.pk)
    except ErrorDeNegocio as error:
        if isinstance(error, EstadoInvalido):
            auditoria.registrar(EventoAuditoria.TICKET_CONFLICTO, request, detalle=f"ticket={ticket_id}")
        # 409: otro agente lo tomó primero (problema duro, HU-08 criterio 2).
        messages.error(request, f"No pudiste tomar el ticket: {error}.")
        return redirect("web:cola")
    messages.success(request, f"Tomaste el ticket {ticket.numero}.")
    return redirect("web:pqr", ticket_id=ticket.pk)


@solo_agentes
@require_POST
def responder(request, ticket_id):
    """HU-10: el agente asignado responde la PQR."""
    try:
        soporte.responder_ticket(ticket_id, request.user.pk, request.POST.get("mensaje"))
    except NoEncontrado:
        raise Http404
    except ErrorDeNegocio as error:
        messages.error(request, f"No se pudo enviar la respuesta: {error}")
    else:
        messages.success(request, "Respuesta enviada. El cliente ya puede verla.")
    return redirect("web:pqr", ticket_id=ticket_id)


@solo_agentes
@require_POST
def cambiar_estado(request, ticket_id):
    """HU-10: el agente asignado cambia el estado (Resuelto, Cerrado, reabrir)."""
    try:
        ticket = soporte.cambiar_estado(ticket_id, request.user.pk, request.POST.get("estado"))
    except NoEncontrado:
        raise Http404
    except ErrorDeNegocio as error:
        messages.error(request, f"No se pudo cambiar el estado: {error}")
    else:
        messages.success(request, f"{ticket.numero} quedó en estado «{ticket.get_estado_display()}».")
    return redirect("web:pqr", ticket_id=ticket_id)


@solo_agentes
@require_GET
def mis_asignados(request):
    return render(request, "web/agente_asignados.html", {"tickets": soporte.asignados_a(request.user)})



# --- Gestión del catálogo (HU-03, solo administradores) -------------------

@solo_administradores
@require_GET
def gestion_productos(request):
    return render(request, "web/gestion_productos.html",
                  {"productos": catalogo.listar_todos(request.user)})


@solo_administradores
@require_http_methods(["GET", "POST"])
def gestion_producto_nuevo(request):
    formulario = ProductoForm(request.POST or None, initial={"activo": True, "stock": 0})
    if request.method == "POST" and formulario.is_valid():
        try:
            producto = catalogo.crear_producto(request.user, formulario.cleaned_data)
        except ErrorDeNegocio as error:
            formulario.add_error(None, str(error))
        else:
            messages.success(request, f"Producto «{producto.nombre}» creado.")
            return redirect("web:gestion_productos")
    return render(request, "web/gestion_producto_form.html", {"form": formulario, "producto": None})


@solo_administradores
@require_http_methods(["GET", "POST"])
def gestion_producto_editar(request, producto_id):
    producto = _obtener_o_404(catalogo.producto_para_editar, request.user, producto_id)
    inicial = {c: getattr(producto, c) for c in catalogo.CAMPOS_EDITABLES}
    formulario = ProductoForm(request.POST or None, initial=inicial)
    if request.method == "POST" and formulario.is_valid():
        cambios = {c: v for c, v in formulario.cleaned_data.items() if v != inicial[c]}
        if not cambios:
            messages.info(request, "No hubo cambios.")
            return redirect("web:gestion_productos")
        try:
            producto = catalogo.actualizar_producto(request.user, producto_id, cambios)
        except NoEncontrado:
            raise Http404
        except ErrorDeNegocio as error:
            formulario.add_error(None, str(error))
        else:
            messages.success(request, f"Producto «{producto.nombre}» actualizado.")
            return redirect("web:gestion_productos")
    return render(request, "web/gestion_producto_form.html", {"form": formulario, "producto": producto})


@solo_administradores
@require_POST
def gestion_producto_activo(request, producto_id):
    """Activa o desactiva un producto (HU-03 criterio 3)."""
    activar = request.POST.get("activo") == "1"
    try:
        producto = catalogo.actualizar_producto(request.user, producto_id, {"activo": activar})
    except NoEncontrado:
        raise Http404
    except ErrorDeNegocio as error:
        messages.error(request, str(error))
    else:
        estado = "visible en el catálogo" if producto.activo else "retirado del catálogo"
        messages.success(request, f"«{producto.nombre}» quedó {estado}.")
    return redirect("web:gestion_productos")
