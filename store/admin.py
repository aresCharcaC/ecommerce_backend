from django.contrib import admin
from .models import Category, Product, CartItem, CouponUsage, Coupon, Discount

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created', 'updated']
    list_filter = ['created', 'updated']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'category', 'price', 'stock', 'available', 'created']
    list_filter = ['available', 'created', 'updated', 'category']
    list_editable = ['price', 'stock', 'available']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    raw_id_fields = ['category']
    date_hierarchy = 'created'
    ordering = ['created']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'created']
    list_filter = ['created']
    raw_id_fields = ['product']
    
@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ['name', 'discount_type', 'value', 'active', 'start_date', 'end_date']
    list_filter = ['active', 'discount_type', 'start_date', 'end_date']
    search_fields = ['name', 'description']
    filter_horizontal = ['products'] 
    date_hierarchy = 'start_date'
    ordering = ['-start_date']

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_value', 'is_percentage', 'active', 'valid_from', 'valid_to', 'current_uses']
    list_filter = ['active', 'is_percentage', 'valid_from', 'valid_to']
    search_fields = ['code', 'description']
    date_hierarchy = 'valid_from'
    ordering = ['-valid_from']

@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ['coupon', 'user', 'used_at', 'order_total', 'discount_amount']
    list_filter = ['used_at']
    search_fields = ['coupon__code', 'user__username']
    date_hierarchy = 'used_at'
    ordering = ['-used_at']
    
    
