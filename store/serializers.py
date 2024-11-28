from rest_framework import serializers
from .models import Category, Product, CartItem, Customer, Coupon, Discount
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image']

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'category', 'category_id', 'name', 'slug',
            'description', 'price', 'stock', 'available',
            'image', 'created', 'updated'
        ]

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'created']

        
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')

class RegisterSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'first_name', 'last_name')
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        Customer.objects.create(
            user=user,
            phone='', 
            address='' 
        )
        
        return user
    
class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = [
            'id', 'name', 'description', 'discount_type',
            'value', 'active', 'start_date', 'end_date'
        ]

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'description', 'discount_value', 'is_percentage',
            'minimum_purchase', 'valid_from', 'valid_to', 'max_uses',
            'current_uses'
        ]

# Actualizar el ProductSerializer para incluir descuentos
class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    current_price = serializers.SerializerMethodField()
    active_discounts = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'category', 'category_id', 'name', 'slug',
            'description', 'price', 'current_price', 'active_discounts',
            'stock', 'available', 'image', 'created', 'updated'
        ]

    def get_current_price(self, obj):
        best_discount = 0
        original_price = float(obj.price)
        
        for discount in obj.discounts.filter(active=True):
            if discount.is_valid():
                discount_amount = float(discount.calculate_discount(original_price))
                best_discount = max(best_discount, discount_amount)
        
        return original_price - best_discount

    def get_active_discounts(self, obj):
        return DiscountSerializer(
            [d for d in obj.discounts.filter(active=True) if d.is_valid()],
            many=True
        ).data