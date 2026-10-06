from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal

from store.models import Category, Product
from .models import Cart, CartItem
from .forms import AddToCartForm, UpdateCartItemForm


class CartModelTests(TestCase):

    def setUp(self):
        self.cat = Category.objects.create(name='Books')
        self.product = Product.objects.create(
            category=self.cat, name='Django', price=Decimal('100'), stock=10,
        )
        self.user = User.objects.create_user(username='john', password='pass1234')
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_str(self):
        self.assertIn('john', str(self.cart))

    def test_cart_is_empty(self):
        self.assertTrue(self.cart.is_empty)

    def test_cart_totals(self):
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=3)
        self.assertEqual(self.cart.total_items, 3)
        self.assertEqual(self.cart.subtotal, Decimal('300'))

    def test_cart_item_subtotal_uses_discount(self):
        self.product.discount_price = Decimal('80')
        self.product.save()
        item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.assertEqual(item.subtotal, Decimal('160'))

    def test_exceeds_stock(self):
        item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=15)
        self.assertTrue(item.exceeds_stock)


class AddToCartFormTests(TestCase):

    def setUp(self):
        self.cat = Category.objects.create(name='Books')
        self.product = Product.objects.create(
            category=self.cat, name='X', price=Decimal('100'), stock=5,
        )

    def test_valid(self):
        form = AddToCartForm(data={'quantity': 3}, product=self.product)
        self.assertTrue(form.is_valid())

    def test_exceeds_stock(self):
        form = AddToCartForm(data={'quantity': 10}, product=self.product)
        self.assertFalse(form.is_valid())

    def test_zero_quantity(self):
        form = AddToCartForm(data={'quantity': 0}, product=self.product)
        self.assertFalse(form.is_valid())


class CartViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name='Books')
        self.product = Product.objects.create(
            category=self.cat, name='Django', price=Decimal('100'), stock=10,
        )

    def test_add_to_cart_as_guest(self):
        res = self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 2})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(CartItem.objects.count(), 1)
        self.assertEqual(CartItem.objects.first().quantity, 2)

    def test_add_to_cart_as_user(self):
        User.objects.create_user(username='john', password='pass1234')
        self.client.login(username='john', password='pass1234')
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 1})
        cart = Cart.objects.get(user__username='john')
        self.assertEqual(cart.total_items, 1)

    def test_add_again_increments(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 2})
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 3})
        self.assertEqual(CartItem.objects.first().quantity, 5)

    def test_update_quantity(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 2})
        item = CartItem.objects.first()
        self.client.post(reverse('cart:update', args=[item.id]), {'quantity': 5})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)

    def test_update_to_zero_removes_item(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 2})
        item = CartItem.objects.first()
        self.client.post(reverse('cart:update', args=[item.id]), {'quantity': 0})
        self.assertEqual(CartItem.objects.count(), 0)

    def test_remove_item(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 2})
        item = CartItem.objects.first()
        self.client.post(reverse('cart:remove', args=[item.id]))
        self.assertEqual(CartItem.objects.count(), 0)

    def test_clear_cart(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 2})
        self.client.post(reverse('cart:clear'))
        self.assertEqual(CartItem.objects.count(), 0)

    def test_cart_detail_renders(self):
        res = self.client.get(reverse('cart:detail'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'cart/cart_detail.html')
        self.assertContains(res, 'Your cart is empty')

    def test_cart_detail_shows_items(self):
        self.client.post(reverse('cart:add', args=[self.product.id]), {'quantity': 2})
        res = self.client.get(reverse('cart:detail'))
        self.assertContains(res, 'Django')
        self.assertContains(res, '200')