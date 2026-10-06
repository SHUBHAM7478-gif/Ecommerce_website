"""
Forms for the accounts app.


  - RegisterForm        → new user signup (extends UserCreationForm)
  - LoginForm           → plain username/password form
  - UserUpdateForm      → edit User fields (first_name, last_name, email)
  - ProfileUpdateForm   → edit Profile fields (phone, avatar, bio, address...)

"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from .models import Profile


# ---------------------------------------------------------------------------
# REGISTER
# ---------------------------------------------------------------------------
class RegisterForm(UserCreationForm):
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        }),
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username',
                'autocomplete': 'username',
            }),
        }
        labels = {
            'username': 'Username',
            'email': 'Email',
        }

    def clean_email(self):
        """Reject duplicate emails (case-insensitive)."""
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        """Trim whitespace and reject reserved names."""
        username = self.cleaned_data.get('username', '').strip()
        reserved = {'admin', 'root', 'superuser', 'system'}
        if username.lower() in reserved:
            raise ValidationError("This username is reserved.")
        return username


# ---------------------------------------------------------------------------
# LOGIN
# ---------------------------------------------------------------------------
class LoginForm(forms.Form):
    """
    Simple login form. Authentication itself happens in the view via
    django.contrib.auth.authenticate(). This form only validates that the
    fields are non-empty.
    """

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your username',
            'autocomplete': 'username',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        }),
    )
    remember_me = forms.BooleanField(required=False)


# ---------------------------------------------------------------------------
# USER UPDATE (first_name, last_name, email)
# ---------------------------------------------------------------------------
class UserUpdateForm(forms.ModelForm):
    """Edit fields that live on django.contrib.auth.models.User."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@example.com',
        }),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'John',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Doe',
            }),
        }

    def clean_email(self):
        """Reject duplicates, but allow keeping the current email."""
        email = self.cleaned_data.get('email', '').strip().lower()
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("This email is already in use.")
        return email

    def clean_first_name(self):
        name = self.cleaned_data.get('first_name', '').strip()
        if name and len(name) < 2:
            raise ValidationError("First name is too short.")
        return name

    def clean_last_name(self):
        name = self.cleaned_data.get('last_name', '').strip()
        if name and len(name) < 2:
            raise ValidationError("Last name is too short.")
        return name


# ---------------------------------------------------------------------------
# PROFILE UPDATE (phone, avatar, bio, address)
# ---------------------------------------------------------------------------
class ProfileUpdateForm(forms.ModelForm):
    """Edit fields that live on accounts.models.Profile."""

    class Meta:
        model = Profile
        fields = ['phone', 'avatar', 'bio', 'address', 'city', 'postal_code', 'country']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91 98765 43210',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Tell us a bit about yourself...',
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '123 Main Street',
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mumbai',
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '400001',
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'India',
            }),
            'avatar': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }

    def clean_phone(self):
        """Accept digits, spaces, +, - and parentheses only."""
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            allowed = set('0123456789 +-()')
            if not all(ch in allowed for ch in phone):
                raise ValidationError("Phone number contains invalid characters.")
            digits = sum(c.isdigit() for c in phone)
            if digits < 7:
                raise ValidationError("Phone number is too short.")
        return phone

    def clean_postal_code(self):
        """Must be digits (spaces and hyphens allowed as separators)."""
        pc = self.cleaned_data.get('postal_code', '').strip()
        if pc:
            cleaned = pc.replace('-', '').replace(' ', '')
            if not cleaned.isdigit():
                raise ValidationError("Postal code must contain digits only.")
        return pc

    def clean_avatar(self):
        """Reject files larger than 2 MB."""
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'size'):
            if avatar.size > 2 * 1024 * 1024:
                raise ValidationError("Avatar must be smaller than 2 MB.")
        return avatar

    def clean_bio(self):
        """Enforce the 500-char limit defined on the model."""
        bio = self.cleaned_data.get('bio', '').strip()
        if len(bio) > 500:
            raise ValidationError("Bio cannot exceed 500 characters.")
        return bio