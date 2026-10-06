"""
Helpers for the cart app.

`_get_cart(request)` is the single source of truth for "which cart does
this request belong to". Logged-in users → cart tied to User. Guests →
cart tied to session_key.
"""

from .models import Cart


def _get_cart(request):
    """
    Return the current cart, creating it if needed.
    - If the user is authenticated, use the cart linked to their account.
    - Otherwise, use the cart linked to the session_key (guest cart).
    """
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return cart

    # Guest — make sure a session exists
    if not request.session.session_key:
        request.session.create()

    cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key)
    return cart


def merge_session_cart_into_user(request):
    """
    Called right after login: if the guest had a session cart, move its
    items into the user's cart (or just relink the cart).
    """
    if not request.session.session_key:
        return

    try:
        guest_cart = Cart.objects.get(session_key=request.session.session_key)
    except Cart.DoesNotExist:
        return

    user_cart, _ = Cart.objects.get_or_create(user=request.user)

    for item in guest_cart.items.all():
        existing = user_cart.items.filter(product=item.product).first()
        if existing:
            existing.quantity += item.quantity
            existing.save()
        else:
            item.cart = user_cart
            item.save()

    guest_cart.delete()