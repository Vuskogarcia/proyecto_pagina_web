#!/usr/bin/env bash
# Ejecuta un escenario de k6 contra el servidor de rendimiento y guarda la
# salida cruda como evidencia (Historias 08, 09 y 10).
#
#   uso: bash docs/rendimiento/medir.sh <etiqueta> <escenario> [--sin-reset]
#     etiqueta : nombre de la corrida, p. ej. "antes" o "argon2-ligera"
#     escenario: catalogo | login_checkout | registro
#
# Antes de cada escenario deja la base `ecommerce_rendimiento` limpia
# (borrar, crear, migrar y preparar_datos.py) para que todas las corridas
# arranquen con los mismos datos. El servidor (waitress) debe estar
# corriendo aparte contra esa base: ver instrucciones.md §3.
#
# Variables: K6 (ruta a k6), BASE_URL, VUS, DURACION, PYTHON.
set -euo pipefail

etiqueta="${1:?falta la etiqueta}"
escenario="${2:?falta el escenario}"
raiz="$(cd "$(dirname "$0")/../.." && pwd)"
K6="${K6:-k6}"
PYTHON="${PYTHON:-$raiz/tests/venv/Scripts/python.exe}"
[ -x "$PYTHON" ] || PYTHON="$raiz/tests/venv/bin/python"
fecha="$(date +%F)"
salida="$raiz/docs/rendimiento/resultados/$fecha"
mkdir -p "$salida"
base="$salida/$etiqueta-$escenario"

if [ "${3:-}" != "--sin-reset" ]; then
  docker exec ecom_postgres_db psql -q -U admin -d postgres \
    -c "DROP DATABASE IF EXISTS ecommerce_rendimiento WITH (FORCE);" \
    -c "CREATE DATABASE ecommerce_rendimiento OWNER admin;"
  (cd "$raiz/tests" && DB_NAME=ecommerce_rendimiento "$PYTHON" manage.py migrate --noinput -v 0 \
    && DB_NAME=ecommerce_rendimiento "$PYTHON" "$raiz/docs/rendimiento/preparar_datos.py")
fi

{
  echo "# escenario=$escenario etiqueta=$etiqueta inicio=$(date '+%F %T %z')"
  echo "# k6=$("$K6" version | head -1)"
  echo "# BASE_URL=${BASE_URL:-http://127.0.0.1:8001} VUS=${VUS:-por defecto} DURACION=${DURACION:-por defecto}"
} > "$base.txt"

set +e
(cd "$raiz/docs/rendimiento/k6" && "$K6" run --quiet --no-color --summary-export "$base.json" "$escenario.js") >> "$base.txt" 2>&1
codigo=$?
set -e
# Qué parámetros de Argon2id usó de verdad el servidor: se guarda solo el
# encabezado del hash (algoritmo, variante, versión y m,t,p), nunca la sal
# ni el hash.
docker exec ecom_postgres_db psql -At -U admin -d ecommerce_rendimiento -c \
  "SELECT split_part(password,'\$',1)||'\$'||split_part(password,'\$',2)||'\$'||split_part(password,'\$',3)||'\$'||split_part(password,'\$',4) AS parametros, count(*)
     FROM auth_user WHERE username LIKE 'k6\\_%' OR username LIKE 'perf\\_cliente\\_%' GROUP BY 1;" \
  | sed 's/^/# hash_usuarios_de_carga: /' >> "$base.txt"
echo "# fin=$(date '+%F %T %z') codigo_salida_k6=$codigo (99 = algún umbral no se cumplió)" >> "$base.txt"
echo "Guardado: $base.txt y $base.json (k6 salió con $codigo)"
