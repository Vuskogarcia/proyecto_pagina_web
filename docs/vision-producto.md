Visión del Producto — Sistema "SHOP-HUB" (Tienda Virtual con Soporte Postventa)
1. Declaración del Problema

Las tiendas virtuales pequeñas y medianas carecen de un canal organizado para el soporte postventa: cuando un cliente tiene una duda, un reclamo o un problema con su pedido, no existe un proceso claro para reportarlo, darle seguimiento y resolverlo. Este problema se agrava porque la venta y el soporte suelen estar desconectados entre sí, sin trazabilidad entre lo que el cliente compró y lo que está reclamando.

El sistema debe ofrecer, sobre una base de venta en línea completa (catálogo, carrito, checkout e inventario), un canal de tickets de soporte integrado con la información del pedido.

Revisión (19 ago 2026): el equipo identificó que el soporte postventa es el problema central del proyecto, y la venta en línea es la plataforma que lo sostiene — no al revés. Esta redacción reemplaza la versión original, que presentaba ambos como problemas paralelos.

2. Usuarios y Actores Principales
   
Cliente: Compra productos y puede abrir tickets de soporte relacionados con sus pedidos.

Agente de Servicio al Cliente: Atiende la cola de tickets y responde las solicitudes de los clientes.

Administrador: Gestiona el catálogo de productos y supervisa información general del sistema.

3. Propuesta de Valor (Plantilla de Visión)
   
PARA los clientes, agentes de servicio y administradores de una tienda pequeña o mediana,
QUE NECESITAN resolver el soporte postventa con la misma trazabilidad con la que se gestiona la venta,
EL SISTEMA "SHOP-HUB" es una plataforma web de venta en línea con soporte postventa integrado,
QUE vincula cada ticket de soporte al pedido que lo originó, dando seguimiento completo desde la compra hasta la resolución del reclamo,
A DIFERENCIA DE procesos manuales y dispersos (correos, mensajes, hojas de cálculo) que hoy usan estos negocios para atender reclamos,
NUESTRO PRODUCTO garantiza trazabilidad entre venta y soporte, eliminando la desconexión entre lo que el cliente compró y lo que está reclamando.

4. Alcance del MVP (Límites del Producto)
   
Incluido (Obligatorio):
Catálogo de productos con inventario (alta, edición, consulta de stock).
Carrito de compras y checkout con generación de pedido.
Apertura de tickets de soporte por parte del cliente, vinculados obligatoriamente a un pedido existente.
Cola de tickets para agentes: asignación, cambio de estado (abierto / en proceso / resuelto) y respuesta al cliente.
Problema duro: Prevención de asignación concurrente del mismo ticket a dos agentes distintos, y consistencia entre el estado del pedido y el estado del ticket asociado.
Excluido (Fuera de alcance):
Chat en vivo o mensajería en tiempo real entre cliente y agente.
Reembolsos o gestión de pagos/devoluciones automatizadas.
Múltiples tiendas o multi-tenant (una sola tienda por instancia).
Respuestas automáticas por IA o bots de soporte.
