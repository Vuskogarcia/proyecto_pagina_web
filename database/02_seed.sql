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
