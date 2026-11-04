# Historias de usuario implementadas

Cada historia tiene criterios de aceptación **verificables** y un archivo de
pruebas que los comprueba. El backlog completo está en
[`Historia de usuario/historias.md`](Historia%20de%20usuario/historias.md);
aquí está solo lo que ya funciona y cómo comprobarlo.

Correr todas las pruebas (desde la carpeta `tests/`):

```bash
python manage.py test
```

Resultado esperado: **172 pruebas en verde** (en PostgreSQL): 27 de integración por historia (3 por HU, de HU-02 a HU-10), 2 del comando `cargar_datos_demo`, 42 unitarias, 15 de casos borde, 71 de seguridad y 15 de la interfaz web.

**Las 10 historias del backlog están implementadas.** El detalle por archivo está en el README §5.1.

La API ahora usa la **sesión** del usuario (HU-01): ya no recibe `id_cliente` ni `id_agente` en el cuerpo. Ver [`seguridad/semana-13.md`](seguridad/semana-13.md).

Cada historia cumple la [Definición de Terminado](definicion-de-terminado.md).

| HU | Historia | Endpoint | Archivo de pruebas | Pruebas |
| --- | --- | --- | --- | --- |
| HU-01 | Registro e inicio de sesión con roles | `POST /api/registro/` · `GET/POST/DELETE /api/sesion/` · web `/entrar/`, `/registro/` | `comun/pruebas/test_seguridad.py` (`SesionYRegistroTests`, `ADL01*`) · `web/pruebas/test_interfaz.py` (`AccesoPorRolTests`) | 3 + 3 |
| HU-02 | Consultar catálogo | `GET /api/productos/` · `GET /api/productos/<id>/` | `catalogo/pruebas/test_hu02_consultar_catalogo.py` | 3 |
| HU-03 | Gestionar catálogo e inventario | `POST /api/productos/` · `PATCH /api/productos/<id>/` · `GET /api/gestion/productos/` · web `/gestion/productos/` | `catalogo/pruebas/test_hu03_gestionar_catalogo.py` | 3 |
| HU-04 | Carrito, envío y checkout | `POST /api/pedidos/` · `GET /api/pedidos/<id>/` · web `/carrito/`, `/carrito/pagar/` | `carrito/pruebas/test_hu04_checkout.py` | 3 |
| HU-05 | Crear ticket asociado a un pedido | `POST /api/tickets/` | `soporte/pruebas/test_hu05_crear_ticket.py` | 3 |
| HU-06 | Consultar mis tickets | `GET /api/tickets/` · `GET /api/tickets/<id>/` · web `/pqr/` | `soporte/pruebas/test_hu06_mis_tickets.py` | 3 |
| HU-07 | Cola de tickets sin asignar | `GET /api/tickets/cola/` | `soporte/pruebas/test_hu07_cola_sin_asignar.py` | 3 |
| HU-08 | Tomar ticket con control de concurrencia | `POST /api/tickets/<id>/tomar/` | `soporte/pruebas/test_hu08_tomar_ticket.py` | 3 |
| HU-09 | Ver el pedido asociado al ticket | `GET /api/tickets/<id>/` → `GET /api/pedidos/<id>/` · web `/pqr/<id>/` | `soporte/pruebas/test_hu09_pedido_del_ticket.py` | 3 |
| HU-10 | Responder y cambiar el estado | `POST /api/tickets/<id>/respuestas/` · `POST /api/tickets/<id>/estado/` · web `/pqr/<id>/` | `soporte/pruebas/test_hu10_responder_ticket.py` | 3 |

Cada historia nueva tiene además su archivo de **seguridad**:

- `catalogo/pruebas/test_seguridad_hu03.py`
- `carrito/pruebas/test_seguridad_envio.py`
- `soporte/pruebas/test_seguridad_hu10.py`

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

## HU-03 · Gestionar catálogo e inventario

> Como administrador, quiero gestionar el catálogo y el inventario para
> mantener actualizada la información de los productos disponibles.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 1 y 4. El administrador crea productos y aparecen en el catálogo. | `test_criterio1y4_crea_un_producto_y_aparece_en_el_catalogo` |
| 2 y 4. Modifica nombre, descripción, precio y stock, y el catálogo lo refleja. | `test_criterio2y4_modifica_nombre_descripcion_precio_y_stock` |
| 3 y 4. Desactiva productos: salen del catálogo sin borrarse. | `test_criterio3y4_desactivar_lo_retira_del_catalogo_sin_borrarlo` |
| Regla: solo el administrador (superusuario); los cambios de precio no alteran pedidos ya pagados. | `test_seguridad_hu03.py` |

## HU-04 · Checkout

> Como cliente, quiero agregar productos a un carrito y realizar el checkout
> para completar mi compra.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 2. El sistema calcula correctamente el total (y el checkout descuenta el stock). | `test_criterio2_calcula_el_total_y_descuenta_el_stock` |
| 1. El cliente agrega y quita productos del carrito antes de pagar (carrito en la sesión; precio y stock se leen de la base de datos). | `test_agregar_cambiar_quitar_y_pagar_el_carrito` (web) · `CarritoSesionTests` |
| 3. El cliente ingresa los datos necesarios: **envío obligatorio** (nombre, dirección, ciudad y teléfono). Además: 400 si los datos están incompletos o mal formados, 404 si el producto no existe, 401 sin sesión y 409 sin stock suficiente (no se crea el pedido ni se descuenta nada). | `test_criterio3_datos_invalidos_o_sin_stock_no_crean_el_pedido` · `test_seguridad_envio.py` |
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

## HU-06 · Consultar mis tickets

> Como cliente, quiero consultar el estado de mis tickets para conocer el
> avance de mi solicitud.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 1 y 2. Veo solo mis tickets, con número, fecha, asunto y pedido. | `test_criterio1y2_veo_solo_mis_tickets_con_numero_fecha_asunto_y_pedido` |
| 3. Estados Abierto, En proceso, Resuelto y Cerrado. | `test_criterio3_muestra_los_estados_abierto_en_proceso_resuelto_y_cerrado` |
| 4. El estado se actualiza cuando el agente hace cambios. | `test_criterio4_el_estado_se_actualiza_cuando_el_agente_hace_cambios` |

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

## HU-09 · Ver el pedido asociado al ticket

> Como agente, quiero consultar la información del pedido asociado a un
> ticket para conocer qué compró el cliente antes de atender su solicitud.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 1. Desde el ticket se llega al pedido. | `test_criterio1_desde_el_ticket_se_llega_al_pedido` |
| 2 y 3. Se ven los productos, la fecha y el estado del pedido. | `test_criterio2y3_muestra_productos_fecha_y_estado_del_pedido` |
| 4. La información corresponde al pedido del ticket. | `test_criterio4_la_informacion_corresponde_al_pedido_del_ticket` |

## HU-10 · Responder y cambiar el estado del ticket

> Como agente, quiero responder los tickets que tengo asignados y cambiar su
> estado para registrar el proceso de atención.

| Criterio | Prueba que lo verifica |
| --- | --- |
| 1. Solo el agente asignado responde (otro agente: 403). | `test_criterio1_solo_el_agente_asignado_puede_responder` |
| 2. La respuesta queda registrada con fecha y autor. | `test_criterio2_la_respuesta_queda_registrada_con_fecha_y_autor` |
| 3 y 4. En proceso → Resuelto → Cerrado; el cliente ve la respuesta y el nuevo estado. | `test_criterio3y4_cambia_el_estado_y_el_cliente_ve_respuesta_y_estado` |
| Regla: solo las transiciones permitidas (no se cierra sin resolver; Resuelto se puede reabrir; Cerrado es final); dos cierres simultáneos → uno solo gana. | `test_seguridad_hu10.py` (`CambioDeEstadoConcurrenteTests`, PostgreSQL) |

```bash
python manage.py test soporte
```

> La prueba de concurrencia necesita PostgreSQL: SQLite no soporta
> `SELECT ... FOR UPDATE`.

---

## Pendientes del backlog

Ninguna historia del backlog queda pendiente. Las mejoras que quedan están priorizadas en [`deuda-tecnica.md`](deuda-tecnica.md) (por ejemplo: MFA, recuperación de contraseña y caché compartida para los límites).
