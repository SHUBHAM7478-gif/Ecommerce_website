"""
URL patterns for the orders app.

  /orders/checkout/             → checkout
  /orders/success/<order_id>/   → order_success
  /orders/                     → order_history
  /orders/<order_id>/          → order_detail

Order matters: `checkout/` and `success/...` must come before `<int:order_id>/`
so Django doesn't try to match "checkout" as an integer.
"""

from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('success/<int:order_id>/', views.order_success, name='order_success'),
    path('', views.order_history, name='order_history'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
]