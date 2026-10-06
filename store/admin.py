from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    readonly_fields = ('created_at',)

    def product_count(self, obj):
        return obj.product_count
    product_count.short_description = 'Products'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'price', 'discount_price',
        'stock', 'available', 'featured', 'created_at',
    )
    list_filter = ('available', 'featured', 'category', 'created_at')
    list_editable = ('price', 'stock', 'available', 'featured')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'preview_image')
    inlines = [ProductImageInline]

    fieldsets = (
        ('Basic', {
            'fields': ('category', 'name', 'slug', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'discount_price')
        }),
        ('Inventory', {
            'fields': ('stock', 'available', 'featured')
        }),
        ('Media', {
            'fields': ('image', 'preview_image')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def preview_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:150px;border-radius:6px;" />',
                obj.image.url
            )
        return "—"
    preview_image.short_description = 'Preview'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'alt_text', 'created_at')
    search_fields = ('product__name', 'alt_text')