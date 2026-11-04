# Interfaz web

Plantillas de Django servidas por el mismo proyecto (app `web/`). No usa JavaScript ni build: cada acción es un formulario con token CSRF que llama al **mismo servicio** que la API.

**Solo para computador:** el diseño tiene un ancho mínimo de 1024 px y no tiene versión móvil. En un celular se ve la versión de escritorio reducida.

## Paleta 60 · 30 · 10 — «Confianza total»

| Uso | Color | Dónde |
| --- | --- | --- |
| **60 % · dominante** | `#F8F9FA` blanco grisáceo | fondo de todas las páginas; tarjetas en blanco puro |
| **30 % · base profesional** | `#1A365D` azul marino | barra superior, títulos, encabezados de tabla, botones secundarios, foco |
| **10 % · acento de acción** | `#FF6B6B` coral cálido | **solo** CTAs: «Añadir al carrito», «Continuar al pago», «Pagar», «Enviar PQR», «Radicar PQR», «Tomar», «Enviar respuesta», «Nuevo producto», «Entrar», «Crear cuenta» |

**Por qué el texto de los botones coral es oscuro y no blanco:** el blanco sobre `#FF6B6B` tiene un contraste de 2,8:1 y no cumple WCAG AA. Se usa `#0F213D` (marino oscuro), que da 5,8:1 y mantiene la marca.

Los estados usan tonos suaves que no compiten con el acento:

- Abierto: ámbar.
- En proceso: marino claro.
- Cerrado: gris.
- Confirmado: verde.

Los errores usan un rojo (`#B42318`) distinto del coral, para no confundirlos con un botón de acción.

## Pantallas por rol (HU-01 criterio 3)

| Rol | Ruta | Pantalla | Historia |
| --- | --- | --- | --- |
| Todos | `/` | Catálogo con agotados marcados | HU-02 |
| Todos | `/productos/<id>/` | Detalle y cantidad | HU-02 |
| Todos | `/entrar/`, `/registro/` | Inicio de sesión y registro (siempre como cliente) | HU-01 |
| Cliente | `/carrito/` | Agregar, cambiar cantidad y quitar | HU-04 |
| Cliente | `/carrito/pagar/` | Datos de envío (nombre, dirección, ciudad, teléfono) y pago | HU-04 |
| Cliente | `/pedidos/`, `/pedidos/<id>/` | Mis pedidos y su detalle | HU-04 |
| Cliente | `/pqr/nueva/` | Radicar una petición, queja o reclamo ligada a un pedido | HU-05 |
| Cliente | `/pqr/`, `/pqr/<id>/` | Mis PQR, su estado y las respuestas del agente | HU-06, HU-10 |
| Agente | `/agente/` | Cola sin asignar, ordenable, con botón «Tomar» | HU-07, HU-08 |
| Agente | `/agente/mis-tickets/` | PQR asignadas | HU-08 |
| Agente | `/pqr/<id>/` | Detalle con los productos del pedido; si la tiene asignada: responder y cambiar estado | HU-09, HU-10 |
| Administrador | `/gestion/productos/` | Crear, editar (precio, stock, descripción) y retirar o republicar productos | HU-03 |
| Administrador | `/admin/` | Usuarios, asignación del rol de agente y registro de auditoría | HU-01 |

Si dos agentes pulsan «Tomar» sobre la misma PQR, el segundo vuelve a la cola con el aviso *«No pudiste tomar el ticket: El ticket ya fue asignado»*. Es el problema duro visto desde la interfaz.

## Cómo asignar el rol de agente

En `/admin/` → Usuarios → elegir el usuario → Grupos → agregar **agentes**. No hace falta marcar «Es staff»: el agente no necesita entrar al panel.
