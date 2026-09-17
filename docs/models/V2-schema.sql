-- ============================================================
-- V3-schema.sql
-- Plataforma de e-commerce + tickets de soporte
-- PostgreSQL
--
-- Cambios respecto a V2:
--   * El bloque DROP va al inicio, con IF EXISTS y orden inverso
--     de dependencias (antes estaba en medio y borraba todo).
--   * Corregido el typo item_ped -> item_pedido.
--   * Estados con CHECK en vez de VARCHAR libre.
--   * Politicas ON DELETE explicitas en todas las FK.
--   * TIMESTAMPTZ donde importa la hora (pedidos, tickets).
--   * producto.activo para poder retirar del catalogo sin borrar.
--   * Indice unico parcial: un solo carrito activo por cliente.
--   * Tablas pago y direccion_envio (checkout). Si no las necesitas
--     todavia, borra la seccion marcada como OPCIONAL.
-- ============================================================
 
-- ------------------------------------------------------------
-- 0. Limpieza (orden inverso de dependencias)
-- ------------------------------------------------------------
DROP TABLE IF EXISTS asignacion CASCADE;
DROP TABLE IF EXISTS ticket_soporte CASCADE;
DROP TABLE IF EXISTS agente CASCADE;
DROP TABLE IF EXISTS pago CASCADE;
DROP TABLE IF EXISTS item_pedido CASCADE;
DROP TABLE IF EXISTS item_carrito CASCADE;
DROP TABLE IF EXISTS pedido CASCADE;
DROP TABLE IF EXISTS carrito CASCADE;
DROP TABLE IF EXISTS direccion_envio CASCADE;
DROP TABLE IF EXISTS producto CASCADE;
DROP TABLE IF EXISTS cliente CASCADE;
 
-- ------------------------------------------------------------
-- 1. Entidades base
-- ------------------------------------------------------------
CREATE TABLE cliente (
    id_cliente   SERIAL PRIMARY KEY,
    nombre       VARCHAR(150) NOT NULL,
    correo       VARCHAR(150) NOT NULL UNIQUE,
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
 
-- Evita que 'Ana@Example.com' y 'ana@example.com' convivan.
CREATE UNIQUE INDEX idx_cliente_correo_lower ON cliente (LOWER(correo));
 
CREATE TABLE producto (
    id_producto      SERIAL PRIMARY KEY,
    nombre           VARCHAR(150) NOT NULL,
    precio_actual    NUMERIC(12,2) NOT NULL CHECK (precio_actual >= 0),
    descripcion      TEXT,
    stock_disponible INT NOT NULL CHECK (stock_disponible >= 0),
    activo           BOOLEAN NOT NULL DEFAULT TRUE
);
 
CREATE TABLE agente (
    id_agente SERIAL PRIMARY KEY,
    nombre    VARCHAR(150) NOT NULL,
    activo    BOOLEAN NOT NULL DEFAULT TRUE
);
 
-- OPCIONAL (checkout): direcciones del cliente
CREATE TABLE direccion_envio (
    id_direccion SERIAL PRIMARY KEY,
    id_cliente   INT NOT NULL REFERENCES cliente(id_cliente) ON DELETE CASCADE,
    linea        VARCHAR(200) NOT NULL,
    ciudad       VARCHAR(100) NOT NULL,
    pais         VARCHAR(100) NOT NULL DEFAULT 'Colombia',
    telefono     VARCHAR(30)
);
 
-- ------------------------------------------------------------
-- 2. Carrito
-- ------------------------------------------------------------
CREATE TABLE carrito (
    id_carrito       SERIAL PRIMARY KEY,
    id_cliente       INT NOT NULL REFERENCES cliente(id_cliente) ON DELETE CASCADE,
    estado           VARCHAR(30) NOT NULL
                     CHECK (estado IN ('activo', 'abandonado', 'convertido')),
    fecha_creacion   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
 
-- Regla de negocio: un solo carrito activo por cliente.
CREATE UNIQUE INDEX idx_carrito_un_activo
    ON carrito (id_cliente)
    WHERE estado = 'activo';
 
CREATE TABLE item_carrito (
    id_carrito  INT NOT NULL REFERENCES carrito(id_carrito) ON DELETE CASCADE,
    id_producto INT NOT NULL REFERENCES producto(id_producto) ON DELETE RESTRICT,
    cantidad    INT NOT NULL CHECK (cantidad > 0),
    PRIMARY KEY (id_carrito, id_producto)
);
 
-- ------------------------------------------------------------
-- 3. Pedido
-- ------------------------------------------------------------
CREATE TABLE pedido (
    id_pedido    SERIAL PRIMARY KEY,
    id_cliente   INT NOT NULL REFERENCES cliente(id_cliente) ON DELETE RESTRICT,
    id_direccion INT REFERENCES direccion_envio(id_direccion) ON DELETE SET NULL,
    fecha        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    estado       VARCHAR(30) NOT NULL
                 CHECK (estado IN ('pendiente', 'pagado', 'enviado',
                                   'entregado', 'cancelado'))
);
-- RESTRICT en id_cliente: no se borra un cliente con historial de compras.
 
CREATE TABLE item_pedido (
    id_pedido      INT NOT NULL REFERENCES pedido(id_pedido) ON DELETE CASCADE,
    id_producto    INT NOT NULL REFERENCES producto(id_producto) ON DELETE RESTRICT,
    cantidad       INT NOT NULL CHECK (cantidad > 0),
    precio_pactado NUMERIC(12,2) NOT NULL CHECK (precio_pactado >= 0),
    PRIMARY KEY (id_pedido, id_producto)
);
 
-- OPCIONAL (pagos)
CREATE TABLE pago (
    id_pago     SERIAL PRIMARY KEY,
    id_pedido   INT NOT NULL REFERENCES pedido(id_pedido) ON DELETE CASCADE,
    monto       NUMERIC(12,2) NOT NULL CHECK (monto > 0),
    metodo      VARCHAR(30) NOT NULL
                CHECK (metodo IN ('tarjeta', 'pse', 'efectivo', 'transferencia')),
    estado      VARCHAR(30) NOT NULL
                CHECK (estado IN ('pendiente', 'aprobado', 'rechazado', 'reembolsado')),
    referencia  VARCHAR(100) UNIQUE,
    fecha_hora  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
 
-- ------------------------------------------------------------
-- 4. Soporte
-- ------------------------------------------------------------
CREATE TABLE ticket_soporte (
    id_ticket      SERIAL PRIMARY KEY,
    id_cliente     INT NOT NULL REFERENCES cliente(id_cliente) ON DELETE CASCADE,
    id_pedido      INT REFERENCES pedido(id_pedido) ON DELETE SET NULL,
    descripcion    TEXT NOT NULL,
    estado         VARCHAR(30) NOT NULL
                   CHECK (estado IN ('abierto', 'en_proceso', 'cerrado')),
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_cierre   TIMESTAMPTZ,
    CHECK (fecha_cierre IS NULL OR fecha_cierre >= fecha_creacion)
);
 
CREATE TABLE asignacion (
    id_asignacion SERIAL PRIMARY KEY,
    id_ticket     INT NOT NULL REFERENCES ticket_soporte(id_ticket) ON DELETE CASCADE,
    id_agente     INT NOT NULL REFERENCES agente(id_agente) ON DELETE RESTRICT,
    fecha_hora    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resultado     VARCHAR(100)
);
 
-- ------------------------------------------------------------
-- 5. Indices de apoyo
-- ------------------------------------------------------------
CREATE INDEX idx_carrito_cliente      ON carrito(id_cliente);
CREATE INDEX idx_pedido_cliente       ON pedido(id_cliente);
CREATE INDEX idx_pedido_estado        ON pedido(estado);
CREATE INDEX idx_item_pedido_producto ON item_pedido(id_producto);
CREATE INDEX idx_ticket_cliente       ON ticket_soporte(id_cliente);
CREATE INDEX idx_ticket_pedido        ON ticket_soporte(id_pedido);
CREATE INDEX idx_ticket_abiertos      ON ticket_soporte(fecha_creacion)
                                      WHERE estado <> 'cerrado';
CREATE INDEX idx_asignacion_ticket    ON asignacion(id_ticket);
CREATE INDEX idx_asignacion_agente    ON asignacion(id_agente);
CREATE INDEX idx_pago_pedido          ON pago(id_pedido);
CREATE INDEX idx_producto_activo      ON producto(activo) WHERE activo;
 
-- ============================================================
-- 6. Datos de prueba
-- ============================================================
 
INSERT INTO cliente (nombre, correo) VALUES
('Ana Torres',  'ana.torres@example.com'),
('Luis Gómez',  'luis.gomez@example.com'),
('María Pérez', 'maria.perez@example.com');
 
INSERT INTO producto (nombre, precio_actual, descripcion, stock_disponible) VALUES
('Teclado mecánico',  150000.00, 'Teclado mecánico switches rojos', 25),
('Mouse inalámbrico',  60000.00, 'Mouse ergonómico 2.4GHz',         40),
('Monitor 24"',       650000.00, 'Monitor Full HD IPS',             10),
('Audífonos gamer',   120000.00, 'Audífonos con micrófono',         15);
 
INSERT INTO agente (nombre) VALUES
('Carlos Ruiz'),
('Diana Salazar');
 
INSERT INTO direccion_envio (id_cliente, linea, ciudad, telefono) VALUES
(1, 'Calle 45 #12-30, Apto 402', 'Bogotá',   '3001112233'),
(2, 'Carrera 7 #80-15',          'Medellín', '3004445566'),
(3, 'Av. Siempre Viva 742',      'Cali',     '3007778899');
 
-- Carritos: solo uno activo por cliente (indice unico parcial)
INSERT INTO carrito (id_cliente, estado) VALUES
(1, 'activo'),
(2, 'activo'),
(3, 'abandonado');
 
INSERT INTO pedido (id_cliente, id_direccion, fecha, estado) VALUES
(1, 1, NOW(),                        'pendiente'),
(2, 2, NOW() - INTERVAL '2 days',    'enviado'),
(3, 3, NOW() - INTERVAL '5 days',    'entregado');
 
INSERT INTO item_carrito (id_carrito, id_producto, cantidad) VALUES
(1, 1, 2),
(1, 2, 1),
(2, 3, 1);
 
INSERT INTO item_pedido (id_pedido, id_producto, cantidad, precio_pactado) VALUES
(1, 1, 1, 150000.00),
(2, 3, 1, 650000.00),
(2, 4, 2, 120000.00),
(3, 2, 3,  60000.00);
 
INSERT INTO pago (id_pedido, monto, metodo, estado, referencia, fecha_hora) VALUES
(2, 890000.00, 'tarjeta', 'aprobado', 'REF-000002', NOW() - INTERVAL '2 days'),
(3, 180000.00, 'pse',     'aprobado', 'REF-000003', NOW() - INTERVAL '5 days');
 
INSERT INTO ticket_soporte (id_cliente, id_pedido, descripcion, estado, fecha_creacion, fecha_cierre) VALUES
(1, 1,    'El producto no ha llegado',      'abierto',    NOW(),                     NULL),
(2, 2,    'Cambio de dirección de envío',   'en_proceso', NOW() - INTERVAL '1 day',  NULL),
(3, NULL, 'Consulta sobre garantía',        'cerrado',    NOW() - INTERVAL '3 days', NOW() - INTERVAL '2 days');
 
INSERT INTO asignacion (id_ticket, id_agente, fecha_hora, resultado) VALUES
(1, 1, NOW(),                     'asignado'),
(2, 2, NOW(),                     'asignado'),
(3, 1, NOW() - INTERVAL '3 days', 'resuelto');
