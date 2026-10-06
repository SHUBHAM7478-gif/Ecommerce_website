"""
URL patterns for the cart app.

  /cart/                     → cart_detail
  /cart/add/<product_id>/    → add_to_cart
  /cart/update/<item_id>/    → update_cart_item
  /cart/remove/<item_id>/    → remove_cart_item
  /cart/clear/               → clear_cart
"""

from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail, name='detail'),
    path('add/<int:product_id>/', views.add_to_cart, name='add'),
    path('update/<int:item_id>/', views.update_cart_item, name='update'),
    path('remove/<int:item_id>/', views.remove_cart_item, name='remove'),
    path('clear/', views.clear_cart, name='clear'),
]