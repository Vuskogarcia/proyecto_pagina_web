"""Hash de contraseñas con Argon2id (Módulo 7, Historia 04).

Es el `Argon2PasswordHasher` de Django (que ya usa la variante Argon2id),
con los parámetros de costo tomados de settings en vez de fijos en el
código. Así se pueden medir y ajustar por entorno (Historia 10) sin tocar
el código: ARGON2_TIME_COST, ARGON2_MEMORY_COST (KiB) y ARGON2_PARALLELISM.

Si los parámetros cambian, Django vuelve a calcular el hash la próxima vez
que el usuario inicia sesión (`must_update`), igual que con los hashes
PBKDF2 existentes.
"""

from django.conf import settings
from django.contrib.auth.hashers import Argon2PasswordHasher


class Argon2idPasswordHasher(Argon2PasswordHasher):
    # Mismo identificador que el de Django ("argon2"): los hashes son
    # compatibles en ambos sentidos.

    @property
    def time_cost(self):
        return settings.ARGON2_TIME_COST

    @property
    def memory_cost(self):
        return settings.ARGON2_MEMORY_COST

    @property
    def parallelism(self):
        return settings.ARGON2_PARALLELISM
