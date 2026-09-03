
CREATE TABLE cliente (
    id_cliente   SERIAL PRIMARY KEY,
    nombre       VARCHAR(150) NOT NULL,
    correo       VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE carrito (
    id_carrito   SERIAL PRIMARY KEY,
    id_cliente   INT  UNIQUE NOT NULL REFERENCES cliente(id_cliente),
    estado       VARCHAR(30) NOT NULL
);

CREATE TABLE producto (
    id_producto      SERIAL PRIMARY KEY,
    nombre           VARCHAR(150) NOT NULL,
    precio_actual    NUMERIC(12,2) NOT NULL CHECK (precio_actual >= 0),
    descripcion      TEXT,
    stock_disponible INT NOT NULL CHECK (stock_disponible >= 0)
);

CREATE TABLE pedido (
    id_pedido    SERIAL PRIMARY KEY,
    id_cliente   INT NOT NULL REFERENCES cliente(id_cliente),
    fecha        DATE NOT NULL DEFAULT CURRENT_DATE,
    estado       VARCHAR(30) NOT NULL
);

CREATE TABLE item_carrito (
    id_carrito   INT NOT NULL REFERENCES carrito(id_carrito),
    id_producto  INT NOT NULL REFERENCES producto(id_producto),
    cantidad     INT NOT NULL CHECK (cantidad > 0),
    PRIMARY KEY (id_carrito, id_producto)
);

CREATE TABLE item_pedido (
    id_pedido       INT NOT NULL REFERENCES pedido(id_pedido),
    id_producto     INT NOT NULL REFERENCES producto(id_producto),
    cantidad        INT NOT NULL CHECK (cantidad > 0),
    precio_pactado  NUMERIC(12,2) NOT NULL CHECK (precio_pactado >= 0),
    PRIMARY KEY (id_pedido, id_producto)
);

CREATE TABLE ticket_soporte (
    id_ticket        SERIAL PRIMARY KEY,
    id_cliente       INT NOT NULL REFERENCES cliente(id_cliente),
    id_pedido        INT REFERENCES pedido(id_pedido),
    descripcion      TEXT NOT NULL,
    estado           VARCHAR(30) NOT NULL,
    fecha_creacion   DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE agente (
    id_agente    SERIAL PRIMARY KEY,
    nombre       VARCHAR(150) NOT NULL
);

CREATE TABLE asignacion (
    id_asignacion  SERIAL PRIMARY KEY,
    id_ticket      INT NOT NULL REFERENCES ticket_soporte(id_ticket),
    id_agente      INT NOT NULL REFERENCES agente(id_agente),
    fecha_hora     TIMESTAMP NOT NULL DEFAULT NOW(),
    resultado      VARCHAR(100)
);

CREATE INDEX idx_carrito_cliente ON carrito(id_cliente);
CREATE INDEX idx_pedido_cliente ON pedido(id_cliente);
CREATE INDEX idx_ticket_cliente ON ticket_soporte(id_cliente);
CREATE INDEX idx_ticket_pedido ON ticket_soporte(id_pedido);
CREATE INDEX idx_asignacion_ticket ON asignacion(id_ticket);
CREATE INDEX idx_asignacion_agente ON asignacion(id_agente);
