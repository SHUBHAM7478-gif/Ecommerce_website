"""
Forms for the cart app.

  - AddToCartForm       → quantity input on product pages
  - UpdateCartItemForm  → inline quantity update on the cart page
"""

from django import forms


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
        }),
    )

    def __init__(self, *args, product=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product
        if product is not None:
            self.fields['quantity'].widget.attrs['max'] = product.stock

    def clean_quantity(self):
        qty = self.cleaned_data['quantity']
        if self.product is not None and qty > self.product.stock:
            raise forms.ValidationError(
                f"Only {self.product.stock} item(s) left in stock."
            )
        return qty


class UpdateCartItemForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
        }),
    )

    def __init__(self, *args, cart_item=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cart_item = cart_item
        if cart_item is not None:
            self.fields['quantity'].widget.attrs['max'] = cart_item.product.stock

    def clean_quantity(self):
        qty = self.cleaned_data['quantity']
        if self.cart_item is not None and qty > self.cart_item.product.stock:
            raise forms.ValidationError(
                f"Only {self.cart_item.product.stock} item(s) available."
            )
        return qty