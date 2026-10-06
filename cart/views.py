"""
Views for the cart app.

  - cart_detail        → show cart contents
  - add_to_cart        → add a product (or increment quantity)
  - update_cart_item   → change quantity or remove (qty=0)
  - remove_cart_item   → delete a row
  - clear_cart         → empty the whole cart
"""

from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_http_methods

from store.models import Product
from .forms import AddToCartForm, UpdateCartItemForm
from .models import CartItem
from .utils import _get_cart


# ---------------------------------------------------------------------------
# CART PAGE
# ---------------------------------------------------------------------------
def cart_detail(request):
    cart = _get_cart(request)

    # Build a list of (item, form) pairs so each row's form is bound with
    # the correct initial value — easier to loop in the template.
    rows = [
        {
            'item': item,
            'form': UpdateCartItemForm(
                initial={'quantity': item.quantity},
                cart_item=item,
            ),
        }
        for item in cart.items.select_related('product', 'product__category')
    ]

    return render(request, 'cart/cart_detail.html', {
        'cart': cart,
        'rows': rows,
    })


# ---------------------------------------------------------------------------
# ADD TO CART
# ---------------------------------------------------------------------------
@require_http_methods(["POST"])
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, available=True)
    form = AddToCartForm(request.POST, product=product)

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if form.is_valid():
        qty = form.cleaned_data['quantity']
        cart = _get_cart(request)

        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={'quantity': qty},
        )
        if not created:
            item.quantity += qty
            if item.quantity > product.stock:
                item.quantity = product.stock
            item.save()

        if is_ajax:
            return JsonResponse({
                'success': True,
                'cart_count': cart.total_items,
                'message': f"'{product.name}' added to cart",
            })

        messages.success(request, f"'{product.name}' added to your cart.")
    else:
        if is_ajax:
            return JsonResponse({
                'success': False,
                'error': 'Invalid quantity or out of stock.',
            }, status=400)
        messages.error(request, "Could not add that item to your cart.")

    return redirect(request.META.get('HTTP_REFERER', 'cart:detail'))

# ---------------------------------------------------------------------------
# UPDATE CART ITEM (quantity change or removal)
# ---------------------------------------------------------------------------
@require_http_methods(["POST"])
def update_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    form = UpdateCartItemForm(request.POST, cart_item=item)

    if form.is_valid():
        qty = form.cleaned_data['quantity']
        if qty == 0:
            item.delete()
            messages.info(request, "Item removed from cart.")
        else:
            item.quantity = qty
            item.save()
            messages.success(request, "Cart updated.")

    return redirect('cart:detail')


# ---------------------------------------------------------------------------
# REMOVE CART ITEM
# ---------------------------------------------------------------------------
@require_http_methods(["POST"])
def remove_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id)
    name = item.product.name
    item.delete()
    messages.info(request, f"'{name}' removed from your cart.")
    return redirect('cart:detail')


# ---------------------------------------------------------------------------
# CLEAR CART
# ---------------------------------------------------------------------------
@require_http_methods(["POST"])
def clear_cart(request):
    cart = _get_cart(request)
    cart.items.all().delete()
    messages.info(request, "Your cart is now empty.")
    return redirect('cart:detail')