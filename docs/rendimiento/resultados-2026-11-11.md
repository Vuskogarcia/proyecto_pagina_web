# Resultados de las pruebas de carga · 2026-11-11

Módulo 7, Historias 08 y 09. Todos los números salen de las ejecuciones guardadas en [`resultados/2026-11-11/`](resultados/2026-11-11/) (salida cruda de k6, `.txt` y `.json`). Cómo repetirlas: [`instrucciones.md`](instrucciones.md).

## 1. Condiciones

| Dato | Valor |
| --- | --- |
| Fecha y hora | 2026-11-11, de 00:31 a 00:49 (America/Bogota) |
| Máquina | Intel Core Ultra 7 155H (22 CPU lógicas), 15,7 GB de RAM, Windows 11 Home 10.0.26200 |
| Servidor | **waitress 3.0.2**, 1 proceso, 8 hilos, `DEBUG=False`, `LOG_LEVEL=WARNING` |
| Aplicación | rama `feature/modulo7-rnf-y-rc`, Python 3.12.10, Django 6.1.2, psycopg2-binary 2.9.13, argon2-cffi 25.1.0 |
| Base de datos | PostgreSQL 15.19 en Docker Desktop (contenedor `ecom_postgres_db`), base `ecommerce_rendimiento` **reiniciada antes de cada escenario** (50 clientes de carga y 10 productos) |
| Generador de carga | k6 v2.3.0 en la **misma máquina** |
| Ajuste solo para la prueba | `LIMITE_REGISTROS_POR_HORA=1000000` (todos los VUs comparten la IP 127.0.0.1; ver `instrucciones.md` §2) |
| Otros procesos | El servidor de desarrollo (`runserver`, puerto 8000, base `ecommerce_db`) seguía abierto pero sin tráfico |

| Escenario | Usuarios virtuales | Duración | Pausa por iteración |
| --- | --- | --- | --- |
| Catálogo | 20 | 60 s | 0,5 s |
| Login + checkout | 20 | 60 s | la iteración dura ≥ 4 s |
| Registro | 10 | 60 s | 1 s |

## 2. Configuración final (Argon2id t=3, m=64 MiB, p=4)

Archivos: `final-catalogo`, `final-login_checkout`, `final-registro`. El servidor arrancó **sin** variables `ARGON2_*`, y el pie de cada archivo confirma `m=65536,t=3,p=4`.

| Petición | Peticiones | p50 | p95 | p99 | Umbral p95 | Errores | ¿Cumple? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Catálogo · lista | 2222 | 20,02 ms | 35,95 ms | 43,23 ms | < 300 ms | 0 de 4445 (0,00 %) en todo el escenario | ✅ |
| Catálogo · detalle | 2222 | 16,51 ms | 36,86 ms | 54,77 ms | < 300 ms | (incluido arriba) | ✅ |
| Inicio de sesión | 300 | 204,12 ms | 369,44 ms | 553,76 ms | < 1000 ms | 0 de 1201 (0,00 %) en todo el escenario | ✅ |
| Checkout | 300 | 177,58 ms | 302,60 ms | 387,31 ms | < 800 ms | (incluido arriba) | ✅ |
| Registro | 555 | 83,42 ms | 151,52 ms | 208,27 ms | < 1500 ms | 0 de 1110 (0,00 %) | ✅ |

Rendimiento observado: catálogo 73,4 peticiones/s; login + checkout 20,0 peticiones/s (300 iteraciones completas); registro 18,2 peticiones/s (555 cuentas creadas).

## 3. Línea base (antes de elegir Argon2id; t=2, m=100 MiB, p=8)

Archivos: `antes-catalogo`, `antes-login_checkout`, `antes-registro`. Es la misma aplicación con los parámetros de Argon2id que trae Django por defecto.

| Petición | Peticiones | p50 | p95 | p99 | Errores | ¿Cumple? |
| --- | --- | --- | --- | --- | --- | --- |
| Catálogo · lista | 2202 | 21,18 ms | 40,05 ms | 57,37 ms | 0 de 4405 | ✅ |
| Catálogo · detalle | 2202 | 20,23 ms | 38,91 ms | 70,20 ms | (incluido arriba) | ✅ |
| Inicio de sesión | 300 | 237,73 ms | 555,14 ms | 931,62 ms | 0 de 1201 | ✅ |
| Checkout | 300 | 199,24 ms | 366,78 ms | 556,19 ms | (incluido arriba) | ✅ |
| Registro | 552 | 89,10 ms | 155,55 ms | 201,36 ms | 0 de 1104 | ✅ |

## 4. ¿Hubo que corregir un cuello de botella? (punto 8)

**No.** Todos los umbrales se cumplieron desde la primera ejecución (línea base, §3), así que no hubo un antes y un después de una corrección de rendimiento. Para no fabricar una comparación, no se tocó código por rendimiento.

Lo que sí se observó, sin corregirlo:

- **DT-07 (N+1 en `Pedido.total()`)** sigue abierta. La respuesta del checkout recorre `pedido.items.all()` sin `prefetch_related`, más un acceso a `item.producto` por cada ítem. Con pedidos de 1 o 2 productos el costo no se nota: el p95 del checkout está muy por debajo de su umbral. Queda diferida en [`../triage-rc.md`](../triage-rc.md).
- **El checkout se vuelve más lento cuando el hash de contraseña es más costoso**, aunque el checkout no calcula ningún hash: p50 de 199 ms con t=2/m=100 MiB/p=8, 173 ms con t=3/m=64 MiB/p=4 y 142 ms con t=2/m=19 MiB/p=1 (`*-login_checkout.txt`). La explicación probable es que los logins del mismo escenario ocupan CPU e hilos de waitress. Es una **interpretación**: no se midió por separado.
- Las pausas entre iteraciones mantienen la carga moderada. El punto de quiebre del servidor **no** se buscó.
