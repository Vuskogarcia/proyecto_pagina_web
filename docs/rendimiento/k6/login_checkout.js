// Escenario 2 · Inicio de sesión + checkout (HU-01 y HU-04).
//
// Cada usuario virtual (VU) usa su propio cliente perf_cliente_<VU>, creado
// por preparar_datos.py. Cada iteración:
//   1. GET  /api/sesion/   → cookie csrftoken (cookie jar propio del VU)
//   2. POST /api/sesion/   → inicia sesión (verifica Argon2id); Django rota
//                            la sesión y el token CSRF, así que se relee.
//   3. POST /api/pedidos/  → checkout con 1–2 productos y datos de envío
//   4. DELETE /api/sesion/ → cierra sesión
//
// Límites de la aplicación que el diseño respeta:
//   - 30 escrituras por minuto por usuario autenticado (checkout + salir =
//     2 por iteración) → cada iteración dura al menos PAUSA_S segundos
//     (4 s por defecto = máx. 15 iteraciones/min = 30 escrituras/min).
//   - 5 inicios de sesión FALLIDOS bloquean usuario + IP: la clave es
//     correcta; si algo falla, el check lo muestra.

import http from 'k6/http';
import { check, sleep, fail } from 'k6';
import { BASE_URL, ESTADISTICAS, UMBRALES, carga, tokenCsrf, cabecerasJson } from './config.js';

const CLAVE = __ENV.PERF_CLAVE || 'Rendimiento#2026';
const PAUSA_S = Number(__ENV.PAUSA_S || 4);
const ENVIO = { nombre: 'Cliente de carga', direccion: 'Calle 1 # 2-3', ciudad: 'Bogotá', telefono: '+57 300 000 0000' };

export const options = {
  ...carga(20, '60s'),
  thresholds: UMBRALES.login_checkout,
  summaryTrendStats: ESTADISTICAS,
  tags: { escenario: 'login_checkout' },
};

export function setup() {
  const productos = http.get(`${BASE_URL}/api/productos/`).json('productos')
    .filter((p) => p.nombre.startsWith('Rendimiento '));
  if (productos.length === 0) throw new Error('Faltan los productos de carga: corre preparar_datos.py');
  return { ids: productos.map((p) => p.id) };
}

export default function (datos) {
  const inicio = Date.now();
  const usuario = `perf_cliente_${__VU}@example.com`;

  http.get(`${BASE_URL}/api/sesion/`, { tags: { nombre: 'csrf' } });
  const login = http.post(`${BASE_URL}/api/sesion/`, JSON.stringify({ usuario, clave: CLAVE }),
    { headers: cabecerasJson(tokenCsrf(http)), tags: { nombre: 'login' } });
  if (!check(login, { 'login 200': (r) => r.status === 200 })) {
    fail(`login ${usuario} → ${login.status} ${login.body}`);
  }

  // Dos productos al azar (pueden repetirse: el servicio suma cantidades).
  const items = [0, 1].map(() => ({
    id_producto: datos.ids[Math.floor(Math.random() * datos.ids.length)],
    cantidad: 1,
  }));
  const pedido = http.post(`${BASE_URL}/api/pedidos/`, JSON.stringify({ items, envio: ENVIO }),
    { headers: cabecerasJson(tokenCsrf(http)), tags: { nombre: 'checkout' } });
  check(pedido, {
    'checkout 201': (r) => r.status === 201,
    'checkout trae código PED-': (r) => r.status === 201 && r.json('codigo').startsWith('PED-'),
  });

  const salir = http.del(`${BASE_URL}/api/sesion/`, null,
    { headers: cabecerasJson(tokenCsrf(http)), tags: { nombre: 'logout' } });
  check(salir, { 'logout 204': (r) => r.status === 204 });

  const transcurrido = (Date.now() - inicio) / 1000;
  sleep(Math.max(0, PAUSA_S - transcurrido));
}
