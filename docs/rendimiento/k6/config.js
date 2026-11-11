// Configuración común de las pruebas de carga (Módulo 7, Historias 08 y 09).
//
// Los umbrales se fijaron ANTES de la primera ejecución, a partir del uso
// esperado (ver ../instrucciones.md §1). Un umbral que no se cumple hace
// que k6 termine con código distinto de 0.

export const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8001';

// Estadísticas que se guardan en el resumen: p50 (med), p95 y p99.
export const ESTADISTICAS = ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max', 'count'];

// Umbrales por tipo de petición (etiqueta `nombre` de cada request).
//   - Errores: menos del 1 % de peticiones fallidas en cada escenario.
//   - Lectura del catálogo: p95 < 300 ms.
//   - Inicio de sesión: p95 < 1000 ms (incluye verificar Argon2id a propósito).
//   - Checkout: p95 < 800 ms (transacción con bloqueo de filas).
//   - Registro: p95 < 1500 ms (incluye calcular Argon2id).
export const UMBRALES = {
  catalogo: {
    'http_req_failed{escenario:catalogo}': ['rate<0.01'],
    'http_req_duration{nombre:catalogo_lista}': ['p(95)<300'],
    'http_req_duration{nombre:catalogo_detalle}': ['p(95)<300'],
  },
  login_checkout: {
    'http_req_failed{escenario:login_checkout}': ['rate<0.01'],
    'http_req_duration{nombre:login}': ['p(95)<1000'],
    'http_req_duration{nombre:checkout}': ['p(95)<800'],
  },
  registro: {
    'http_req_failed{escenario:registro}': ['rate<0.01'],
    'http_req_duration{nombre:registro}': ['p(95)<1500'],
  },
};

// Carga por escenario. Se puede cambiar con variables de entorno sin
// tocar los scripts (VUS=..., DURACION=...).
export function carga(vusPorDefecto, duracionPorDefecto) {
  return {
    vus: Number(__ENV.VUS || vusPorDefecto),
    duration: __ENV.DURACION || duracionPorDefecto,
  };
}

// Lee el token CSRF de la cookie que Django entrega en GET /api/sesion/.
// k6 guarda las cookies por usuario virtual (cookie jar propio por VU).
export function tokenCsrf(http) {
  const cookies = http.cookieJar().cookiesForURL(`${BASE_URL}/api/sesion/`);
  return cookies.csrftoken ? cookies.csrftoken[0] : null;
}

export function cabecerasJson(token) {
  return { 'Content-Type': 'application/json', 'X-CSRFToken': token };
}

// El resumen crudo se guarda con las opciones de la línea de comandos
// (sin módulos remotos): --summary-export=<archivo>.json para el JSON y la
// salida de consola redirigida a <archivo>.txt. Ver ../instrucciones.md.
