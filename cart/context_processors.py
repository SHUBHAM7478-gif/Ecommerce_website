"""
Exposes `cart_count` to every template (used by navbar.html).
"""

from .utils import _get_cart


def cart_count(request):
    try:
        cart = _get_cart(request)
        return {'cart_count': cart.total_items if cart else 0}
    except Exception:
        return {'cart_count': 0}