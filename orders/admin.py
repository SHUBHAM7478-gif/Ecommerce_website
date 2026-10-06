from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'price', 'quantity', 'subtotal_display')

    def subtotal_display(self, obj):
        return obj.subtotal
    subtotal_display.short_description = 'Subtotal'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'number', 'full_name', 'email', 'city',
        'status', 'paid', 'total_display', 'created_at',
    )
    list_filter = ('status', 'paid', 'payment_method', 'created_at')
    search_fields = ('full_name', 'email', 'address', 'city', 'postal_code')
    readonly_fields = ('created_at', 'updated_at', 'total_display')
    inlines = [OrderItemInline]

    fieldsets = (
        ('Owner', {
            'fields': ('user',)
        }),
        ('Contact', {
            'fields': ('full_name', 'email')
        }),
        ('Shipping', {
            'fields': ('address', 'city', 'postal_code', 'country')
        }),
        ('Order', {
            'fields': ('status', 'payment_method', 'paid', 'total_display')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def total_display(self, obj):
        return f"₹{obj.get_total()}"
    total_display.short_description = 'Total'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'price', 'quantity', 'subtotal_display')
    list_filter = ('order__status',)
    search_fields = ('product_name', 'order__full_name')

    def subtotal_display(self, obj):
        return obj.subtotal
    subtotal_display.short_description = 'Subtotal'