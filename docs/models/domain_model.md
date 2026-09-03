```mermaid
erDiagram
    CLIENTE {
        int id_cliente PK
        string nombre
        string correo
    }
    CARRITO {
        int id_carrito PK
        int id_cliente FK
        string estado
    }
    PRODUCTO {
        int id_producto PK
        string nombre
        decimal precio_actual
        string descripcion
        int stock_disponible
    }
    PEDIDO {
        int id_pedido PK
        int id_cliente FK
        date fecha
        string estado
    }
    ITEM_CARRITO {
        int id_carrito FK
        int id_producto FK
        int cantidad
    }
    ITEM_PEDIDO {
        int id_pedido FK
        int id_producto FK
        int cantidad
        decimal precio_pactado
    }
    TICKET_SOPORTE {
        int id_ticket PK
        int id_cliente FK
        int id_pedido FK
        string descripcion
        string estado
        date fecha_creacion
    }
    AGENTE {
        int id_agente PK
        string nombre
    }
    ASIGNACION {
        int id_asignacion PK
        int id_ticket FK
        int id_agente FK
        datetime fecha_hora
        string resultado
    }

    CLIENTE ||--|| CARRITO : tiene
    CLIENTE ||--o{ PEDIDO : realiza
    CLIENTE ||--o{ TICKET_SOPORTE : crea
    CARRITO ||--o{ ITEM_CARRITO : contiene
    PRODUCTO ||--o{ ITEM_CARRITO : aparece_en
    PEDIDO ||--o{ ITEM_PEDIDO : contiene
    PRODUCTO ||--o{ ITEM_PEDIDO : aparece_en
    PEDIDO ||--o| TICKET_SOPORTE : origina
    TICKET_SOPORTE ||--o{ ASIGNACION : tiene
    AGENTE ||--o{ ASIGNACION : realiza
´´´´
