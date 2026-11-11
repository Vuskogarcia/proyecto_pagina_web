# Rotación de la `SECRET_KEY` y cierre de DT-13

Módulo 7, Historia 05. Cierra la deuda **DT-13** (hallazgo H12, recomendación ADL-08).

## 1. Decisión sobre las claves del historial (DT-13)

| Dato | Valor |
| --- | --- |
| Fecha | 2026-11-11 |
| Decidido por | Kevin García (pedido explícito de cerrar DT-13 en esta sesión) |
| Hechos verificados | El historial de Git tiene **3** claves `django-insecure-…`, agregadas en los commits `1a2b391` (2026-08-13), `2c19daf` (2026-09-16) y `83705b3` (2026-10-12). El código las quitó en `7afe94d` (PR #15). Se comprobó con `git log --all -p -S django-insecure` y la misma regex de gitleaks. |
| Lo que **no** se puede verificar desde el repositorio | Si alguna de esas claves llegó a usarse en un servidor desplegado. |

**Decisión: revocar (rotar), no purgar el historial.**

| Opción | Qué logra | Por qué se descarta o se elige |
| --- | --- | --- |
| Purgar el historial (`git filter-repo` + push forzado) | Quita las claves de los commits de GitHub | **Se descarta.** No vuelve secreta una clave que ya fue pública: siguen en los clones de cada integrante, en las referencias de los PR que guarda GitHub y en cualquier fork o caché. Además reescribe todos los hashes de commit, rompe las referencias de la documentación (incluido este archivo) y obliga a todo el equipo a volver a clonar. |
| Revocar las claves | Ninguna de las tres puede volver a usarse | **Se elige.** Es lo que de verdad elimina el riesgo: una `SECRET_KEY` filtrada solo es peligrosa mientras algún entorno la use. |

Cómo queda aplicada la decisión:

1. `settings.py` guarda la **huella SHA-256** de las tres claves (no las claves) en `_CLAVES_REVOCADAS_SHA256` y **no arranca** si la `SECRET_KEY` coincide con una de ellas, **con o sin `DEBUG`**.
2. La prueba `comun/pruebas/test_m7_h05_claves_revocadas.py` lee las claves del historial real de Git y comprueba que:
   - cada clave del historial tiene su huella en la lista de revocadas;
   - con cada una, `settings` falla con `DEBUG=False` (y también con `DEBUG=True`), y el error no repite la clave;
   - una clave nueva sí arranca.
3. El CI hace checkout con todo el historial (`fetch-depth: 0`) para que esa prueba corra allí y no se salte.
4. `.gitleaks.toml` mantiene las 3 claves en su lista de permitidos **por commit**: ya están revocadas, y cualquier clave nueva sigue haciendo fallar el pipeline.

Riesgo residual: si alguna de las tres claves se usó en un entorno desplegado, las sesiones, los enlaces firmados y los tokens de restablecimiento de ese entorno pudieron ser forjables mientras se usó. Ese entorno debe aplicar el procedimiento de la §2. **No hay evidencia en el repositorio de un despliegue.**

## 2. Procedimiento de rotación

Úsalo cuando una clave se filtre (Git, captura de pantalla, chat, log) o cuando alguien con acceso deje el equipo.

### Paso 1 · Revocar

1. Calcula la huella de la clave comprometida, sin escribirla en ningún archivo versionado:
   ```bash
   python -c "import hashlib,getpass; print(hashlib.sha256(getpass.getpass('Clave: ').encode()).hexdigest())"
   ```
2. Agrega la huella a `_CLAVES_REVOCADAS_SHA256` en `tests/config/settings.py`, con un comentario de dónde se filtró.
3. Si la clave quedó en un commit, agrega ese commit a la lista de permitidos de `.gitleaks.toml` **solo después** de revocarla.

### Paso 2 · Generar una clave nueva

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

Debe tener al menos 50 caracteres y no empezar por `django-insecure` (`settings.py` lo exige con `DEBUG=False`).

### Paso 3 · Actualizar `.env` y el CI

| Dónde | Qué hacer |
| --- | --- |
| `tests/.env` de cada integrante | Reemplazar `SECRET_KEY=`. El archivo está en `.gitignore`: **nunca** se sube. |
| Servidor desplegado (si hay) | Cambiar la variable de entorno `SECRET_KEY` y reiniciar el proceso. |
| CI (GitHub Actions) | No requiere cambios: el job genera una clave aleatoria en cada ejecución (paso «Generar SECRET_KEY de la ejecución»). Si en el futuro hay despliegue desde el CI, la clave va en *Settings → Secrets and variables → Actions*, nunca en el YAML. |

Efecto esperado: al cambiar la clave se invalidan todas las sesiones abiertas (los usuarios vuelven a iniciar sesión) y los enlaces firmados con la clave anterior.

### Paso 4 · Verificar

```bash
cd tests
python manage.py check                                                    # arranca con la clave nueva
python manage.py test comun.pruebas.test_m7_h05_claves_revocadas          # la vieja queda rechazada
```

Y en el CI: el job `seguridad` (gitleaks) en verde y el job `pruebas` sin pruebas saltadas en `test_m7_h05_claves_revocadas`.
