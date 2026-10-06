"""
Tests for the orders app.

Coverage:
  - Model-level: totals, snapshots, deletion safety (SET_NULL)
  - Forms: CheckoutForm validation, OrderStatusForm rules
  - Views: checkout flow (empty cart, stock, atomicity), success,
           history, detail (owner vs staff vs stranger)
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from store.models import Category, Product
from cart.models import Cart, CartItem
from cart.utils import _get_cart

from .forms import CheckoutForm, OrderStatusForm
from .models import Order, OrderItem


# ===========================================================================
# BASE MIXIN
# ===========================================================================
class OrdersTestBase(TestCase):
    """Shared setup: one user, one category, one product."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='john', password='pass1234', email='john@example.com',
        )
        self.other = User.objects.create_user(
            username='jane', password='pass1234',
        )
        self.staff = User.objects.create_user(
            username='admin', password='pass1234', is_staff=True,
        )

        self.cat = Category.objects.create(name='Books')
        self.product = Product.objects.create(
            category=self.cat, name='Django Book',
            price=Decimal('100'), stock=10,
        )

        self.checkout_url = reverse('orders:checkout')

    def _login(self, user=None):
        self.client.login(username=(user or self.user).username, password='pass1234')

    def _add_to_cart(self, quantity=1, product=None):
        product = product or self.product
        cart = _get_cart(self.client.session and self.client.get('/').wsgi_request) \
            if False else None
        # Simpler: use the client to POST to cart:add
        self.client.post(
            reverse('cart:add', args=[product.id]),
            {'quantity': quantity},
        )

    def _valid_checkout_payload(self, **overrides):
        data = {
            'full_name':   'John Doe',
            'email':       'john@example.com',
            'address':     '123 Main Street',
            'city':        'Mumbai',
            'postal_code': '400001',
            'country':     'India',
            'payment_method': 'cod',
        }
        data.update(overrides)
        return data


# ===========================================================================
# MODEL TESTS
# ===========================================================================
class OrderModelTests(OrdersTestBase):

    def test_order_str(self):
        order = Order.objects.create(
            user=self.user, full_name='John Doe', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
        )
        self.assertIn('John Doe', str(order))
        self.assertIn(f"{order.pk:06d}", str(order))

    def test_number_property(self):
        order = Order.objects.create(
            user=self.user, full_name='J', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
        )
        self.assertEqual(order.number, f"#{order.pk:06d}")

    def test_get_total_empty(self):
        order = Order.objects.create(
            user=self.user, full_name='J', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
        )
        self.assertEqual(order.get_total(), Decimal('0.00'))

    def test_get_total_with_items(self):
        order = Order.objects.create(
            user=self.user, full_name='J', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
        )
        OrderItem.objects.create(
            order=order, product=self.product, product_name=self.product.name,
            price=Decimal('100'), quantity=2,
        )
        OrderItem.objects.create(
            order=order, product=self.product, product_name=self.product.name,
            price=Decimal('50'), quantity=3,
        )
        self.assertEqual(order.get_total(), Decimal('350.00'))

    def test_item_count(self):
        order = Order.objects.create(
            user=self.user, full_name='J', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
        )
        OrderItem.objects.create(
            order=order, product=self.product, product_name=self.product.name,
            price=Decimal('100'), quantity=2,
        )
        OrderItem.objects.create(
            order=order, product=self.product, product_name=self.product.name,
            price=Decimal('50'), quantity=3,
        )
        self.assertEqual(order.item_count, 5)

    def test_item_subtotal(self):
        order = Order.objects.create(
            user=self.user, full_name='J', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
        )
        item = OrderItem.objects.create(
            order=order, product=self.product, product_name=self.product.name,
            price=Decimal('100'), quantity=3,
        )
        self.assertEqual(item.subtotal, Decimal('300'))

    def test_default_status_is_pending(self):
        order = Order.objects.create(
            user=self.user, full_name='J', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
        )
        self.assertEqual(order.status, Order.STATUS_PENDING)
        self.assertTrue(order.is_pending)

    def test_can_be_cancelled(self):
        order = Order.objects.create(
            user=self.user, full_name='J', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
        )
        self.assertTrue(order.can_be_cancelled)
        order.status = Order.STATUS_DELIVERED
        order.save()
        self.assertFalse(order.can_be_cancelled)

    def test_price_snapshot_preserved_after_product_change(self):
        order = Order.objects.create(
            user=self.user, full_name='J', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
        )
        item = OrderItem.objects.create(
            order=order, product=self.product, product_name=self.product.name,
            price=Decimal('100'), quantity=1,
        )
        self.product.price = Decimal('999')
        self.product.save()
        item.refresh_from_db()
        self.assertEqual(item.price, Decimal('100'))

    def test_order_item_survives_product_deletion(self):
        order = Order.objects.create(
            user=self.user, full_name='J', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
        )
        item = OrderItem.objects.create(
            order=order, product=self.product, product_name='Django Book',
            price=Decimal('100'), quantity=1,
        )
        self.product.delete()
        item.refresh_from_db()
        self.assertIsNone(item.product)
        self.assertEqual(item.product_name, 'Django Book')


# ===========================================================================
# CHECKOUT FORM TESTS
# ===========================================================================
class CheckoutFormTests(TestCase):

    def _valid_data(self, **overrides):
        data = {
            'full_name':   'John Doe',
            'email':       'john@example.com',
            'address':     '123 Main Street',
            'city':        'Mumbai',
            'postal_code': '400001',
            'country':     'India',
        }
        data.update(overrides)
        return data

    def test_valid(self):
        form = CheckoutForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_short_full_name_rejected(self):
        form = CheckoutForm(data=self._valid_data(full_name='J'))
        self.assertFalse(form.is_valid())
        self.assertIn('full_name', form.errors)

    def test_short_address_rejected(self):
        form = CheckoutForm(data=self._valid_data(address='abc'))
        self.assertFalse(form.is_valid())
        self.assertIn('address', form.errors)

    def test_non_digit_postal_code_rejected(self):
        form = CheckoutForm(data=self._valid_data(postal_code='ABC123'))
        self.assertFalse(form.is_valid())
        self.assertIn('postal_code', form.errors)

    def test_postal_code_with_hyphen_allowed(self):
        form = CheckoutForm(data=self._valid_data(postal_code='400-001'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_email_lowercased(self):
        form = CheckoutForm(data=self._valid_data(email='John@Example.com'))
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['email'], 'john@example.com')


# ===========================================================================
# ORDER STATUS FORM TESTS
# ===========================================================================
class OrderStatusFormTests(OrdersTestBase):

    def setUp(self):
        super().setUp()
        self.order = Order.objects.create(
            user=self.user, full_name='J', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
            status=Order.STATUS_PENDING,
        )

    def test_valid_change(self):
        form = OrderStatusForm(
            data={'status': Order.STATUS_SHIPPED}, instance=self.order,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_delivered_cannot_revert(self):
        self.order.status = Order.STATUS_DELIVERED
        self.order.save()
        form = OrderStatusForm(
            data={'status': Order.STATUS_PENDING}, instance=self.order,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('status', form.errors)

    def test_cancelled_is_final(self):
        self.order.status = Order.STATUS_CANCELLED
        self.order.save()
        form = OrderStatusForm(
            data={'status': Order.STATUS_SHIPPED}, instance=self.order,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('status', form.errors)


# ===========================================================================
# VIEW TESTS — CHECKOUT
# ===========================================================================
class CheckoutViewTests(OrdersTestBase):

    def test_checkout_requires_login(self):
        res = self.client.get(self.checkout_url)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/accounts/login/', res.url)

    def test_empty_cart_redirects(self):
        self._login()
        res = self.client.get(self.checkout_url)
        self.assertRedirects(res, reverse('store:product_list'))

    def test_checkout_page_renders_with_cart(self):
        self._login()
        self._add_to_cart(quantity=2)
        res = self.client.get(self.checkout_url)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'orders/checkout.html')

    def test_successful_checkout_creates_order(self):
        self._login()
        self._add_to_cart(quantity=2)
        res = self.client.post(self.checkout_url, self._valid_checkout_payload())
        self.assertEqual(res.status_code, 302)

        order = Order.objects.get(user=self.user)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().quantity, 2)
        self.assertEqual(order.items.first().price, Decimal('100'))

    def test_checkout_decrements_stock(self):
        self._login()
        self._add_to_cart(quantity=3)
        self.client.post(self.checkout_url, self._valid_checkout_payload())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 7)

    def test_checkout_clears_cart(self):
        self._login()
        self._add_to_cart(quantity=2)
        self.client.post(self.checkout_url, self._valid_checkout_payload())
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 0)

    def test_checkout_with_insufficient_stock_rolls_back(self):
        self._login()
        self._add_to_cart(quantity=5)
        # Someone else buys almost everything
        self.product.stock = 2
        self.product.save()

        res = self.client.post(self.checkout_url, self._valid_checkout_payload())
        # No order should be created
        self.assertEqual(Order.objects.filter(user=self.user).count(), 0)
        # Stock unchanged
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        # Cart still has items
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)

    def test_invalid_payload_rerenders(self):
        self._login()
        self._add_to_cart(quantity=1)
        res = self.client.post(self.checkout_url, self._valid_checkout_payload(email=''))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'orders/checkout.html')
        self.assertEqual(Order.objects.count(), 0)


# ===========================================================================
# VIEW TESTS — SUCCESS
# ===========================================================================
class OrderSuccessViewTests(OrdersTestBase):

    def _make_order(self, user=None):
        return Order.objects.create(
            user=user or self.user, full_name='J', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
        )

    def test_requires_login(self):
        order = self._make_order()
        res = self.client.get(reverse('orders:order_success', args=[order.id]))
        self.assertEqual(res.status_code, 302)

    def test_owner_can_view(self):
        self._login()
        order = self._make_order()
        res = self.client.get(reverse('orders:order_success', args=[order.id]))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'orders/order_success.html')

    def test_stranger_redirected(self):
        self._login(self.other)
        order = self._make_order()
        res = self.client.get(reverse('orders:order_success', args=[order.id]))
        self.assertRedirects(res, reverse('orders:order_history'))

    def test_staff_can_view_any_order(self):
        self._login(self.staff)
        order = self._make_order()
        res = self.client.get(reverse('orders:order_success', args=[order.id]))
        self.assertEqual(res.status_code, 200)


# ===========================================================================
# VIEW TESTS — HISTORY
# ===========================================================================
class OrderHistoryViewTests(OrdersTestBase):

    def test_requires_login(self):
        res = self.client.get(reverse('orders:order_history'))
        self.assertEqual(res.status_code, 302)

    def test_lists_only_own_orders(self):
        Order.objects.create(
            user=self.user, full_name='Mine', email='m@e.com',
            address='x', city='y', postal_code='1', country='z',
        )
        Order.objects.create(
            user=self.other, full_name='Theirs', email='t@e.com',
            address='x', city='y', postal_code='1', country='z',
        )
        self._login()
        res = self.client.get(reverse('orders:order_history'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Mine')
        self.assertNotContains(res, 'Theirs')

    def test_empty_state(self):
        self._login()
        res = self.client.get(reverse('orders:order_history'))
        self.assertContains(res, 'No orders yet')


# ===========================================================================
# VIEW TESTS — DETAIL
# ===========================================================================
class OrderDetailViewTests(OrdersTestBase):

    def _make_order(self, user=None):
        return Order.objects.create(
            user=user or self.user, full_name='J', email='j@e.com',
            address='x', city='y', postal_code='1', country='z',
        )

    def test_owner_can_view(self):
        self._login()
        order = self._make_order()
        res = self.client.get(reverse('orders:order_detail', args=[order.id]))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'orders/order_detail.html')

    def test_stranger_redirected(self):
        self._login(self.other)
        order = self._make_order()
        res = self.client.get(reverse('orders:order_detail', args=[order.id]))
        self.assertRedirects(res, reverse('orders:order_history'))

    def test_staff_can_view(self):
        self._login(self.staff)
        order = self._make_order()
        res = self.client.get(reverse('orders:order_detail', args=[order.id]))
        self.assertEqual(res.status_code, 200)

    def test_404_for_missing_order(self):
        self._login()
        res = self.client.get(reverse('orders:order_detail', args=[99999]))
        self.assertEqual(res.status_code, 404)