// Escenario 3 · Registro de usuarios (HU-01) · Historias 09 y 10.
//
// Cada iteración registra una cuenta nueva con un email único: VU, número
// de iteración, marca de tiempo y un UUID aleatorio. Así una repetición de
// la prueba (o dos VUs a la vez) nunca chocan con «Ya existe una cuenta».
//
// Límite de la aplicación: 10 registros por hora por IP. Todos los VUs
// salen de 127.0.0.1, así que para medir hay que levantar el servidor con
// LIMITE_REGISTROS_POR_HORA alto (ver ../instrucciones.md). La prueba
// unitaria LimiteDePeticionesTests sigue verificando el límite real.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, ESTADISTICAS, UMBRALES, carga, tokenCsrf, cabecerasJson } from './config.js';

export const options = {
  ...carga(10, '60s'),
  thresholds: UMBRALES.registro,
  summaryTrendStats: ESTADISTICAS,
  tags: { escenario: 'registro' },
};

export function emailUnico() {
  return `k6_vu${__VU}_it${__ITER}_${Date.now()}_${crypto.randomUUID()}@example.com`;
}

export default function () {
  http.get(`${BASE_URL}/api/sesion/`, { tags: { nombre: 'csrf' } });
  const email = emailUnico();
  const registro = http.post(`${BASE_URL}/api/registro/`,
    JSON.stringify({ email, clave: 'Carga-Registro#2026', nombre: `VU ${__VU}` }),
    { headers: cabecerasJson(tokenCsrf(http)), tags: { nombre: 'registro' } });
  check(registro, {
    'registro 201': (r) => r.status === 201,
    // La API devuelve el email como `usuario` (el username es el email) y el rol.
    'registro crea un cliente con ese email': (r) => r.status === 201
      && r.json('usuario') === email && r.json('rol') === 'cliente',
  });
  sleep(1);
}
