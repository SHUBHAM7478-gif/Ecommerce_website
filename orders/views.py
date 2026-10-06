"""
Views for the orders app.

  - checkout        → show form + create order on POST (atomic)
  - order_success   → confirmation page after successful checkout
  - order_history   → list all orders for the logged-in user
  - order_detail    → full view of a single order (owner or staff)

Notes:
  - The checkout view wraps order creation, item creation, and stock
    decrement in `transaction.atomic()` so the whole thing is all-or-nothing.
  - `user` and `payment_method` are set server-side from the request,
    never trusted from POST.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from cart.utils import _get_cart
from store.models import Product

from .forms import CheckoutForm
from .models import Order, OrderItem


# ---------------------------------------------------------------------------
# CHECKOUT
# ---------------------------------------------------------------------------
@login_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    """
    GET  → render checkout page with form pre-filled from the user's profile.
    POST → validate, create Order + OrderItems atomically, decrement stock,
           clear the cart, redirect to success page.
    """
    cart = _get_cart(request)

    # Empty cart → nothing to check out
    if cart.is_empty:
        messages.warning(request, "Your cart is empty. Add something before checking out.")
        return redirect('store:product_list')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)

        if form.is_valid():
            # ---------- Pre-check stock BEFORE starting the transaction ----------
            # This avoids a partially-applied write and gives a clean error message.
            insufficient = []
            for cart_item in cart.items.select_related('product'):
                if cart_item.quantity > cart_item.product.stock:
                    insufficient.append(
                        f"'{cart_item.product.name}' (only {cart_item.product.stock} left)"
                    )

            if insufficient:
                messages.error(
                    request,
                    "Sorry, we can't fulfil these items: " + ", ".join(insufficient) +
                    ". Please adjust your cart."
                )
                return render(request, 'orders/checkout.html', {
                    'form': form,
                    'cart': cart,
                })

            # ---------- Everything is in stock → commit atomically ----------
            with transaction.atomic():
                order = form.save(commit=False)
                order.user = request.user
                order.payment_method = request.POST.get('payment_method', 'cod')
                order.save()

                for cart_item in cart.items.select_related('product'):
                    product = cart_item.product

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,          # snapshot
                        price=product.current_price,         # snapshot
                        quantity=cart_item.quantity,
                    )

                    product.stock -= cart_item.quantity
                    product.save(update_fields=['stock'])

                cart.items.all().delete()

            messages.success(request, f"Order #{order.pk:06d} placed successfully!")
            return redirect('orders:order_success', order_id=order.pk)

        else:
            messages.error(request, "Please fix the errors below.")

    else:
        # GET: pre-fill from user's name / email
        initial = {
            'full_name': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
        }
        form = CheckoutForm(initial=initial)

    return render(request, 'orders/checkout.html', {
        'form': form,
        'cart': cart,
    })


# ---------------------------------------------------------------------------
# ORDER SUCCESS
# ---------------------------------------------------------------------------
@login_required
def order_success(request, order_id):
    """
    Post-checkout confirmation page.
    Only the owner (or staff) can view it.
    """
    order = get_object_or_404(Order, pk=order_id)

    if order.user != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to view that order.")
        return redirect('orders:order_history')

    return render(request, 'orders/order_success.html', {'order': order})


# ---------------------------------------------------------------------------
# ORDER HISTORY
# ---------------------------------------------------------------------------
@login_required
def order_history(request):
    """List every order belonging to the logged-in user, with optional status filter."""
    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related('items__product')
        .order_by('-created_at')
    )

    status_filter = request.GET.get('status')
    if status_filter and status_filter in dict(Order.STATUS_CHOICES):
        orders = orders.filter(status=status_filter)

    return render(request, 'orders/order_history.html', {'orders': orders})


# ---------------------------------------------------------------------------
# ORDER DETAIL
# ---------------------------------------------------------------------------
@login_required
def order_detail(request, order_id):
    """
    Full detail view for a single order.
    Owner or staff only.
    """
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        pk=order_id,
    )

    if order.user != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to view that order.")
        return redirect('orders:order_history')

    return render(request, 'orders/order_detail.html', {'order': order})