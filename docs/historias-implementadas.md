# Historias de usuario implementadas

Cada historia tiene criterios de aceptación **verificables** y un archivo de
pruebas que los comprueba. El backlog completo está en
[`Historia de usuario/historias.md`](Historia%20de%20usuario/historias.md);
aquí está solo lo que ya funciona y cómo comprobarlo.

Correr todas las pruebas (desde la carpeta `tests/`):

```bash
python manage.py test
```

Resultado esperado: **17 pruebas en verde** (3 por cada historia de usuario y 2 del comando `cargar_datos_demo`).

| HU | Historia | Endpoint | Archivo de pruebas | Pruebas |
| --- | --- | --- | --- | --- |
| HU-02 | Consultar catálogo | `GET /api/productos/` · `GET /api/productos/<id>/` | `catalogo/pruebas/test_hu02_consultar_catalogo.py` | 3 |
| HU-04 | Checkout | `POST /api/pedidos/` · `GET /api/pedidos/<id>/` | `carrito/pruebas/test_hu04_checkout.py` | 3 |
| HU-05 | Crear ticket asociado a un pedido | `POST /api/tickets/` | `soporte/pruebas/test_hu05_crear_ticket.py` | 3 |
| HU-07 | Cola de tickets sin asignar | `GET /api/tickets/cola/` | `soporte/pruebas/test_hu07_cola_sin_asignar.py` | 3 |
| HU-08 | Tomar ticket con control de concurrencia | `POST /api/tickets/<id>/tomar/` | `soporte/pruebas/test_hu08_tomar_ticket.py` | 3 |

---

## HU-02 · Consultar catálogo

> Como cliente, quiero consultar el catálogo de productos para conocer los
> productos disponibles antes de realizar una compra.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 1 y 2. El sistema muestra los productos disponibles (los retirados no aparecen), cada uno con nombre, precio y descripción. | `test_criterio1y2_muestra_solo_productos_activos_con_nombre_precio_y_descripcion` |
| 3. Se puede consultar el detalle de un producto (404 si no existe o fue retirado). | `test_criterio3_consultar_detalle_de_un_producto` |
| 4. Los productos sin disponibilidad se identifican como agotados. | `test_criterio4_producto_sin_stock_se_identifica_como_agotado` |

```bash
python manage.py test catalogo
```

## HU-04 · Checkout

> Como cliente, quiero agregar productos a un carrito y realizar el checkout
> para completar mi compra.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 2. El sistema calcula correctamente el total (y el checkout descuenta el stock). | `test_criterio2_calcula_el_total_y_descuenta_el_stock` |
| 3. Los datos del pedido se validan: 400 si están incompletos o mal formados, 404 si el producto o el cliente no existe, 409 sin stock suficiente (no se crea el pedido ni se descuenta nada). | `test_criterio3_datos_invalidos_o_sin_stock_no_crean_el_pedido` |
| 4. Se genera un pedido con identificador único `PED-00001` que se puede consultar. | `test_criterio4_genera_pedido_con_identificador_unico` |

> Pendiente del criterio 1 (agregar y quitar del carrito antes de pagar): hoy
> el checkout recibe la lista de productos en una sola petición.

```bash
python manage.py test carrito
```

## HU-05 · Crear ticket asociado a un pedido

> Como cliente, quiero crear un ticket de soporte asociado a uno de mis
> pedidos para reportar una duda, reclamo o problema con mi compra.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 1, 2 y 4. El ticket queda asociado al pedido seleccionado y guarda asunto y descripción (prueba de punta a punta HTTP → BD). | `test_crear_ticket_endpoint_e2e` |
| 3. Se genera un número único de ticket `TCK-00001`. | `test_criterio3_genera_un_numero_unico_de_ticket` |
| Regla: no se crea el ticket con el pedido de otro cliente, sin descripción (400) o con cliente o pedido inexistente (404). | `test_datos_invalidos_o_pedido_ajeno_no_crean_el_ticket` |

## HU-07 · Cola de tickets sin asignar

> Como agente de servicio al cliente, quiero visualizar una cola de tickets sin
> asignar para elegir cuáles atender.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 1 y 4. Se ven los tickets sin asignar; uno ya asignado no aparece. | `test_criterio1y4_muestra_solo_los_tickets_sin_asignar` |
| 2. Cada ticket muestra el cliente y el pedido asociado. | `test_criterio2_cada_ticket_muestra_cliente_y_pedido` |
| 3. Ordenada por fecha. | `test_criterio3_ordenada_por_fecha_del_mas_antiguo_al_mas_nuevo` |

## HU-08 · Tomar ticket con control de concurrencia (problema duro)

> Como agente de servicio al cliente, quiero tomar (asignarme) un ticket de la
> cola para atenderlo, incluso si otro agente intenta tomarlo al mismo tiempo.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 1 y 4. El ticket queda asignado solo al agente que lo pidió y la asignación queda registrada (agente, ticket, fecha). | `test_criterio1y4_el_ticket_queda_asignado_y_registrado` |
| 2. Si ya fue tomado, el otro agente recibe un mensaje claro (409) y el intento no deja registro. | `test_criterio2_un_ticket_ya_tomado_responde_409` |
| 3. Prueba automatizada de asignación concurrente con dos hilos. | `test_criterio3_dos_agentes_compiten_y_solo_uno_obtiene_el_ticket` |

```bash
python manage.py test soporte
```

> La prueba de concurrencia necesita PostgreSQL: SQLite no soporta
> `SELECT ... FOR UPDATE`.

---

## Pendientes del backlog

- **HU-01** (registro e inicio de sesión con roles): hoy la API recibe
  `id_cliente` / `id_agente` en el cuerpo de la petición. Cuando exista el
  login, esos datos saldrán de la sesión del usuario.
- **HU-03** (gestión del catálogo): se puede hacer desde `/admin/`, pero aún no
  tiene endpoints ni pruebas propias.
- **HU-06, HU-09, HU-10**: sin implementar.
