from django.contrib import admin

from .models import CartItem


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity', 'size', 'price', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']
