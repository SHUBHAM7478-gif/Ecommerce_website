from django.test import TestCase
from django.utils.text import slugify
from decimal import Decimal
from .models import Category, Product
from .forms import ProductSearchForm, ProductForm


class CategoryModelTests(TestCase):

    def test_slug_auto_generated(self):
        cat = Category.objects.create(name='Electronics')
        self.assertEqual(cat.slug, 'electronics')

    def test_str(self):
        cat = Category.objects.create(name='Books')
        self.assertEqual(str(cat), 'Books')

    def test_product_count(self):
        cat = Category.objects.create(name='Toys')
        Product.objects.create(category=cat, name='Ball', price=10, stock=5)
        Product.objects.create(category=cat, name='Doll', price=20, stock=5)
        Product.objects.create(category=cat, name='Kite', price=5, stock=5, available=False)
        self.assertEqual(cat.product_count, 2)


class ProductModelTests(TestCase):

    def setUp(self):
        self.cat = Category.objects.create(name='Books')

    def test_slug_unique_on_collision(self):
        p1 = Product.objects.create(category=self.cat, name='Django Book', price=100, stock=5)
        p2 = Product.objects.create(category=self.cat, name='Django Book', price=100, stock=5)
        self.assertEqual(p1.slug, 'django-book')
        self.assertEqual(p2.slug, 'django-book-1')

    def test_is_on_sale_true(self):
        p = Product.objects.create(
            category=self.cat, name='X', price=100, discount_price=80, stock=5,
        )
        self.assertTrue(p.is_on_sale)
        self.assertEqual(p.current_price, Decimal('80'))

    def test_is_on_sale_false_when_no_discount(self):
        p = Product.objects.create(category=self.cat, name='Y', price=100, stock=5)
        self.assertFalse(p.is_on_sale)
        self.assertEqual(p.current_price, Decimal('100'))

    def test_discount_percent(self):
        p = Product.objects.create(
            category=self.cat, name='Z', price=100, discount_price=75, stock=5,
        )
        self.assertEqual(p.discount_percent, 25)

    def test_in_stock(self):
        p = Product.objects.create(category=self.cat, name='A', price=10, stock=0)
        self.assertFalse(p.in_stock)
        p.stock = 5
        p.save()
        self.assertTrue(p.in_stock)


class ProductSearchFormTests(TestCase):

    def test_valid_empty(self):
        form = ProductSearchForm(data={})
        self.assertTrue(form.is_valid())

    def test_price_range_valid(self):
        form = ProductSearchForm(data={'min_price': '10', 'max_price': '100'})
        self.assertTrue(form.is_valid())

    def test_price_range_inverted(self):
        form = ProductSearchForm(data={'min_price': '100', 'max_price': '10'})
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)


class ProductFormTests(TestCase):

    def setUp(self):
        self.cat = Category.objects.create(name='Misc')

    def test_discount_must_be_lower(self):
        form = ProductForm(data={
            'category': self.cat.id,
            'name': 'X',
            'description': 'desc',
            'price': '100',
            'discount_price': '150',
            'stock': 5,
            'available': True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_valid_product(self):
        form = ProductForm(data={
            'category': self.cat.id,
            'name': 'Y',
            'description': 'desc',
            'price': '100',
            'discount_price': '80',
            'stock': 5,
            'available': True,
        })
        self.assertTrue(form.is_valid(), form.errors)

class StoreViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name='Books')
        self.p1 = Product.objects.create(
            category=self.cat, name='Django Book', price=Decimal('100'), stock=5,
        )
        self.p2 = Product.objects.create(
            category=self.cat, name='Python Book', price=Decimal('200'), stock=0,
        )
        self.p3 = Product.objects.create(
            category=self.cat, name='Hidden', price=Decimal('50'), stock=5,
            available=False,
        )

    # ---------- home ----------
    def test_home_renders(self):
        res = self.client.get(reverse('store:home'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'store/home.html')
        self.assertContains(res, 'Django Book')

    def test_home_excludes_unavailable(self):
        res = self.client.get(reverse('store:home'))
        self.assertNotContains(res, 'Hidden')

    # ---------- product_list ----------
    def test_product_list_renders(self):
        res = self.client.get(reverse('store:product_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Django Book')
        self.assertContains(res, 'Python Book')
        self.assertNotContains(res, 'Hidden')

    def test_product_list_search(self):
        res = self.client.get(reverse('store:product_list'), {'q': 'Django'})
        self.assertContains(res, 'Django Book')
        self.assertNotContains(res, 'Python Book')

    def test_product_list_filter_by_price(self):
        res = self.client.get(reverse('store:product_list'), {'max_price': '150'})
        self.assertContains(res, 'Django Book')
        self.assertNotContains(res, 'Python Book')

    def test_product_list_filter_by_category(self):
        res = self.client.get(
            reverse('store:product_list'), {'category': self.cat.slug}
        )
        self.assertContains(res, 'Django Book')

    # ---------- product_detail ----------
    def test_product_detail_renders(self):
        res = self.client.get(
            reverse('store:product_detail', kwargs={'slug': self.p1.slug})
        )
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Django Book')

    def test_product_detail_404_for_unavailable(self):
        res = self.client.get(
            reverse('store:product_detail', kwargs={'slug': self.p3.slug})
        )
        self.assertEqual(res.status_code, 404)

    # ---------- staff views ----------
    def test_product_create_requires_login(self):
        res = self.client.get(reverse('store:product_create'))
        self.assertNotEqual(res.status_code, 200)  # redirected to login

    def test_product_create_works_for_staff(self):
        User.objects.create_superuser(username='admin', password='pass1234')
        self.client.login(username='admin', password='pass1234')
        res = self.client.post(reverse('store:product_create'), {
            'category': self.cat.id,
            'name': 'New Product',
            'description': 'desc',
            'price': '99.99',
            'stock': 10,
            'available': True,
        })
        self.assertEqual(res.status_code, 302)
        self.assertTrue(Product.objects.filter(name='New Product').exists())