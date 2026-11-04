# Modelo de amenazas: SHOP-HUB

Guía Módulo 7, semana 13, §5. Revisado el 2026-11-02 y actualizado el 2026-11-04 (HU-03, HU-04 criterio 3 y HU-10) sobre la rama `feature/seguridad-e-interfaz`.

> No todos los riesgos se pueden eliminar: se gestionan según su impacto y su probabilidad. Este documento dice qué se controló, con qué evidencia y qué riesgo queda.

## 1. El sistema y sus fronteras de confianza

```
 Usuario (navegador)          │ Sistema SHOP-HUB (Django)                         │  Servicios externos
 cliente · agente · admin     │                                                   │
                              │  Web (plantillas)  ─┐                             │  (ninguno hoy: no hay
 ──── HTTPS (HTTPS=true) ────►│                     ├─► Servicios ─► ORM ─► PostgreSQL   pasarela de pago,
                              │  API JSON (/api/) ──┘   (reglas)                  │   correo ni llamadas
        ▲ frontera 1          │        ▲ frontera 2: sesión + rol + validación    │   salientes: no aplica SSRF)
        no se confía en nada  │          frontera 3: consultas parametrizadas     │
        de lo que llega       │                                                   │
```

- **Frontera 1 (navegador → servidor):** todo lo que llega del cliente es no confiable: cuerpo JSON, formularios, parámetros, URL y cookies.
- **Frontera 2 (vista → servicio):** la identidad sale de la sesión y el rol se verifica en el servidor. Los datos se validan con lista de permitidos.
- **Frontera 3 (servicio → base de datos):** solo ORM, con consultas parametrizadas. Las operaciones críticas van en transacción con `SELECT ... FOR UPDATE`.

## 2. Activos

| Activo | Por qué importa |
| --- | --- |
| Credenciales y sesiones | Con ellas se actúa como el cliente o el agente |
| Datos de clientes | Nombre, email, pedidos y contenido de las PQR (datos personales) |
| Pedidos e inventario | Dinero y stock: no deben alterarse ni quedar negativos |
| Asignación de tickets | El problema duro: un ticket, un solo agente |
| Disponibilidad del servicio | Si cae, nadie compra ni radica PQR |
| Configuración y secretos | `SECRET_KEY` y contraseña de la base de datos |

## 3. Amenazas, controles y evidencia

Impacto y probabilidad: **Alto / Medio / Bajo**. El riesgo residual es lo que queda con los controles puestos.

| # | Activo | Amenaza | Vectores de ataque | Impacto | Controles aplicados | Evidencia (prueba) | Riesgo residual |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Credenciales | Suplantación de identidad | Fuerza bruta, credenciales filtradas, identidad en el cuerpo JSON (H1-H3) | **Alto** | Sesión de Django; identidad solo desde la sesión; 5 intentos → 429 por 15 min; hash PBKDF2; contraseña mínima de 10 caracteres; mismo mensaje si el usuario existe o no | `FuerzaBrutaTests`, `ADL01*`, `SesionYRegistroTests`, `test_el_login_no_revela_si_el_usuario_existe` | **Medio**: no hay MFA; el bloqueo es por usuario + IP (un ataque de *password spraying* desde muchas IP no se frena); el límite vive en la memoria de cada proceso (DT-12) |
| A2 | Sesiones | Robo o fijación de sesión, CSRF | XSS para robar la cookie, enlace malicioso que hace un POST | **Alto** | Cookies `HttpOnly` y `SameSite=Lax`; `Secure` y HSTS con `HTTPS=true`; `login()` rota la sesión; CSRF en la API y la web; sesión de 8 h; salir solo por POST | `H13CsrfConSesionTests`, `test_los_formularios_exigen_csrf`, `test_salir_solo_por_post` | **Bajo** |
| A3 | Datos de clientes | Exposición de datos | IDOR (`/api/pedidos/<id>/`), SQLi, mensajes de error detallados, `?debug=true` | **Alto** | Pedido o ticket ajeno → 404 (ADL-03); solo ORM; guardia que falla si aparece SQL crudo; `DEBUG=False` por defecto; red genérica de errores; `Cache-Control: no-store` en la API | `IdorTests`, `InyeccionSqlTests`, `DivulgacionDeInformacionTests`, `ADL03*`, `ADL06*` | **Bajo** |
| A4 | Datos de clientes | XSS almacenado | `<script>` en el asunto o la descripción de una PQR que luego ve el agente | **Alto** | Escape automático de plantillas; CSP sin `unsafe-inline`; la interfaz no usa JS en línea | `XssTests`, `test_el_contenido_del_usuario_se_escapa`, `CabecerasDeSeguridadTests` | **Bajo** |
| A5 | Pedidos e inventario | Modificación no autorizada | Comprar a nombre de otro; manipular precio o cantidad; floats y enteros enormes (H5, H6); stock negativo por concurrencia | **Alto** | Lista de permitidos de campos y tipos; cotas (1000 unidades, 50 ítems); el precio sale siempre de la base de datos; checkout transaccional con bloqueo de filas | `ADL04*`, `test_criterio3_datos_invalidos_o_sin_stock_no_crean_el_pedido`, `CarritoSesionTests` | **Bajo** |
| A6 | Asignación de tickets | Doble asignación (problema duro); un cliente que toma tickets | Dos agentes a la vez; cliente que llama a `/tomar/` | **Alto** | `select_for_update` en la transacción; rol de agente verificado en el servicio; registro de cada asignación | `HU08ConcurrenciaTests` (PostgreSQL), `test_un_cliente_que_intenta_tomar_un_ticket_recibe_403` | **Bajo** |
| A7 | Disponibilidad | Denegación de servicio | Abuso de endpoints, peticiones masivas, cuerpos gigantes, caracteres que tumbaban PostgreSQL (H7, H8) | **Medio** | 30 escrituras por minuto por usuario (429); 10 registros por hora por IP; cuerpo máximo de 64 KB (413); NUL y surrogates → 400 | `LimiteDePeticionesTests`, `ADL05*` | **Medio**: las lecturas (GET) no tienen límite; un ataque distribuido necesita protección del proxy o la infraestructura |
| A8 | Integridad del registro | Repudio («yo no hice eso») | Acciones sin rastro | **Medio** | Tabla `EventoAuditoria`: login, logout, registro, pedidos, tickets, conflictos 409, accesos denegados, CSRF, 429 y 500. Solo lectura en `/admin/`; nunca guarda contraseñas | `RegistroDeEventosCriticosTests` | **Bajo**: el superusuario podría borrarlo desde la base de datos |
| A9 | Configuración y secretos | Secretos expuestos | `SECRET_KEY` en el código o en Git (H11, H12), `.env` subido por error | **Alto** | Sin claves de respaldo; con `DEBUG=False` se rechaza una clave de ejemplo; `.env` en `.gitignore`; gitleaks en el CI | `ADL07*`, job `seguridad` del CI | **Medio**: las 2 claves viejas siguen en el historial (DT-13, decisión del equipo) |
| A10 | Plataforma | Componentes vulnerables | Una versión de Django o psycopg2 con un CVE | **Medio** | `pip-audit` en el CI; bandit (SAST) | job `seguridad` del CI | **Bajo** |
| A11 | Privilegios | Escalada de rol | Registrarse como agente; agente que entra a `/admin/` (H14) | **Alto** | El registro siempre crea un cliente (campo `rol` → 400); agente = grupo, sin `is_staff` | `test_registro_crea_cliente_y_no_permite_elegir_rol`, `H14*` | **Bajo** |
| A12 | Datos de clientes | Exposición de datos de envío (dirección, teléfono) | IDOR sobre `/api/pedidos/<id>/`; datos personales copiados al registro de auditoría | **Alto** | Solo el dueño y los agentes ven el envío (404 al resto); la auditoría guarda el código del pedido, nunca la dirección ni el teléfono; validación con lista de permitidos | `test_seguridad_envio.py` | **Bajo** |
| A13 | Pedidos e inventario | Manipulación del catálogo (precio o stock) | Cliente o agente que llama a `POST`/`PATCH /api/productos/`; asignación masiva (`id`, `creado_en`); precio negativo o NaN | **Alto** | Solo el superusuario (verificado en la vista y en el servicio); campos permitidos; `dinero()` y `entero(minimo=0)`; bloqueo de fila al editar; el precio de los pedidos pagados no cambia (`precio_pactado`); auditoría | `test_seguridad_hu03.py` | **Bajo** |
| A14 | Atención de tickets | Respuesta o cierre por quien no corresponde; saltar estados | Agente no asignado o cliente llamando a `/respuestas/` o `/estado/`; cerrar sin resolver; dos cierres a la vez | **Medio** | Solo el agente asignado (403); transiciones permitidas (409); `select_for_update`; XSS escapado; auditoría de cada respuesta y cambio de estado | `test_seguridad_hu10.py` (incluye concurrencia en PostgreSQL) | **Bajo** |

## 4. OWASP Top 10 (2021): cómo queda el proyecto

| # | Categoría | Estado | Dónde |
| --- | --- | --- | --- |
| A01 | Control de acceso roto | ✅ Controlado | A1, A3, A6, A11 |
| A02 | Fallos criptográficos | ✅ hash PBKDF2, HTTPS y HSTS (`HTTPS=true`) · ⚠️ depende de servir el sitio por HTTPS | A1, A2 |
| A03 | Inyección | ✅ ORM + guardia estática + pruebas `' OR 1=1 --` | A3 |
| A04 | Diseño inseguro | ✅ modelo de amenazas, reglas en los servicios, lista de permitidos | este documento |
| A05 | Configuración incorrecta | ✅ `DEBUG=False`, cabeceras, `check --deploy` en el CI | A9 |
| A06 | Componentes vulnerables | ✅ `pip-audit` en el CI | A10 |
| A07 | Identificación y autenticación | ✅ con riesgo residual (sin MFA) | A1 |
| A08 | Integridad de software y datos | ✅ CSRF, transacciones, CI con quality gates | A2, A5 |
| A09 | Registro y monitoreo insuficientes | ✅ `EventoAuditoria` + log · ⚠️ sin alertas automáticas | A8 |
| A10 | SSRF | No aplica: el sistema no hace peticiones salientes | — |

## 5. Riesgos aceptados o pendientes

Decisión del equipo: llenar en el [AI Decision Log](ai-decision-log-seguridad.md).

| Riesgo | Por qué se acepta o pospone | Seguimiento |
| --- | --- | --- |
| Sin MFA | Alcance del curso; el control compensatorio es el bloqueo por intentos | DT-14 |
| Límite de peticiones en memoria por proceso | Suficiente con un solo proceso (demo); en producción hay que usar Redis | DT-12 |
| Claves en el historial de Git | Purgar la historia afecta a todo el equipo | DT-13 |
| Sin alertas automáticas sobre el registro | El registro existe y se consulta en `/admin/` | — |
