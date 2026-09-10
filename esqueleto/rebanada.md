# Selección de rebanada.
Candidata A — Consultar catálogo

Rebanada vertical:

UI → HTTP → aplicación → dominio → persistencia real (PRODUCTO) → migración

Permite atravesar las cinco fronteras técnicas.
La operación principal es de consulta de PRODUCTO, sin introducir todavía carrito, pedido, ticket o concurrencia.
El modelo de datos ya define PRODUCTO, por lo que no requiere inventar una entidad para hacer la rebanada.
Candidata B — Crear ticket de soporte asociado a pedido

UI → HTTP → aplicación → dominio → persistencia real (TICKET_SOPORTE) → migración

También cruza las cinco fronteras, pero incorpora más reglas: autenticación/autorización del cliente, asociación con un pedido, datos del ticket, identificador, estado y las discrepancias existentes respecto de asunto.

Elección — Candidata A: Consultar catálogo

Fronteras que cruza explícitamente:

HTTP/UI
Aplicación
Dominio
Persistencia real
Migración

Es la mejor primera rebanada porque atraviesa todas las fronteras solicitadas sin introducir el problema duro ni las reglas de carrito/pedido/ticket.

Descartada — 3 líneas:
La creación de ticket cruza la misma cantidad de fronteras, pero introduce más dominio: cliente, pedido, ticket, estado e identificador.
Además, el asunto exigido por las historias no está resuelto en el modelo de datos.
Por eso tiene mayor riesgo de obligarnos a inventar o reconciliar decisiones antes de tener el esqueleto andando.

# Diagrama de secuencia.

```
sequenceDiagram
actor Cliente
    participant Vista as "Vista Django (HTTP/UI + Aplicación)"
    participant ORM as "ORM Django (Dominio / Mapeo)"
    participant DB as "PostgreSQL (Persistencia real)"


    Cliente->>Vista: GET /productos/{id_producto}
    activate Vista

    Vista->>ORM: Producto.objects.get(id_producto=id)
    activate ORM

    Note over ORM,DB: INICIO transacción implícita (autocommit, solo lectura)
    ORM->>DB: SELECT * FROM producto WHERE id_producto = %s
    activate DB

    alt Producto existe
        DB-->>ORM: 1 fila
        Note over ORM: Mapeo dominio↔persistencia: fila SQL → instancia Producto
        Note over ORM,DB: FIN transacción (commit implícito)
    else Producto no existe
        DB-->>ORM: 0 filas
        Note over ORM,DB: FIN transacción (commit implícito, sin resultado)
    end

    ORM-->>Vista: instancia Producto
    Vista-->>Cliente: 200 OK + detalle del producto
    deactivate DB
    deactivate ORM
    deactivate Vista
´´´´

# Diagrama de clases.


```
classDiagram
    class ProductoDetailView {
        <<Vista - HTTP/UI + Aplicación>>
        +get(request, id_producto)
HttpResponse
    }

    class Producto {
        <<Modelo - Dominio + Persistencia>>
        +id_producto : int
        +nombre : str
        +precio_actual : decimal
        +descripcion : str
        +stock_disponible : int
        +objects.get(id_producto)
Producto
    }

    class DoesNotExist {
        <<Excepción - Dominio>>
    }

    ProductoDetailView ..> Producto : consulta
    Producto ..> DoesNotExist : lanza si no existe
´´´
