from django.db import models
from django.utils.text import slugify
from decimal import Decimal
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super(Category, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super(Product, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created']

class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    created = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.quantity} x {self.product.name}'
    
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    
    def __str__(self):
        return self.user.username
    
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

# Agregar estos nuevos modelos a tu archivo models.py existente

class Discount(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Porcentaje'),
        ('fixed', 'Monto Fijo'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    value = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    active = models.BooleanField(default=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    products = models.ManyToManyField(
        'Product', 
        related_name='discounts',
        blank=True
    )

    def is_valid(self):
        now = timezone.now()
        return (
            self.active and 
            self.start_date <= now <= self.end_date
        )

    def calculate_discount(self, original_price):
        if not self.is_valid():
            return Decimal('0')
            
        original_price = Decimal(str(original_price))
        
        if self.discount_type == 'percentage':
            return (original_price * self.value / Decimal('100')).quantize(Decimal('0.01'))
        return min(self.value, original_price)

    def __str__(self):
        return f"{self.name} - {self.value}{'%' if self.discount_type == 'percentage' else '$'}"

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    discount_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    is_percentage = models.BooleanField(default=True)
    minimum_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    max_uses = models.IntegerField(default=None, null=True, blank=True)
    current_uses = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def calculate_discount(self, cart_total):
        if not self.is_valid(cart_total):
            return Decimal('0')
            
        cart_total = Decimal(str(cart_total))
        
        if self.is_percentage:
            return (cart_total * self.discount_value / Decimal('100')).quantize(Decimal('0.01'))
        return min(self.discount_value, cart_total)

    def is_valid(self, cart_total=None):
        now = timezone.now()
        
        if not self.active or now < self.valid_from or now > self.valid_to:
            return False
            
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
            
        if cart_total is not None and Decimal(str(cart_total)) < self.minimum_purchase:
            return False
            
        return True

    def __str__(self):
        return f"{self.code} - {self.discount_value}{'%' if self.is_percentage else '$'}"

class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)
    order_total = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ['coupon', 'user']
