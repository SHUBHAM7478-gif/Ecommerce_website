

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from .forms import RegisterForm, LoginForm, UserUpdateForm, ProfileUpdateForm
from .models import Profile


# ===========================================================================
# MODEL + SIGNAL TESTS
# ===========================================================================
class ProfileModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='john', password='TestPass123!', email='john@example.com'
        )

    def test_profile_auto_created_on_user_creation(self):
        """Creating a User must create a linked Profile automatically."""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertEqual(self.user.profile.user, self.user)

    def test_profile_is_created_by_createsuperuser(self):
        """Signals must also fire for superusers."""
        admin = User.objects.create_superuser(
            username='admin', password='TestPass123!', email='admin@example.com'
        )
        self.assertTrue(Profile.objects.filter(user=admin).exists())

    def test_profile_str(self):
        self.assertEqual(str(self.user.profile), "john's profile")

    def test_profile_full_name_falls_back_to_username(self):
        self.assertEqual(self.user.profile.full_name, 'john')

    def test_profile_full_name_uses_real_name(self):
        self.user.first_name = 'John'
        self.user.last_name = 'Doe'
        self.user.save()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.full_name, 'John Doe')

    def test_has_address_false_when_incomplete(self):
        self.user.profile.address = '123 Main St'
        self.user.profile.save()
        self.assertFalse(self.user.profile.has_address)

    def test_has_address_true_when_complete(self):
        p = self.user.profile
        p.address = '123 Main St'
        p.city = 'Mumbai'
        p.postal_code = '400001'
        p.country = 'India'
        p.save()
        self.assertTrue(p.has_address)

    def test_profile_deleted_when_user_deleted(self):
        """CASCADE: deleting the user removes the profile."""
        self.user.delete()
        self.assertEqual(Profile.objects.count(), 0)


# ===========================================================================
# REGISTER FORM TESTS
# ===========================================================================
class RegisterFormTests(TestCase):

    def _valid_data(self, **overrides):
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }
        data.update(overrides)
        return data

    def test_valid_registration(self):
        form = RegisterForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username='newuser', password='TestPass123!')
        form = RegisterForm(data=self._valid_data())
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_duplicate_email_rejected(self):
        User.objects.create_user(
            username='other', password='TestPass123!', email='new@example.com'
        )
        form = RegisterForm(data=self._valid_data())
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_duplicate_email_case_insensitive(self):
        User.objects.create_user(
            username='other', password='TestPass123!', email='NEW@EXAMPLE.COM'
        )
        form = RegisterForm(data=self._valid_data())
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_password_mismatch_rejected(self):
        form = RegisterForm(data=self._valid_data(password2='DifferentPass123!'))
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_short_password_rejected(self):
        form = RegisterForm(data=self._valid_data(password1='abc', password2='abc'))
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)

    def test_numeric_only_password_rejected(self):
        form = RegisterForm(data=self._valid_data(password1='12345678', password2='12345678'))
        self.assertFalse(form.is_valid())

    def test_reserved_username_rejected(self):
        form = RegisterForm(data=self._valid_data(username='admin'))
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_email_is_lowercased(self):
        form = RegisterForm(data=self._valid_data(email='New@Example.com'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['email'], 'new@example.com')

    def test_form_creates_user(self):
        form = RegisterForm(data=self._valid_data())
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.username, 'newuser')
        self.assertTrue(user.check_password('StrongPass123!'))
        self.assertTrue(hasattr(user, 'profile'))


# ===========================================================================
# LOGIN FORM TESTS
# ===========================================================================
class LoginFormTests(TestCase):

    def test_valid_login_form(self):
        form = LoginForm(data={'username': 'john', 'password': 'x'})
        self.assertTrue(form.is_valid())

    def test_missing_username(self):
        form = LoginForm(data={'username': '', 'password': 'x'})
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_missing_password(self):
        form = LoginForm(data={'username': 'john', 'password': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)

    def test_remember_me_optional(self):
        form = LoginForm(data={'username': 'john', 'password': 'x'})
        self.assertTrue(form.is_valid())
        self.assertFalse(form.cleaned_data['remember_me'])


# ===========================================================================
# USER UPDATE FORM TESTS
# ===========================================================================
class UserUpdateFormTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='john', password='TestPass123!', email='john@example.com'
        )

    def test_valid_update(self):
        form = UserUpdateForm(
            data={'first_name': 'John', 'last_name': 'Doe', 'email': 'john@example.com'},
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_can_keep_own_email(self):
        """Editing profile without changing email must not trigger duplicate error."""
        form = UserUpdateForm(
            data={'first_name': 'John', 'last_name': 'Doe', 'email': 'john@example.com'},
            instance=self.user,
        )
        self.assertTrue(form.is_valid())

    def test_cannot_take_someone_elses_email(self):
        User.objects.create_user(
            username='other', password='TestPass123!', email='other@example.com'
        )
        form = UserUpdateForm(
            data={'first_name': 'John', 'last_name': 'Doe', 'email': 'other@example.com'},
            instance=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_short_first_name_rejected(self):
        form = UserUpdateForm(
            data={'first_name': 'J', 'last_name': 'Doe', 'email': 'john@example.com'},
            instance=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)

    def test_blank_names_allowed(self):
        form = UserUpdateForm(
            data={'first_name': '', 'last_name': '', 'email': 'john@example.com'},
            instance=self.user,
        )
        self.assertTrue(form.is_valid())


# ===========================================================================
# PROFILE UPDATE FORM TESTS
# ===========================================================================
class ProfileUpdateFormTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='john', password='TestPass123!')
        self.profile = self.user.profile

    def _data(self, **overrides):
        data = {
            'phone': '+91 98765 43210',
            'bio': 'Hello world',
            'address': '123 Main St',
            'city': 'Mumbai',
            'postal_code': '400001',
            'country': 'India',
        }
        data.update(overrides)
        return data

    def test_valid_profile_update(self):
        form = ProfileUpdateForm(data=self._data(), instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_phone_characters(self):
        form = ProfileUpdateForm(data=self._data(phone='abc#123'), instance=self.profile)
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_short_phone_rejected(self):
        form = ProfileUpdateForm(data=self._data(phone='123'), instance=self.profile)
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_blank_phone_allowed(self):
        form = ProfileUpdateForm(data=self._data(phone=''), instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)

    def test_postal_code_digits_only(self):
        form = ProfileUpdateForm(data=self._data(postal_code='ABC123'), instance=self.profile)
        self.assertFalse(form.is_valid())
        self.assertIn('postal_code', form.errors)

    def test_postal_code_with_hyphen_allowed(self):
        form = ProfileUpdateForm(data=self._data(postal_code='400-001'), instance=self.profile)
        self.assertTrue(form.is_valid(), form.errors)

    def test_oversized_avatar_rejected(self):
        big = SimpleUploadedFile(
            'big.jpg', b'x' * (3 * 1024 * 1024), content_type='image/jpeg'
        )
        form = ProfileUpdateForm(
            data=self._data(),
            files={'avatar': big},
            instance=self.profile,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_bio_too_long_rejected(self):
        form = ProfileUpdateForm(data=self._data(bio='x' * 600), instance=self.profile)
        self.assertFalse(form.is_valid())
        self.assertIn('bio', form.errors)


# ===========================================================================
# VIEW TESTS
# ===========================================================================
class RegisterViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:register')

    def test_register_page_renders(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'accounts/register.html')

    def test_successful_registration_redirects_to_login(self):
        res = self.client.post(self.url, {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertRedirects(res, reverse('accounts:login'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_invalid_registration_rerenders_form(self):
        res = self.client.post(self.url, {
            'username': '',
            'email': 'bad',
            'password1': 'x',
            'password2': 'y',
        })
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'accounts/register.html')
        self.assertFalse(User.objects.exists())


class LoginViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:login')
        self.user = User.objects.create_user(
            username='john', password='TestPass123!'
        )

    def test_login_page_renders(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'accounts/login.html')

    def test_successful_login_redirects(self):
        res = self.client.post(self.url, {
            'username': 'john',
            'password': 'TestPass123!',
        })
        self.assertEqual(res.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_invalid_credentials_show_error(self):
        res = self.client.post(self.url, {
            'username': 'john',
            'password': 'wrongpass',
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Invalid username or password')

    def test_next_parameter_honored(self):
        res = self.client.post(self.url + '?next=/cart/', {
            'username': 'john',
            'password': 'TestPass123!',
            'next': '/cart/',
        })
        self.assertRedirects(res, '/cart/')


class LogoutViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:logout')
        self.user = User.objects.create_user(
            username='john', password='TestPass123!'
        )

    def test_logout_get_shows_confirmation_page(self):
        self.client.login(username='john', password='TestPass123!')
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'accounts/logout.html')

    def test_logout_post_logs_user_out(self):
        self.client.login(username='john', password='TestPass123!')
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)


class ProfileViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:profile')
        self.user = User.objects.create_user(
            username='john', password='TestPass123!', email='john@example.com'
        )

    def test_profile_requires_login(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/accounts/login/', res.url)

    def test_profile_page_renders_for_logged_in_user(self):
        self.client.login(username='john', password='TestPass123!')
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'accounts/profile.html')

    def test_profile_update_saves_user_and_profile(self):
        self.client.login(username='john', password='TestPass123!')
        res = self.client.post(self.url, {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'phone': '+91 98765 43210',
            'bio': 'Hello',
            'address': '123 Main St',
            'city': 'Mumbai',
            'postal_code': '400001',
            'country': 'India',
        })
        self.assertEqual(res.status_code, 302)
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.profile.city, 'Mumbai')