"""
Views for the store app.

Public (customer-facing):
  - home              → landing page (hero, categories, featured, new arrivals)
  - product_list      → catalog with search / filter / pagination
  - product_detail    → single product page + related products

Staff (dashboard-ready):
  - product_create    → add a product (staff only)
  - product_update    → edit a product (staff only)
  - product_delete    → delete a product (staff only, POST)

Notes:
  - All querysets use select_related / prefetch_related to avoid N+1 queries.
  - product_list reads GET params (q, category, min_price, max_price, page).
  - The search form is validated; if invalid, we still render the page
    (we just don't apply filters) so the user sees the error inline.
"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from .models import Product, Category
from .forms import ProductSearchForm, ProductForm


# ---------------------------------------------------------------------------
# HOME
# ---------------------------------------------------------------------------
def home(request):
    """
    Landing page:
      - 6 categories
      - up to 8 featured products (Product.featured=True)
      - up to 8 newest products
    """
    categories = Category.objects.all()[:6]

    featured_products = (
        Product.objects
        .filter(available=True, featured=True)
        .select_related('category')
        .order_by('-created_at')[:8]
    )

    new_arrivals = (
        Product.objects
        .filter(available=True)
        .select_related('category')
        .order_by('-created_at')[:8]
    )

    return render(request, 'store/home.html', {
        'categories': categories,
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
    })


# ---------------------------------------------------------------------------
# PRODUCT LIST (catalog + search + filter + pagination)
# ---------------------------------------------------------------------------
def product_list(request):
    """
    GET params:
      q          → free-text search (name + description)
      category   → category slug
      min_price  → minimum price
      max_price  → maximum price
      page       → pagination page number
    """
    form = ProductSearchForm(request.GET or None)

    products = (
        Product.objects
        .filter(available=True)
        .select_related('category')
        .order_by('-created_at')
    )

    current_category = None

    if form.is_valid():
        q = form.cleaned_data.get('q')
        cat_slug = form.cleaned_data.get('category')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')

        if q:
            products = products.filter(
                Q(name__icontains=q) | Q(description__icontains=q)
            )

        if cat_slug:
            current_category = Category.objects.filter(slug=cat_slug).first()
            if current_category:
                products = products.filter(category=current_category)

        if min_price is not None:
            products = products.filter(price__gte=min_price)

        if max_price is not None:
            products = products.filter(price__lte=max_price)

    # Pagination: 12 products per page
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'store/product_list.html', {
        'form': form,
        'products': page_obj,          # paginated queryset
        'categories': Category.objects.all(),
        'current_category': current_category,
    })


# ---------------------------------------------------------------------------
# PRODUCT DETAIL
# ---------------------------------------------------------------------------
def product_detail(request, slug):
    """
    Show a single product by slug, plus up to 4 related products
    from the same category.
    """
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('images'),
        slug=slug,
        available=True,
    )

    related_products = (
        Product.objects
        .filter(category=product.category, available=True)
        .exclude(pk=product.pk)
        .select_related('category')
        .order_by('-created_at')[:4]
    )

    return render(request, 'store/product_detail.html', {
        'product': product,
        'related_products': related_products,
    })


# ---------------------------------------------------------------------------
# STAFF: CREATE / UPDATE / DELETE  (dashboard-ready)
# ---------------------------------------------------------------------------
@staff_member_required
@require_http_methods(["GET", "POST"])
def product_create(request):
    """Add a new product. Staff only."""
    form = ProductForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        product = form.save()
        messages.success(request, f"Product '{product.name}' created.")
        return redirect('store:product_detail', slug=product.slug)

    return render(request, 'store/product_form.html', {
        'form': form,
        'action': 'Create',
    })


@staff_member_required
@require_http_methods(["GET", "POST"])
def product_update(request, slug):
    """Edit an existing product. Staff only."""
    product = get_object_or_404(Product, slug=slug)
    form = ProductForm(
        request.POST or None,
        request.FILES or None,
        instance=product,
    )

    if request.method == 'POST' and form.is_valid():
        product = form.save()
        messages.success(request, f"Product '{product.name}' updated.")
        return redirect('store:product_detail', slug=product.slug)

    return render(request, 'store/product_form.html', {
        'form': form,
        'action': 'Update',
        'product': product,
    })


@staff_member_required
@require_http_methods(["POST"])
def product_delete(request, slug):
    """Delete a product. Staff only, POST only."""
    product = get_object_or_404(Product, slug=slug)
    name = product.name
    product.delete()
    messages.success(request, f"Product '{name}' deleted.")
    return redirect('store:product_list')