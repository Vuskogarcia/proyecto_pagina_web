```mermaid
---
config:
  layout: elk
---
erDiagram
  CLIENTE ||--o{ PEDIDO : realiza
  CLIENTE ||--o| CARRITO : tiene
  PEDIDO ||--|{ ITEM_PEDIDO : contiene
  PRODUCTO ||--o{ ITEM_PEDIDO : "aparece en"
  CARRITO ||--o{ ITEM_CARRITO : contiene
  PRODUCTO ||--o{ ITEM_CARRITO : "aparece en"
  CLIENTE ||--o{ TICKET_SOPORTE : crea
  PEDIDO |o--o{ TICKET_SOPORTE : "puede originar"
  AGENTE ||--o{ ASIGNACION : realiza
  TICKET_SOPORTE ||--o{ ASIGNACION : tiene

  CLIENTE {
    int id_cliente PK
    string nombre
    string correo
  }
  PRODUCTO {
    int id_producto PK
    string nombre
    decimal precio_actual
    int stock_disponible
  }
  PEDIDO {
    int id_pedido PK
    int id_cliente FK
    date fecha
    string estado
    decimal total
  }
  ITEM_PEDIDO {
    int id_pedido FK
    int id_producto FK
    int cantidad
    decimal precio_pactado
  }
  CARRITO {
    int id_carrito PK
    int id_cliente FK
    string estado
  }
  ITEM_CARRITO {
    int id_carrito FK
    int id_producto FK
    int cantidad
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
    datetime timestamp
    string resultado
  }
´´´
