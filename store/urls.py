"""
URL patterns for the store app.

Public routes:
  /                       → home
  /products/              → product_list (with ?q=&category=&page=)
  /products/<slug>/       → product_detail

Staff routes (login + is_staff required by the views):
  /products/add/          → product_create
  /products/<slug>/edit/  → product_update
  /products/<slug>/delete/→ product_delete
"""

from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # ---------- Public ----------
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),

    # ---------- Staff dashboard ----------
    path('products/add/', views.product_create, name='product_create'),
    path('products/<slug:slug>/edit/', views.product_update, name='product_update'),
    path('products/<slug:slug>/delete/', views.product_delete, name='product_delete'),
]