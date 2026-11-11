# Pruebas de carga con k6: cómo reproducirlas

Módulo 7, Historias 08, 09 y 10. Resultados: [`resultados-2026-11-11.md`](resultados-2026-11-11.md) · Argon2id: [`argon2.md`](argon2.md).

## 1. Qué se mide y con qué umbrales

| Escenario | Script | Qué hace cada iteración | Carga por defecto |
| --- | --- | --- | --- |
| Catálogo (HU-02) | [`k6/catalogo.js`](k6/catalogo.js) | `GET /api/productos/` y el detalle de un producto al azar; pausa 0,5 s | 20 VUs · 60 s |
| Login + checkout (HU-01, HU-04) | [`k6/login_checkout.js`](k6/login_checkout.js) | token CSRF → login → checkout de 2 productos → logout; cada iteración dura ≥ 4 s | 20 VUs · 60 s |
| Registro (HU-01) | [`k6/registro.js`](k6/registro.js) | token CSRF → registro con email único; pausa 1 s | 10 VUs · 60 s |

Umbrales ([`k6/config.js`](k6/config.js)). Se fijaron **antes** de la primera ejecución y no se movieron después:

| Métrica | Umbral | Por qué |
| --- | --- | --- |
| Peticiones fallidas (cada escenario) | < 1 % | Una tienda no puede perder pedidos o registros bajo carga normal |
| p95 lista y detalle del catálogo | < 300 ms | Navegación: debe sentirse inmediata |
| p95 inicio de sesión | < 1000 ms | Incluye verificar Argon2id, que es lento a propósito |
| p95 checkout | < 800 ms | Transacción con bloqueo de filas (`select_for_update`) |
| p95 registro | < 1500 ms | Incluye calcular Argon2id y validar la contraseña |

Si un umbral no se cumple, k6 termina con código **99** y `medir.sh` lo anota al final del `.txt`.

## 2. Cómo respetan los scripts los límites de la aplicación

| Límite de la aplicación | Valor | Cómo lo maneja la prueba |
| --- | --- | --- |
| Escrituras por usuario autenticado (`LIMITE_ESCRITURAS_POR_MINUTO`) | 30 por minuto | Login + checkout: cada VU usa **su propio** usuario (`perf_cliente_<VU>`) y cada iteración dura al menos 4 s. Hace 2 escrituras (checkout y logout), o sea máximo 30 por minuto. El login es anónimo y no cuenta. |
| Registros por IP (`LIMITE_REGISTROS_POR_HORA`) | 10 por hora | Todos los VUs salen de `127.0.0.1`, así que con el límite real la prueba mediría 429. **Solo para el servidor de la prueba** se sube con `LIMITE_REGISTROS_POR_HORA=1000000`. El límite real lo sigue verificando `LimiteDePeticionesTests`. |
| Bloqueo por intentos de login fallidos | 5 fallos por usuario + IP | La clave de los usuarios de carga es correcta; un fallo de login aborta la iteración y se ve en el check `login 200`. |
| Tamaño del cuerpo | 64 KB | Los cuerpos de la prueba son de pocos cientos de bytes. |
| Lecturas (GET) | sin límite | El catálogo no necesita ajustes. |

Sesión y CSRF: k6 guarda las cookies por VU. Antes de cada POST se hace `GET /api/sesion/` (entrega la cookie `csrftoken`) y el token va en la cabecera `X-CSRFToken`. Después del login Django **rota** la sesión y el token, por eso el script lo vuelve a leer antes del checkout.

Email único por iteración (registro): `k6_vu<VU>_it<ITER>_<timestamp>_<uuid>@example.com`, con `crypto.randomUUID()` de k6.

## 3. Pasos

Requisitos: Docker con el contenedor de PostgreSQL del proyecto, el venv de `tests/` y k6.

```bash
# 0. k6. En Windows: winget install k6 (pide permisos de administrador).
#    Sin permisos: descargar el .zip oficial de https://github.com/grafana/k6/releases,
#    verificar el SHA-256 con el archivo *-checksums.txt y usar k6.exe directamente.
#    Esta medición usó k6 v2.3.0 (zip oficial, SHA-256 verificado).

# 1. Dependencias de la prueba (waitress: servidor WSGI que funciona en Windows)
pip install -r docs/rendimiento/requirements-rendimiento.txt

# 2. PostgreSQL y la base aparte para la carga (no se ensucia la de desarrollo)
docker compose up -d db
docker exec ecom_postgres_db psql -U admin -d postgres -c "CREATE DATABASE ecommerce_rendimiento OWNER admin;"

# 3. Servidor de la prueba, en otra terminal (desde tests/)
cd tests
DB_NAME=ecommerce_rendimiento DEBUG=False LOG_LEVEL=WARNING LIMITE_REGISTROS_POR_HORA=1000000 \
  waitress-serve --listen=127.0.0.1:8001 --threads=8 config.wsgi:application
#    (para medir otra configuración de Argon2id, agrega ARGON2_TIME_COST,
#     ARGON2_MEMORY_COST y ARGON2_PARALLELISM aquí Y en el paso 4)

# 4. Cada escenario (desde la raíz del repo). medir.sh reinicia la base, corre
#    preparar_datos.py, ejecuta k6 y guarda la salida cruda:
export K6=/ruta/a/k6
bash docs/rendimiento/medir.sh final catalogo
bash docs/rendimiento/medir.sh final login_checkout
bash docs/rendimiento/medir.sh final registro
#    Opcional: VUS=50 DURACION=2m bash docs/rendimiento/medir.sh prueba catalogo

# 5. Costo de un hash Argon2id, sin servidor (Historia 10)
python docs/rendimiento/argon2_micro.py 50
```

Salida: `docs/rendimiento/resultados/<fecha>/<etiqueta>-<escenario>.txt` (consola de k6 más la cabecera y el pie que escribe `medir.sh`) y `.json` (`--summary-export`). En el JSON, `"thresholds": {"p(95)<300": false}` significa que el umbral **no** se superó, es decir, que se cumplió.

La última línea de cada `.txt` (`# hash_usuarios_de_carga: argon2$argon2id$v=19$m=…,t=…,p=…|N`) dice con qué parámetros de Argon2id quedaron los usuarios de la prueba. Así se comprueba que el servidor usó la configuración que se quería medir. Solo se guarda el encabezado del hash, nunca la sal ni el hash.

## 4. Lo que estas pruebas no dicen

- **El generador de carga y el servidor están en la misma máquina** y compiten por la CPU. Los tiempos son un límite superior de lo que mediría un k6 en otra máquina.
- Un solo proceso de waitress. Con varios procesos, el límite de peticiones en memoria deja de ser global (DT-12).
- PostgreSQL corre en Docker Desktop (WSL 2), no en un servidor dedicado.
- Son 60 s por escenario: sirven para comparar configuraciones, no son una prueba de resistencia (*soak*) ni de estrés hasta el punto de quiebre.
