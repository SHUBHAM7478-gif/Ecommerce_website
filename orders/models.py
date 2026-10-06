"""
Models for the orders app.

Covers:
  - Order       → one customer order (shipping details + status + totals)
  - OrderItem   → line items belonging to an order

Design notes:
  - `OrderItem.price` is a *snapshot* of the product's price at checkout time.
    This is critical: if the product's price changes later, past orders
    must still show what the customer actually paid.
  - Stock is decremented in the *view* (inside a transaction.atomic block),
    not here — so models stay data-only.
  - `status` uses choices + a status property so templates can render a badge
    with the right colour without any logic in the template.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from store.models import Product


# ---------------------------------------------------------------------------
# ORDER
# ---------------------------------------------------------------------------
class Order(models.Model):
    # ---------- Status choices ----------
    STATUS_PENDING    = 'Pending'
    STATUS_PROCESSING = 'Processing'
    STATUS_SHIPPED    = 'Shipped'
    STATUS_DELIVERED  = 'Delivered'
    STATUS_CANCELLED  = 'Cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING,    'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_SHIPPED,    'Shipped'),
        (STATUS_DELIVERED,  'Delivered'),
        (STATUS_CANCELLED,  'Cancelled'),
    ]

    # ---------- Owner ----------
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        help_text="Null if the order was placed by a now-deleted user.",
    )

    # ---------- Contact & shipping (mirrors CheckoutForm) ----------
    full_name   = models.CharField(max_length=150)
    email       = models.EmailField()
    address     = models.CharField(max_length=250)
    city        = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country     = models.CharField(max_length=100)

    # ---------- Payment ----------
    payment_method = models.CharField(
        max_length=20,
        default='cod',
        choices=[
            ('cod',  'Cash on Delivery'),
            ('card', 'Card / UPI'),
        ],
    )
    paid = models.BooleanField(default=False)

    # ---------- Status ----------
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    # ---------- Timestamps ----------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Order #{self.pk:06d} — {self.full_name}"

    def get_absolute_url(self):
        return reverse('orders:order_detail', kwargs={'order_id': self.pk})

    # ---------- Totals ----------
    def get_total(self):
        """Sum of all item subtotals. Called from templates as `order.get_total`."""
        return sum((item.subtotal for item in self.items.all()), Decimal('0.00'))

    @property
    def total(self):
        """Alias — handy for Python code that prefers a property."""
        return self.get_total()

    @property
    def item_count(self):
        """Total number of physical units in the order."""
        return sum(item.quantity for item in self.items.all())

    # ---------- Status helpers (used by the timeline template) ----------
    @property
    def is_pending(self):
        return self.status == self.STATUS_PENDING

    @property
    def is_shipped(self):
        return self.status == self.STATUS_SHIPPED

    @property
    def is_delivered(self):
        return self.status == self.STATUS_DELIVERED

    @property
    def is_cancelled(self):
        return self.status == self.STATUS_CANCELLED

    @property
    def can_be_cancelled(self):
        """Business rule: only pending / processing orders can be cancelled."""
        return self.status in (self.STATUS_PENDING, self.STATUS_PROCESSING)

    # ---------- Convenience ----------
    @property
    def shipping_summary(self):
        return f"{self.city}, {self.country}"

    @property
    def number(self):
        """Human-friendly order number: #000123."""
        return f"#{self.pk:06d}"


# ---------------------------------------------------------------------------
# ORDER ITEM
# ---------------------------------------------------------------------------
class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        help_text="May be null if the product was later deleted from the catalog.",
    )

    # Snapshot of the product's name + price at checkout time.
    # Storing the name here means deleted products still display properly.
    product_name = models.CharField(max_length=200)
    price        = models.DecimalField(max_digits=10, decimal_places=2)

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        ordering = ['id']

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"

    @property
    def subtotal(self):
        return self.price * self.quantity