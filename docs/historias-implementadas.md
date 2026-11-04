# Historias de usuario implementadas

Cada historia tiene criterios de aceptación **verificables** y un archivo de
pruebas que los comprueba. El backlog completo está en
[`Historia de usuario/historias.md`](Historia%20de%20usuario/historias.md);
aquí está solo lo que ya funciona y cómo comprobarlo.

Correr todas las pruebas (desde la carpeta `tests/`):

```bash
python manage.py test
```

Resultado esperado: **134 pruebas en verde** (en PostgreSQL): 15 de integración por historia (3 por HU), 2 del comando `cargar_datos_demo`, 42 unitarias, 15 de casos borde, 45 de seguridad y 15 de la interfaz web. El detalle por archivo está en el README §5.1.

La API ahora usa la **sesión** del usuario (HU-01): ya no recibe `id_cliente` ni `id_agente` en el cuerpo. Ver [`seguridad/semana-13.md`](seguridad/semana-13.md).

Cada historia cumple la [Definición de Terminado](definicion-de-terminado.md).

| HU | Historia | Endpoint | Archivo de pruebas | Pruebas |
| --- | --- | --- | --- | --- |
| HU-01 | Registro e inicio de sesión con roles | `POST /api/registro/` · `GET/POST/DELETE /api/sesion/` · web `/entrar/`, `/registro/` | `comun/pruebas/test_seguridad.py` (`SesionYRegistroTests`, `ADL01*`) · `web/pruebas/test_interfaz.py` (`AccesoPorRolTests`) | 3 + 3 |
| HU-02 | Consultar catálogo | `GET /api/productos/` · `GET /api/productos/<id>/` | `catalogo/pruebas/test_hu02_consultar_catalogo.py` | 3 |
| HU-04 | Checkout | `POST /api/pedidos/` · `GET /api/pedidos/<id>/` | `carrito/pruebas/test_hu04_checkout.py` | 3 |
| HU-05 | Crear ticket asociado a un pedido | `POST /api/tickets/` | `soporte/pruebas/test_hu05_crear_ticket.py` | 3 |
| HU-07 | Cola de tickets sin asignar | `GET /api/tickets/cola/` | `soporte/pruebas/test_hu07_cola_sin_asignar.py` | 3 |
| HU-08 | Tomar ticket con control de concurrencia | `POST /api/tickets/<id>/tomar/` | `soporte/pruebas/test_hu08_tomar_ticket.py` | 3 |
| HU-06 | Consultar mis tickets | `GET /api/tickets/` · web `/pqr/` | `web/pruebas/test_interfaz.py` (`test_radicar_pqr_sobre_mi_pedido_y_verla_en_mis_pqr`) | 1 |
| HU-09 | Ver el pedido asociado al ticket | `GET /api/pedidos/<id>/` (agente) · web `/pqr/<id>/` | `web/pruebas/test_interfaz.py` (`test_el_agente_ve_el_pedido_asociado_al_ticket`) · `test_seguridad.py` (`ADL03*`) | 2 |

---

## HU-01 · Registro e inicio de sesión con roles

> Como usuario, quiero registrarme e iniciar sesión con un rol definido
> (cliente, agente o administrador) para acceder a las funciones de mi rol.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 1. Registro con email y contraseña (política de contraseñas de Django, mínimo 10). | `test_registro_crea_cliente_y_no_permite_elegir_rol` · `test_registro_crea_cliente_y_entra` |
| 2. Rol cliente por defecto; agente (grupo `agentes`) y administrador los asigna un administrador. | `test_registro_crea_cliente_y_no_permite_elegir_rol` · `RolesTests` |
| 3. Cada rol solo ve sus opciones. | `test_el_menu_muestra_solo_las_opciones_del_rol` · `test_cliente_no_entra_al_panel_de_agente_y_agente_no_usa_el_carrito` |
| 4. Sin sesión no se accede a rutas protegidas (401 en la API, redirección a `/entrar/` en la web). | `test_sin_sesion_la_api_protegida_responde_401_y_no_cambia_nada` · `test_anonimo_ve_el_catalogo_pero_las_rutas_protegidas_piden_entrar` |
| Regla: 5 intentos fallidos bloquean el inicio de sesión (429). | `test_tras_5_intentos_fallidos_se_bloquea_aunque_la_clave_sea_correcta` |

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
| 1. El cliente agrega y quita productos del carrito antes de pagar (carrito en la sesión; precio y stock se leen de la base de datos). | `test_agregar_cambiar_quitar_y_pagar_el_carrito` (web) · `CarritoSesionTests` |
| 3. Los datos del pedido se validan: 400 si están incompletos o mal formados, 404 si el producto no existe, 401 sin sesión, 409 sin stock suficiente (no se crea el pedido ni se descuenta nada). | `test_criterio3_datos_invalidos_o_sin_stock_no_crean_el_pedido` |
| 4. Se genera un pedido con identificador único `PED-00001` que se puede consultar. | `test_criterio4_genera_pedido_con_identificador_unico` |

> El criterio 1 vive en la interfaz web (`/carrito/`). La API conserva el
> checkout en una sola petición (`POST /api/pedidos/`).

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
| Regla: no se crea el ticket sin descripción (400), con un pedido inexistente o **de otro cliente** (404 en ambos casos, ADL-03), ni eligiendo el cliente por el cuerpo (400). | `test_datos_invalidos_o_pedido_ajeno_no_crean_el_ticket` |
| Tipo de PQR: petición, queja o reclamo (`tipo`). | `test_radicar_pqr_sobre_mi_pedido_y_verla_en_mis_pqr` (web) |

## HU-07 · Cola de tickets sin asignar

> Como agente de servicio al cliente, quiero visualizar una cola de tickets sin
> asignar para elegir cuáles atender.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 1 y 4. Se ven los tickets sin asignar; uno ya asignado no aparece. | `test_criterio1y4_muestra_solo_los_tickets_sin_asignar` |
| 2. Cada ticket muestra el cliente y el pedido asociado. | `test_criterio2_cada_ticket_muestra_cliente_y_pedido` |
| 3. Ordenada por fecha, en ambos sentidos (`?orden=recientes`). | `test_criterio3_ordenada_por_fecha_del_mas_antiguo_al_mas_nuevo` · `test_la_cola_se_puede_ordenar_de_la_mas_nueva_a_la_mas_antigua` |
| Regla: solo agentes (401 sin sesión, 403 si es cliente). | `test_la_cola_es_solo_para_agentes` |

## HU-08 · Tomar ticket con control de concurrencia (problema duro)

> Como agente de servicio al cliente, quiero tomar (asignarme) un ticket de la
> cola para atenderlo, incluso si otro agente intenta tomarlo al mismo tiempo.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 1 y 4. El ticket queda asignado solo al agente que lo pidió y la asignación queda registrada (agente, ticket, fecha). | `test_criterio1y4_el_ticket_queda_asignado_y_registrado` |
| 2. Si ya fue tomado, el otro agente recibe un mensaje claro (409) y el intento no deja registro. | `test_criterio2_un_ticket_ya_tomado_responde_409` |
| Regla: solo un agente puede tomar tickets; un cliente recibe 403 (defecto RC-01 corregido). | `test_un_cliente_que_intenta_tomar_un_ticket_recibe_403` |
| 3. Prueba automatizada de asignación concurrente con dos hilos. | `test_criterio3_dos_agentes_compiten_y_solo_uno_obtiene_el_ticket` |

```bash
python manage.py test soporte
```

> La prueba de concurrencia necesita PostgreSQL: SQLite no soporta
> `SELECT ... FOR UPDATE`.

---

## Pendientes del backlog

Los pendientes están priorizados en [`deuda-tecnica.md`](deuda-tecnica.md).

- **HU-03** (gestión del catálogo): se hace desde `/admin/` (superusuario), sin
  endpoints ni pruebas propias.
- **HU-06** criterio 4 y **HU-10** (el agente responde y cambia el estado del
  ticket): sin implementar. Hoy el estado solo pasa de Abierto a En proceso al
  tomarlo. Falta el estado *Resuelto* (DT-03).
