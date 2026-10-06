"""
Forms for the orders app.

Covers:
  - CheckoutForm     → shipping details for placing an order (used on checkout page)
  - OrderStatusForm  → staff-only status change (used in admin / staff dashboard)

The CheckoutForm is a ModelForm on Order, but intentionally omits
`user`, `status`, `paid`, and `payment_method` — those are set by
the view and never accepted from the client.
"""

from django import forms

from .models import Order


# ---------------------------------------------------------------------------
# CHECKOUT
# ---------------------------------------------------------------------------
class CheckoutForm(forms.ModelForm):
    """
    Shipping + contact details collected at checkout.
    Only the fields a customer is allowed to submit are exposed.
    """

    class Meta:
        model = Order
        fields = ['full_name', 'email', 'address', 'city', 'postal_code', 'country']
        widgets = {
            'full_name':   forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'John Doe',
                'autocomplete': 'name',
            }),
            'email':       forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'you@example.com',
                'autocomplete': 'email',
            }),
            'address':     forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '123 Main Street, Apt 4B',
                'autocomplete': 'street-address',
            }),
            'city':        forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Mumbai',
                'autocomplete': 'address-level2',
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '400001',
                'autocomplete': 'postal-code',
            }),
            'country':     forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'India',
                'autocomplete': 'country-name',
            }),
        }

    # ---------- Custom validation ----------

    def clean_full_name(self):
        name = self.cleaned_data['full_name'].strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter your full name.")
        return name

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_address(self):
        address = self.cleaned_data['address'].strip()
        if len(address) < 5:
            raise forms.ValidationError("Please enter a complete address.")
        return address

    def clean_postal_code(self):
        pc = self.cleaned_data['postal_code'].strip()
        cleaned = pc.replace('-', '').replace(' ', '')
        if not cleaned.isdigit():
            raise forms.ValidationError("Postal code must contain digits only.")
        if len(cleaned) < 4:
            raise forms.ValidationError("Postal code is too short.")
        return pc

    def clean_country(self):
        country = self.cleaned_data['country'].strip()
        if len(country) < 2:
            raise forms.ValidationError("Please enter a valid country.")
        return country


# ---------------------------------------------------------------------------
# STAFF: CHANGE ORDER STATUS
# ---------------------------------------------------------------------------
class OrderStatusForm(forms.ModelForm):
    """
    Staff-only form to move an order through the fulfilment pipeline.
    Only the `status` field is exposed.
    """

    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_status(self):
        new_status = self.cleaned_data['status']
        current = self.instance.status

        # Guard: a delivered order can't go back to pending.
        if current == Order.STATUS_DELIVERED and new_status != Order.STATUS_DELIVERED:
            raise forms.ValidationError(
                "A delivered order cannot be changed to another status."
            )

        # Guard: a cancelled order is final.
        if current == Order.STATUS_CANCELLED and new_status != Order.STATUS_CANCELLED:
            raise forms.ValidationError(
                "A cancelled order cannot be changed to another status."
            )

        return new_status