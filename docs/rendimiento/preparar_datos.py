"""Prepara la base de datos de las pruebas de carga (Historias 08 y 09).

Crea, si no existen:
- PERF_USUARIOS clientes `perf_cliente_<n>@example.com` (n = 1..N), uno por
  usuario virtual de k6, todos con la clave PERF_CLAVE. Así cada VU tiene su
  propio límite de escrituras (30 por minuto por usuario).
- 10 productos «Rendimiento <n>» con stock alto, para que el checkout no
  se quede sin stock durante la prueba.

Y deja el stock de esos productos otra vez en PERF_STOCK.

Uso (desde la carpeta tests/, con el .env o las variables DB_* apuntando a
la base de rendimiento; ver instrucciones.md):

    python ../docs/rendimiento/preparar_datos.py
"""

import os
import sys
from decimal import Decimal
from pathlib import Path

DIR_TESTS = Path(__file__).resolve().parents[2] / "tests"
sys.path.insert(0, str(DIR_TESTS))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from catalogo.models import Producto  # noqa: E402

USUARIOS = int(os.getenv("PERF_USUARIOS", "50"))
CLAVE = os.getenv("PERF_CLAVE", "Rendimiento#2026")
STOCK = int(os.getenv("PERF_STOCK", "1000000"))


def main():
    Usuario = get_user_model()
    creados = 0
    for n in range(1, USUARIOS + 1):
        email = f"perf_cliente_{n}@example.com"
        if not Usuario.objects.filter(username=email).exists():
            Usuario.objects.create_user(username=email, email=email, password=CLAVE)
            creados += 1
    for n in range(1, 11):
        producto, _ = Producto.objects.get_or_create(
            nombre=f"Rendimiento {n}",
            defaults={"descripcion": f"Producto de la prueba de carga {n}",
                      "precio": Decimal(1000 * n), "stock": STOCK, "activo": True},
        )
        producto.stock, producto.activo = STOCK, True
        producto.save(update_fields=["stock", "activo"])
    ids = list(Producto.objects.filter(nombre__startswith="Rendimiento ").values_list("pk", flat=True))
    print(f"base={django.db.connection.settings_dict['NAME']} usuarios_nuevos={creados} "
          f"usuarios_perf={Usuario.objects.filter(username__startswith='perf_cliente_').count()} "
          f"productos_perf={ids}")


if __name__ == "__main__":
    main()
