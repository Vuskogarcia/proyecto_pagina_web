"""Costo de UN hash Argon2id por configuración, sin servidor ni concurrencia
(Historia 10). Complementa la prueba de carga de registro: aísla cuánto
cuesta el hash en sí en esta máquina.

Uso (con el venv del proyecto):  python docs/rendimiento/argon2_micro.py [repeticiones]
"""

import os
import platform
import statistics
import sys
import time

from importlib.metadata import version
from argon2.low_level import Type, hash_secret

CONFIGURACIONES = [
    # nombre, time_cost, memory_cost (KiB), parallelism
    ("django-por-defecto", 2, 102400, 8),
    ("rfc9106-segunda-recomendada", 3, 65536, 4),
    ("owasp-minima", 2, 19456, 1),
]


def percentil(valores, p):
    ordenados = sorted(valores)
    k = (len(ordenados) - 1) * p / 100
    bajo, alto = int(k), min(int(k) + 1, len(ordenados) - 1)
    return ordenados[bajo] + (ordenados[alto] - ordenados[bajo]) * (k - bajo)


def main():
    repeticiones = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    print(f"# fecha={time.strftime('%Y-%m-%d %H:%M:%S %z')} python={platform.python_version()} "
          f"argon2-cffi={version('argon2-cffi')} cpu_logicos={os.cpu_count()} so={platform.platform()}")
    print(f"# {repeticiones} hashes por configuración, secuenciales, misma clave y sal aleatoria")
    print("configuracion,t,m_kib,p,p50_ms,p95_ms,p99_ms,min_ms,max_ms")
    for nombre, t, m, p in CONFIGURACIONES:
        hash_secret(b"calentamiento", os.urandom(16), t, m, p, 32, Type.ID)
        tiempos = []
        for _ in range(repeticiones):
            inicio = time.perf_counter()
            hash_secret(b"Carga-Registro#2026", os.urandom(16), t, m, p, 32, Type.ID)
            tiempos.append((time.perf_counter() - inicio) * 1000)
        print(f"{nombre},{t},{m},{p},{statistics.median(tiempos):.1f},{percentil(tiempos, 95):.1f},"
              f"{percentil(tiempos, 99):.1f},{min(tiempos):.1f},{max(tiempos):.1f}")


if __name__ == "__main__":
    main()
