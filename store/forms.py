"""
Forms for the store app.

Covers:
  - ProductSearchForm     → search + category + price filter (GET)
  - CategoryForm          → create/edit categories (admin-side)
  - ProductForm           → create/edit products (admin-side)

The customer-facing form is ProductSearchForm; the other two are
handy for building a staff dashboard later.
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import Product, Category, ProductImage


# ---------------------------------------------------------------------------
# SEARCH / FILTER (used on product_list.html)
# ---------------------------------------------------------------------------
class ProductSearchForm(forms.Form):
    """
    Search bar + category filter + price range.
    Uses GET (not POST) — so all fields are `required=False`.
    """

    q = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search products...',
        }),
    )

    category = forms.CharField(
        required=False,
        max_length=120,
    )

    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min ₹',
            'min': 0,
        }),
    )

    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max ₹',
            'min': 0,
        }),
    )

    def clean(self):
        cleaned = super().clean()
        mn = cleaned.get('min_price')
        mx = cleaned.get('max_price')
        if mn is not None and mx is not None and mn > mx:
            raise ValidationError("Minimum price cannot be greater than maximum price.")
        return cleaned


# ---------------------------------------------------------------------------
# CATEGORY FORM (for staff / future dashboard)
# ---------------------------------------------------------------------------
class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'image']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category name',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Short description (optional)',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        qs = Category.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("A category with this name already exists.")
        return name


# ---------------------------------------------------------------------------
# PRODUCT FORM (for staff / future dashboard)
# ---------------------------------------------------------------------------
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'category', 'name', 'description',
            'price', 'discount_price',
            'stock', 'image',
            'available', 'featured',
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Product name',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe the product...',
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0,
            }),
            'discount_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0,
            }),
            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }

    def clean(self):
        cleaned = super().clean()
        price = cleaned.get('price')
        discount = cleaned.get('discount_price')

        if discount is not None and price is not None:
            if discount >= price:
                raise ValidationError(
                    "Discount price must be lower than the regular price."
                )
        return cleaned

    def clean_stock(self):
        stock = self.cleaned_data['stock']
        if stock < 0:
            raise ValidationError("Stock cannot be negative.")
        return stock

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and hasattr(image, 'size'):
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("Image must be smaller than 5 MB.")
        return image


# ---------------------------------------------------------------------------
# PRODUCT IMAGE FORM (for gallery uploads)
# ---------------------------------------------------------------------------
class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text']
        widgets = {
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Alt text (optional)',
            }),
        }