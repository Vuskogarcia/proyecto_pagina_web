# Parámetros de Argon2id: medición y elección

Módulo 7, Historia 10. Condiciones de la máquina y del servidor: [`resultados-2026-11-11.md`](resultados-2026-11-11.md) §1. Salida cruda: [`resultados/2026-11-11/`](resultados/2026-11-11/).

## 1. Configuraciones medidas

| Configuración | t (iteraciones) | m (memoria) | p (hilos) | Origen |
| --- | --- | --- | --- | --- |
| **A. Django por defecto** | 2 | 102 400 KiB (100 MiB) | 8 | Valores de `Argon2PasswordHasher` en Django 6.1; fue la línea base |
| **B. RFC 9106, segunda recomendada** | 3 | 65 536 KiB (64 MiB) | 4 | RFC 9106 §4: la opción recomendada cuando no se pueden usar 2 GiB por hash |
| **C. OWASP mínima (más ligera)** | 2 | 19 456 KiB (19 MiB) | 1 | Configuración mínima de la *Password Storage Cheat Sheet* de OWASP |

Las tres son **Argon2id** (`argon2$argon2id$v=19$…`). Se eligen sin tocar código, con `ARGON2_TIME_COST`, `ARGON2_MEMORY_COST` (en KiB) y `ARGON2_PARALLELISM`. En cada corrida, el pie del `.txt` confirma con qué parámetros quedaron guardados los hashes.

## 2. Costo de un hash, sin servidor

`python docs/rendimiento/argon2_micro.py 50`: 50 hashes secuenciales por configuración. Salida cruda: [`argon2-micro.csv`](resultados/2026-11-11/argon2-micro.csv).

| Configuración | p50 | p95 | p99 | mín. | máx. |
| --- | --- | --- | --- | --- | --- |
| A. t=2, m=100 MiB, p=8 | 40,0 ms | 44,5 ms | 51,9 ms | 38,5 ms | 55,3 ms |
| B. t=3, m=64 MiB, p=4 | 42,2 ms | 46,1 ms | 47,3 ms | 40,1 ms | 47,7 ms |
| C. t=2, m=19 MiB, p=1 | 19,4 ms | 23,7 ms | 33,1 ms | 18,0 ms | 39,8 ms |

A y B cuestan casi lo mismo por hash: A usa más memoria y más hilos (8) por cada hash.

## 3. Registro de usuarios bajo carga (10 VUs · 60 s), dos corridas por configuración

| Configuración | Corrida | Cuentas creadas | p50 | p95 | p99 | Errores | Archivo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A. t=2, m=100 MiB, p=8 | 1 | 552 | 89,10 ms | 155,55 ms | 201,36 ms | 0 de 1104 | `antes-registro` |
| A. t=2, m=100 MiB, p=8 | 2 | 551 | 93,37 ms | 150,26 ms | 289,56 ms | 0 de 1102 | `argon2-django-r2-registro` |
| B. t=3, m=64 MiB, p=4 | 1 | 546 | 96,11 ms | 164,15 ms | 240,30 ms | 0 de 1092 | `argon2-rfc9106-r1-registro` |
| B. t=3, m=64 MiB, p=4 | 2 | 552 | 89,25 ms | 148,64 ms | 210,32 ms | 0 de 1104 | `argon2-rfc9106-r2-registro` |
| B (corrida final) | 3 | 555 | 83,42 ms | 151,52 ms | 208,27 ms | 0 de 1110 | `final-registro` |
| C. t=2, m=19 MiB, p=1 | 1 | 570 | 53,30 ms | 73,76 ms | 191,94 ms | 0 de 1140 | `argon2-owasp-r1-registro` |
| C. t=2, m=19 MiB, p=1 | 2 | 570 | 55,03 ms | 72,31 ms | 85,71 ms | 0 de 1140 | `argon2-owasp-r2-registro` |

## 4. Inicio de sesión + checkout bajo carga (20 VUs · 60 s), una corrida por configuración

El login verifica la clave con los mismos parámetros. Es la operación de Argon2id más frecuente en la tienda.

| Configuración | Login p50 | Login p95 | Login p99 | Checkout p95 | Errores | Archivo |
| --- | --- | --- | --- | --- | --- | --- |
| A. t=2, m=100 MiB, p=8 | 237,73 ms | 555,14 ms | 931,62 ms | 366,78 ms | 0 de 1201 | `antes-login_checkout` |
| B. t=3, m=64 MiB, p=4 | 212,28 ms | 366,44 ms | 463,64 ms | 332,72 ms | 0 de 1201 | `argon2-rfc9106-login_checkout` |
| B (corrida final) | 204,12 ms | 369,44 ms | 553,76 ms | 302,60 ms | 0 de 1201 | `final-login_checkout` |
| C. t=2, m=19 MiB, p=1 | 115,14 ms | 211,34 ms | 269,17 ms | 195,72 ms | 0 de 1201 | `argon2-owasp-login_checkout` |

## 5. Elección: **B · t=3, m=64 MiB, p=4** (RFC 9106, segunda recomendada)

Es el valor por defecto en `tests/config/settings.py`, y lo verifica `ParametrosDeProduccionTests` en `cuentas/pruebas/test_m7_h04_argon2.py`.

Justificación, con los datos de arriba:

1. **Cumple todos los umbrales con margen.** Registro p95 de 149–164 ms frente a un umbral de 1500 ms. Login p95 de 366–369 ms frente a 1000 ms. 0 errores en todas las corridas.
2. **Frente a A, la línea base:** el registro queda igual (las diferencias entre A y B, de 148 a 164 ms de p95, están dentro de la variación entre corridas de una misma configuración). En el login, B tuvo mejor cola: p95 366–369 ms contra 555 ms, y p99 464–554 ms contra 932 ms. Esa comparación tiene **una sola corrida de A**, así que es indicativa. Además, B pide 64 MiB por hash contra 100 MiB: con los 8 hilos del servidor ocupados en logins, el pico es de unos 512 MiB contra unos 800 MiB (cálculo a partir de los parámetros, no medido).
3. **Frente a C, la más ligera:** C es claramente más rápida (registro p95 ≈ 73 ms, login p95 ≈ 211 ms). Pero usa 19 MiB por hash, poco más de un cuarto de la memoria de B. La memoria es lo que encarece un ataque de fuerza bruta con GPU o ASIC sobre una base de datos robada. Como B ya cumple los umbrales con margen, no hay motivo de rendimiento para bajar a C.

Cuándo revisar la elección:

- Si el servidor de producción tiene menos de ~1 GB libre para la aplicación, o si hay más hilos o procesos, recalcula el pico de memoria (64 MiB × logins simultáneos).
- Si el p95 del login supera los 1000 ms con la carga real, C es la alternativa medida (sigue dentro de lo que recomienda OWASP).
- Cambiar los parámetros no rompe nada: los hashes existentes siguen sirviendo y Django los recalcula con los parámetros nuevos en el siguiente inicio de sesión (`must_update`). La migración PBKDF2 → Argon2id usa el mismo mecanismo y está probada en `test_un_hash_pbkdf2_existente_sirve_y_se_actualiza_a_argon2id_al_entrar`.
