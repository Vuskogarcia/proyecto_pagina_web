from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def pesos(valor):
    """150000 -> "$150.000" (pesos colombianos, sin decimales)."""
    try:
        numero = Decimal(valor)
    except Exception:
        return valor
    return "$" + f"{numero:,.0f}".replace(",", ".")


@register.filter
def inicial(texto):
    return (str(texto).strip()[:1] or "?").upper()
