# Semana 13: Endurecimiento y seguridad básica del producto

Evidencia del Módulo 7 (Ingeniería de Software 702301). Rama `feature/seguridad-e-interfaz`, sin commit al momento de escribir este documento.

> **Regla de oro:** nunca confíes; verifica, autoriza y registra.
> Que todas las pruebas pasen no hace seguro al sistema: demuestra que los ataques probados aquí están controlados. Los riesgos que quedan están en el [modelo de amenazas](modelo-amenazas.md) §5.

| Evidencia que pide la guía (§8) | Dónde está |
| --- | --- |
| Checklist de controles aplicado y actualizado | §1 de este documento |
| Modelo de amenazas del sistema | [`modelo-amenazas.md`](modelo-amenazas.md) |
| Pruebas de seguridad ejecutadas y resultados | §2 y [`evidencia/semana-13-ejecucion-postgresql.txt`](evidencia/semana-13-ejecucion-postgresql.txt) |
| Correcciones aplicadas | [`correcciones-seguridad.md`](correcciones-seguridad.md) · commits o PR: **pendiente**, el equipo aún no hace commit |
| Registro de decisiones técnicas | [`ai-decision-log-seguridad.md`](ai-decision-log-seguridad.md) |
| Vínculo con historias | HU-01 (autenticación y roles), HU-04, HU-05, HU-08 (ver [`historias-implementadas.md`](../historias-implementadas.md)) |

## 1. Checklist de controles mínimos (guía §4)

| Control | Estado | Cómo | Prueba |
| --- | --- | --- | --- |
| Autenticación implementada | ✅ | Sesión de Django (HU-01): registro, entrar y salir | `SesionYRegistroTests`, `ADL01*` |
| Autorización basada en roles y permisos | ✅ | cliente · agente (grupo) · administrador; verificada en el servidor; recurso ajeno → 404 | `ADL01*`, `ADL03*`, `AccesoPorRolTests`, `IdorTests` |
| Validación de todas las entradas | ✅ | Servidor: lista de permitidos de campos y tipos, cotas, texto sin NUL ni surrogates. Cliente: `required`, `maxlength`, `minlength` y `type=email` en los formularios (sin `novalidate`) | `ADL04*`, `ADL05*` |
| Consultas parametrizadas | ✅ | Solo ORM; una guardia estática falla si aparece SQL crudo | `InyeccionSqlTests` |
| Gestión segura de sesiones | ✅ | Vence a las 8 h, se rota al entrar, cookies `HttpOnly` y `SameSite`, salir solo por POST, CSRF | `H13*`, `test_salir_solo_por_post` |
| Protección de datos sensibles | ✅ | Contraseñas con hash PBKDF2; `SECRET_KEY` y contraseña de la BD fuera del código; HTTPS y HSTS con `HTTPS=true`; el registro de auditoría nunca guarda claves | `ADL07*`, `test_login_fallido_exitoso_y_salida_quedan_registrados_sin_la_clave` |
| Mensajes de error sin información sensible | ✅ | `DEBUG=False` por defecto; 500 genérico; páginas 403, 404, 429 y 500 propias | `ADL06*`, `DivulgacionDeInformacionTests` |
| Cabeceras de seguridad básicas | ✅ | CSP sin `unsafe-inline`, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, COOP, `Permissions-Policy` | `CabecerasDeSeguridadTests`, `XssTests` |
| Registro de eventos críticos (auditoría) | ✅ | Tabla `EventoAuditoria` (13 tipos de evento), de solo lectura en `/admin/` | `RegistroDeEventosCriticosTests` |

## 2. Pruebas de seguridad: ataques simulados (guía §6)

Archivo: `tests/comun/pruebas/test_ataques_simulados.py`. Ejecutado en **PostgreSQL 16.2** en el equipo de Kevin.

| Ataque | Ejemplo de la guía | Qué se envió | Esperado | Resultado |
| --- | --- | --- | --- | --- |
| Inyección SQL | `' OR 1=1 --` | En el usuario y en la clave del login, en el asunto y la descripción de un ticket, en `?orden=` y en la URL | Bloqueado | ✅ 401 en el login; la carga se guarda como texto literal; las tablas quedan intactas; 404 en la URL |
| XSS | `<script>alert(1)</script>` | En el asunto y la descripción de una PQR, vista por el agente y por el cliente | Neutralizado | ✅ Se muestra escapado (`&lt;script&gt;`) y la CSP bloquea los scripts en línea |
| IDOR | `/usuario/1002` | Un intruso recorre `/api/pedidos/<id>/`, `/api/tickets/<id>/`, `/pedidos/<id>/` y `/pqr/<id>/` | Autorizado | ✅ 404 en todo lo ajeno; 200 solo en lo propio |
| Divulgación de información | `/error?debug=true` | `?debug=true` en cuatro rutas y un error interno forzado | Sin datos sensibles | ✅ Ni traceback, ni rutas, ni `settings`, ni datos de la BD; el login no revela si el usuario existe |
| Fuerza bruta de login | múltiples intentos | 5 claves erradas y luego la correcta, por la API y por la web | Limitado | ✅ 429 «Demasiados intentos»; no se crea sesión |

**¿La prueba de SQLi detecta de verdad una inyección?** Como el ORM ya protegía, las pruebas pasaron desde la primera ejecución. Para comprobar que no pasan «por casualidad», se metió a propósito un login vulnerable (SQL armado con f-string) y se corrieron de nuevo:

```
FAIL: test_el_codigo_no_arma_sql_a_mano        ['cuentas/servicios.py:43'] != []
FAIL: test_login_con_or_1_1_no_entra  (usuario="' OR 1=1 --")             200 != 401
FAIL: test_login_con_or_1_1_no_entra  (clave="' OR 1=1 --")                200 != 401
FAIL: test_login_con_or_1_1_no_entra  (usuario="ana@example.com' OR 1=1 --") 200 != 401
```

Con el código vulnerable, `' OR 1=1 --` sí entraba (200), y las pruebas lo detectaron. Después se restauró el código original.

Otras pruebas de seguridad del proyecto:

- `test_seguridad.py`: hallazgos de la auditoría (25 pruebas).
- `test_auditoria_y_limites.py`: registro de eventos y límite de peticiones (9 pruebas).
- `test_interfaz.py`: la web, con CSRF, roles y redirección abierta (15 pruebas).

### 2.1 Resultado de la ejecución completa

| Entorno | Resultado |
| --- | --- |
| **PostgreSQL 16.2**, Django 5.2.18, Python 3.10 (equipo de Kevin) | **134 pruebas OK**, incluida la de concurrencia de HU-08 (un agente 200, el otro 409) |
| PostgreSQL 16, Django 6.1.2, Python 3.12 (nube) | 134 pruebas OK |
| Cobertura | **95 %** (umbral del CI: 85 %) |

Salida completa: [`evidencia/semana-13-ejecucion-postgresql.txt`](evidencia/semana-13-ejecucion-postgresql.txt).

## 3. Pipeline de CI con seguridad (guía §7)

`.github/workflows/ci.yml` tiene dos jobs que corren en cada push y PR:

| Etapa | Herramienta | Quality gate | Resultado local |
| --- | --- | --- | --- |
| Build | `pip install`, `makemigrations --check` | No faltan migraciones | ✅ |
| Pruebas unitarias y de seguridad | `manage.py test` contra **PostgreSQL 15** (servicio del CI) | Todas pasan | ✅ 134/134 |
| Cobertura | `coverage report --fail-under=85` | Cobertura mínima alcanzada | ✅ 95 % |
| Configuración de despliegue | `check --deploy` con `HTTPS=true` | Sin errores | ✅ (solo W021, HSTS preload: decisión consciente) |
| Análisis estático (SAST) | `bandit --severity-level medium` | Sin hallazgos de severidad media o alta | ✅ 0 medios o altos; 5 bajos en datos de prueba (`clave123` en las fábricas, `subprocess` en una prueba) |
| Dependencias | `pip-audit -r requirements.txt` | Sin vulnerabilidades conocidas | ✅ |
| Secretos | `gitleaks git` (todo el historial) + regla propia para `SECRET_KEY` de Django | Sin secretos expuestos | ✅; las 3 claves históricas (H12) están en la lista de permitidos de `.gitleaks.toml` mientras el equipo decide (DT-13). Una clave nueva hace fallar el pipeline (comprobado) |

Las reglas de gitleaks que vienen por defecto **no** detectaban las claves `django-insecure-…`. Por eso se agregó la regla `django-secret-key`.

## 4. OWASP Top 10

Ver el [modelo de amenazas §4](modelo-amenazas.md#4-owasp-top-10-2021-cómo-queda-el-proyecto). Resumen:

- **Controladas:** A01 a A09. Siguen con riesgo residual A02 (depende de servir el sitio por HTTPS), A07 (no hay MFA) y A09 (no hay alertas automáticas).
- **No aplica:** A10 (SSRF), porque el sistema no hace peticiones salientes.

## 5. Errores comunes evitados (guía §9)

| Error | Cómo se evita aquí |
| --- | --- |
| Confiar en validaciones solo del cliente | El navegador valida, pero el servidor vuelve a validar todo |
| Concatenar SQL | Solo ORM, con una prueba guardia contra SQL crudo |
| Mensajes de error detallados | `DEBUG=False` y 500 genérico |
| Contraseñas en texto plano | Hash PBKDF2; las claves nunca van al registro |
| «Asumir» que está seguro | 134 pruebas, prueba de mutación de SQLi y quality gates en el CI |
| No registrar eventos críticos | `EventoAuditoria` |
| Ignorar dependencias vulnerables | `pip-audit` en el CI |

## 6. Cómo reproducir

```bash
docker compose up -d db          # PostgreSQL 15
cd tests
pip install -r requirements-dev.txt
coverage run manage.py test -v 2 && coverage report --fail-under=85
cd .. && bandit -r tests -x tests/venv,tests/.venv,tests/staticfiles --severity-level medium
pip-audit -r tests/requirements.txt
```
