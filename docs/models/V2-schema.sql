
CREATE TABLE cliente (
    id_cliente   SERIAL PRIMARY KEY,
    nombre       VARCHAR(150) NOT NULL,
    correo       VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE carrito (
    id_carrito   SERIAL PRIMARY KEY,
    id_cliente   INT NOT NULL REFERENCES cliente(id_cliente),
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

DROP TABLE cliente CASCADE;
DROP TABLE carrito CASCADE;
DROP TABLE producto CASCADE;
DROP TABLE pedido CASCADE;
DROP TABLE item_carrito CASCADE;
DROP TABLE item_ped CASCADE;




INSERT INTO cliente (nombre, correo) VALUES
('Ana Torres', 'ana.torres@example.com'),
('Luis Gómez', 'luis.gomez@example.com'),
('María Pérez', 'maria.perez@example.com');

INSERT INTO producto (nombre, precio_actual, descripcion, stock_disponible) VALUES
('Teclado mecánico', 150000.00, 'Teclado mecánico switches rojos', 25),
('Mouse inalámbrico', 60000.00, 'Mouse ergonómico 2.4GHz', 40),
('Monitor 24"', 650000.00, 'Monitor Full HD IPS', 10),
('Audífonos gamer', 120000.00, 'Audífonos con micrófono', 15);

INSERT INTO agente (nombre) VALUES
('Carlos Ruiz'),
('Diana Salazar');

-- 2. Dependen de cliente
INSERT INTO carrito (id_cliente, estado) VALUES
(1, 'activo'),
(2, 'activo'),
(3, 'abandonado');

INSERT INTO pedido (id_cliente, fecha, estado) VALUES
(1, CURRENT_DATE, 'pendiente'),
(2, CURRENT_DATE - INTERVAL '2 days', 'enviado'),
(3, CURRENT_DATE - INTERVAL '5 days', 'entregado');

-- 3. Dependen de cliente (y opcionalmente pedido)
INSERT INTO ticket_soporte (id_cliente, id_pedido, descripcion, estado, fecha_creacion) VALUES
(1, 1, 'El producto no ha llegado', 'abierto', CURRENT_DATE),
(2, 2, 'Cambio de dirección de envío', 'en_proceso', CURRENT_DATE - INTERVAL '1 day'),
(3, NULL, 'Consulta sobre garantía', 'cerrado', CURRENT_DATE - INTERVAL '3 days');

-- 4. Dependen de carrito/pedido y producto
INSERT INTO item_carrito (id_carrito, id_producto, cantidad) VALUES
(1, 1, 2),
(1, 2, 1),
(2, 3, 1);

INSERT INTO item_pedido (id_pedido, id_producto, cantidad, precio_pactado) VALUES
(1, 1, 1, 150000.00),
(2, 3, 1, 650000.00),
(2, 4, 2, 120000.00),
(3, 2, 3, 60000.00);

-- 5. Dependen de ticket_soporte y agente
INSERT INTO asignacion (id_ticket, id_agente, fecha_hora, resultado) VALUES
(1, 1, NOW(), 'asignado'),
(2, 2, NOW(), 'asignado'),
(3, 1, NOW() - INTERVAL '3 days', 'resuelto');


