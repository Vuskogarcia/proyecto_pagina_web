Problema Duro Declarado

1. Contexto: el problema de negocio

Las tiendas virtuales pequeñas y medianas no cuentan con un proceso organizado y trazable para gestionar el soporte postventa.

Cuando un cliente tiene una duda, reclamo o problema con un pedido, la solicitud suele gestionarse mediante canales dispersos como correos electrónicos, mensajes o hojas de cálculo. Esto dificulta relacionar la solicitud con el pedido correspondiente, conocer el estado de atención y hacer seguimiento hasta su resolución.

Como consecuencia, los clientes pueden no recibir una respuesta oportuna y los agentes de servicio tienen dificultades para consultar la información necesaria para resolver cada caso.

El problema central que abordará el proyecto es la falta de trazabilidad y organización en el soporte postventa, mientras que la tienda virtual proporciona la información de pedidos necesaria para conectar cada solicitud con la compra que la originó.

2. Problema duro elegido: Concurrencia sobre asignación de tickets

Concurrencia sobre asignación de tickets: dos o más agentes de servicio al cliente intentando tomar (asignarse) el mismo ticket de la cola de soporte al mismo tiempo.

2.1 Descripción técnica del problema

Cuando varios agentes trabajan simultáneamente sobre la misma cola de tickets, existe una condición de carrera (race condition) al momento de asignación: si dos agentes hacen click en "Tomar ticket" sobre el mismo ticket en una ventana de tiempo muy cercana, ambas solicitudes pueden leer el estado del ticket como "sin asignar" antes de que cualquiera de las dos escrituras se confirme. Sin un mecanismo de control, el sistema podría:
Asignar el mismo ticket a dos agentes distintos.
Sobrescribir la asignación de un agente con la del otro sin que ninguno lo note.
Generar inconsistencia entre lo que el agente ve en su bandeja y el estado real del ticket en base de datos.
2.2 Por qué se eligió este escenario y no la concurrencia sobre stock

El soporte postventa es el problema de negocio central del proyecto (ver vision-producto.md, revisión del 19 ago 2026), por lo que resolver su punto más crítico de concurrencia refuerza el enfoque del producto.
A diferencia del stock (donde suele bastar una validación atómica al confirmar el pedido), la asignación de tickets involucra una interacción humana en tiempo real entre varios agentes, lo que hace el problema más visible y más fácil de demostrar en una demo en vivo.

2.3 Mecanismo de control propuesto
Mecanismo	Cómo funcionaría aplicado a este caso
Bloqueo optimista (optimistic locking)	Cada ticket tiene un campo de versión; al asignar, se valida que la versión no haya cambiado desde que el agente la leyó. Si cambió, la asignación se rechaza y se le informa al agente.
Bloqueo pesimista (pesimistic locking)	Al intentar tomar un ticket, se bloquea la fila en la base de datos hasta que la transacción de asignación termina, impidiendo que otro agente lea/escriba sobre el mismo registro mientras tanto.
Transacción con nivel de aislamiento específico	Usar SELECT ... FOR UPDATE o el nivel de aislamiento SERIALIZABLE de PostgreSQL para que la operación de "tomar ticket" sea atómica de extremo a extremo.

3. Evidencia específica que se exigirá al final

Prueba automatizada de concurrencia: un test que simule dos (o más) agentes intentando tomar el mismo ticket al mismo tiempo (ej. usando hilos/procesos concurrentes o llamadas simultáneas al endpoint de asignación) y verifique que solo uno de los dos obtiene el ticket, mientras el otro recibe un error o mensaje claro de "ticket ya asignado".
Evidencia de que no hay condición de carrera silenciosa: el test debe demostrar que no existe ningún escenario donde ambos agentes crean tener el ticket asignado sin que el sistema lo detecte.
Registro/log de la asignación: cada asignación exitosa debe quedar registrada (agente, ticket, timestamp) para poder auditar el resultado del test.

