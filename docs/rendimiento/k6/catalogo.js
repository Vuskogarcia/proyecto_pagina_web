// Escenario 1 · Consulta del catálogo (HU-02), anónimo.
// Cada iteración: lista de productos y el detalle de uno al azar.
// Las lecturas (GET) no tienen límite de peticiones en la aplicación.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, ESTADISTICAS, UMBRALES, carga } from './config.js';

export const options = {
  ...carga(20, '60s'),
  thresholds: UMBRALES.catalogo,
  summaryTrendStats: ESTADISTICAS,
  tags: { escenario: 'catalogo' },
};

export function setup() {
  const respuesta = http.get(`${BASE_URL}/api/productos/`);
  const ids = respuesta.json('productos').map((p) => p.id);
  if (ids.length === 0) throw new Error('El catálogo está vacío: corre preparar_datos.py');
  return { ids };
}

export default function (datos) {
  const lista = http.get(`${BASE_URL}/api/productos/`, { tags: { nombre: 'catalogo_lista' } });
  check(lista, {
    'lista 200': (r) => r.status === 200,
    'lista trae productos': (r) => r.json('productos').length > 0,
  });

  const id = datos.ids[Math.floor(Math.random() * datos.ids.length)];
  const detalle = http.get(`${BASE_URL}/api/productos/${id}/`, { tags: { nombre: 'catalogo_detalle' } });
  check(detalle, { 'detalle 200': (r) => r.status === 200 });

  sleep(0.5); // tiempo de lectura de un usuario
}
