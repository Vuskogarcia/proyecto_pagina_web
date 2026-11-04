"""Cabeceras de seguridad que Django no pone por sí solo."""

# La interfaz no usa scripts ni estilos en línea, así que la política puede
# ser estricta: todo sale del mismo origen. Mitiga XSS: aunque un ticket
# trajera <script>, el navegador no lo ejecutaría.
CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)

PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=()"


class CabecerasDeSeguridadMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)
        # El admin de Django trae su propio JS; se le deja fuera de la CSP.
        if not request.path.startswith("/admin/"):
            respuesta.setdefault("Content-Security-Policy", CSP)
        respuesta.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        if request.path.startswith("/api/"):
            respuesta.setdefault("Cache-Control", "no-store")
        return respuesta
