from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Category, Product, CartItem, Customer, Coupon, Discount
from .serializers import CategorySerializer, ProductSerializer, CartItemSerializer,UserSerializer, CouponSerializer, RegisterSerializer, DiscountSerializer 
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import requests
from django.conf import settings
from rest_framework.views import APIView



class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'

    @action(detail=True, methods=['get'])
    def products(self, request, slug=None):
        category = self.get_object()
        products = Product.objects.filter(category=category, available=True)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'slug'
    
    def get_queryset(self):
        queryset = Product.objects.filter(available=True)
        category_slug = self.request.query_params.get('category', None)
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        return queryset.prefetch_related('discounts')

class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer

    @action(detail=False, methods=['get'])
    def get_cart_total(self, request):
        cart_items = self.get_queryset()
        total = sum(item.product.price * item.quantity for item in cart_items)
        return Response({
            'total': total,
            'items_count': cart_items.count()
        })

    @action(detail=False, methods=['post'])
    def apply_coupon(self, request):
        code = request.data.get('code', '').strip().upper()  # Convertimos a mayúsculas
        cart_total = float(request.data.get('cart_total', 0))

        print(f"Intentando aplicar cupón: {code}")  # Debug
        print(f"Total del carrito: {cart_total}")  # Debug
        
        try:
            coupon = Coupon.objects.get(code__iexact=code)  # Búsqueda case-insensitive
            print(f"Cupón encontrado: {coupon}")  # Debug
            print(f"Cupón activo: {coupon.active}")
            print(f"Validez: {coupon.valid_from} - {coupon.valid_to}")
            
            # Validación detallada
            now = timezone.now()
            if not coupon.active:
                return Response({
                    'valid': False,
                    'message': 'El cupón no está activo'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            if now < coupon.valid_from:
                return Response({
                    'valid': False,
                    'message': 'El cupón aún no es válido'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            if now > coupon.valid_to:
                return Response({
                    'valid': False,
                    'message': 'El cupón ha expirado'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            if coupon.max_uses and coupon.current_uses >= coupon.max_uses:
                return Response({
                    'valid': False,
                    'message': 'El cupón ha alcanzado el límite de usos'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            if cart_total < coupon.minimum_purchase:
                return Response({
                    'valid': False,
                    'message': f'El monto mínimo de compra es ${coupon.minimum_purchase}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Calcular descuento
            discount_amount = coupon.calculate_discount(cart_total)
            
            return Response({
                'valid': True,
                'discount_amount': float(discount_amount),
                'final_total': cart_total - float(discount_amount),
                'message': 'Cupón aplicado exitosamente'
            })
            
        except Coupon.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'Cupón no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error al aplicar cupón: {str(e)}")  # Debug
            return Response({
                'valid': False,
                'message': 'Error al procesar el cupón'
            }, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['POST'])
def register_user(request):
    try:
        # Create user
        user = User.objects.create_user(
            username=request.data.get('username'),
            email=request.data.get('email'),
            password=request.data.get('password'),
            first_name=request.data.get('first_name', ''),
            last_name=request.data.get('last_name', '')
        )
        
        # Create customer profile
        Customer.objects.create(
            user=user,
            phone=request.data.get('phone', ''),
            address=request.data.get('address', '')
        )
        
        return Response({'message': 'Registration successful'}, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({
            'error': 'Por favor proporcione nombre de usuario y contraseña'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=username, password=password)
    
    if user:
        # Incluir más información del usuario en la respuesta
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        })
    
    return Response({
        'error': 'Credenciales inválidas'
    }, status=status.HTTP_401_UNAUTHORIZED)
    
class DiscountViewSet(viewsets.ModelViewSet):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer

    def get_queryset(self):
        queryset = Discount.objects.all()
        product_id = self.request.query_params.get('product', None)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    
    @action(detail=False, methods=['post'])
    def validate(self, request):
        code = request.data.get('code')
        cart_total = request.data.get('cart_total', 0)
        
        try:
            coupon = Coupon.objects.get(code=code)
            if coupon.is_valid(cart_total):
                discount_amount = coupon.calculate_discount(cart_total)
                return Response({
                    'valid': True,
                    'discount_amount': discount_amount,
                    'message': 'Cupón válido'
                })
            return Response({
                'valid': False,
                'message': 'Cupón no válido o expirado'
            }, status=400)
        except Coupon.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'Cupón no encontrado'
            }, status=404)

# Actualizar CartItemViewSet para incluir descuentos
class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer

    @action(detail=False, methods=['post'])
    def apply_coupon(self, request):
        code = request.data.get('code', '').strip().upper()
        try:
            cart_total = Decimal(str(request.data.get('cart_total', '0')))
        except:
            return Response({
                'valid': False,
                'message': 'Total del carrito inválido'
            }, status=status.HTTP_400_BAD_REQUEST)

        print(f"Intentando aplicar cupón: {code}")
        print(f"Total del carrito: {cart_total}")
        
        try:
            coupon = Coupon.objects.get(code__iexact=code)
            print(f"Cupón encontrado: {coupon}")
            print(f"Cupón activo: {coupon.active}")
            print(f"Validez: {coupon.valid_from} - {coupon.valid_to}")
            print(f"Minimum purchase: {coupon.minimum_purchase}")
            
            now = timezone.now()
            if not coupon.active:
                return Response({
                    'valid': False,
                    'message': 'El cupón no está activo'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            if now < coupon.valid_from:
                return Response({
                    'valid': False,
                    'message': 'El cupón aún no es válido'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            if now > coupon.valid_to:
                return Response({
                    'valid': False,
                    'message': 'El cupón ha expirado'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            if coupon.max_uses and coupon.current_uses >= coupon.max_uses:
                return Response({
                    'valid': False,
                    'message': 'El cupón ha alcanzado el límite de usos'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            if cart_total < coupon.minimum_purchase:
                return Response({
                    'valid': False,
                    'message': f'El monto mínimo de compra es ${coupon.minimum_purchase}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Calcular descuento
            discount_amount = coupon.calculate_discount(cart_total)
            print(f"Descuento calculado: {discount_amount}")
            
            return Response({
                'valid': True,
                'discount_amount': str(discount_amount),
                'final_total': str(cart_total - discount_amount),
                'message': 'Cupón aplicado exitosamente'
            })
            
        except Coupon.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'Cupón no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error al aplicar cupón: {str(e)}")
            return Response({
                'valid': False,
                'message': 'Error al procesar el cupón'
            }, status=status.HTTP_400_BAD_REQUEST)
            
class PaymentVerificationView(APIView):
    def post(self, request):
        order_id = request.data.get('orderID')
        
        # Obtener token de acceso
        auth_response = requests.post(
            'https://api-m.sandbox.paypal.com/v1/oauth2/token',
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET_KEY),
            data={'grant_type': 'client_credentials'}
        )
        
        access_token = auth_response.json()['access_token']
        
        # Verificar orden
        order_response = requests.get(
            f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        order_data = order_response.json()
        
        if order_data['status'] == 'COMPLETED':
            # Procesar la orden en tu sistema
            return Response({'status': 'success'})
        else:
            return Response(
                {'status': 'error', 'message': 'Payment not completed'}, 
                status=400
            )