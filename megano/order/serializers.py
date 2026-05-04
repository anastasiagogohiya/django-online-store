from rest_framework import serializers
from .models import Order, OrderItem
from catalog.serializers.product_serializer import ProductSerializer
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from catalog.models import Product
from catalog.serializers.tag_serializers import TagSerializer


class OrderItemProductSerializer(serializers.ModelSerializer):
    """Сериализатор для товара внутри заказа (через OrderItem)"""
    id = serializers.IntegerField(source='product.id', read_only=True)
    category = serializers.IntegerField(source='product.category.id', read_only=True)
    price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    count = serializers.IntegerField(source='quantity', read_only=True)
    date = serializers.DateTimeField(source='product.date', read_only=True)
    title = serializers.CharField(source='product.title', read_only=True)
    description = serializers.CharField(source='product.description', read_only=True)
    freeDelivery = serializers.BooleanField(source='product.free_delivery', read_only=True)
    rating = serializers.DecimalField(source='product.rating', max_digits=3, decimal_places=2, read_only=True)
    reviews = serializers.IntegerField(source='product.reviews_count', read_only=True)
    images = serializers.SerializerMethodField()
    tags = TagSerializer(source='product.tags', many=True, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'category', 'price', 'count', 'date', 'title', 'description',
                  'freeDelivery', 'images', 'tags', 'reviews', 'rating']

    def get_images(self, obj):
        """Возвращает массив изображений из продукта"""
        images_data = []
        for img in obj.product.images.all():
            if img.image and img.image.name:
                images_data.append({
                    "src": img.image.url,
                    "alt": obj.product.title
                })

        if not images_data:
            images_data.append({
                "src": "https://noimage/",
                "alt": obj.product.title
            })

        return images_data



@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Получение заказов',
            value=[
			{
        "id": 123,
        "createdAt": "2023-05-05 12:12",
        "fullName": "Annoying Orange",
        "email": "no-reply@mail.ru",
        "phone": "88002000600",
        "deliveryType": "free",
        "paymentType": "online",
        "totalCost": 567.8,
        "status": "accepted",
        "city": "Moscow",
        "address": "red square 1",
        "products": [
          {
            "id": 123,
            "category": 55,
            "price": 500.67,
            "count": 12,
            "date": "Thu Feb 09 2023 21:39:52 GMT+0100 (Central European Standard Time)",
            "title": "video card",
            "description": "description of the product",
            "freeDelivery": True,
            "images": [
              {
                "src": "https://proprikol.ru/wp-content/uploads/2020/12/kartinki-ryabchiki-14.jpg",
                "alt": "Image alt string"
              }
            ],
            "tags": [
              {
                "id": 12,
                "name": "Gaming"
              }
            ],
            "reviews": 5,
            "rating": 4.6
          }
        ]
      },
			{
        "id": 123,
        "createdAt": "2023-05-05 12:12",
        "fullName": "Annoying Orange",
        "email": "no-reply@mail.ru",
        "phone": "88002000600",
        "deliveryType": "free",
        "paymentType": "online",
        "totalCost": 567.8,
        "status": "accepted",
        "city": "Moscow",
        "address": "red square 1",
        "products": [
          {
            "id": 123,
            "category": 55,
            "price": 500.67,
            "count": 12,
            "date": "Thu Feb 09 2023 21:39:52 GMT+0100 (Central European Standard Time)",
            "title": "video card",
            "description": "description of the product",
            "freeDelivery": True,
            "images": [
              {
                "src": "https://proprikol.ru/wp-content/uploads/2020/12/kartinki-ryabchiki-14.jpg",
                "alt": "Image alt string"
              }
            ],
            "tags": [
              {
                "id": 12,
                "name": "Gaming"
              }
            ],
            "reviews": 5,
            "rating": 4.6
}
                    ]
                }
            ]
        )
    ]
)
class OrderSerializer(serializers.ModelSerializer):
    #profile = serializers.PrimaryKeyRelatedField(read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    fullName = serializers.CharField(source='profile.full_name', read_only=True)
    email = serializers.CharField(source='profile.user.email', read_only=True)
    phone = serializers.CharField(source='profile.phone', read_only=True)
    deliveryType = serializers.CharField(source='delivery_type')
    paymentType = serializers.CharField(source='payment_type')
    address = serializers.CharField(source='address_delivery')
    totalCost = serializers.DecimalField(source='total_cost', max_digits=10, decimal_places=2, read_only=True) # в модели нужно делать метод вычисления для этого поля проперти
    products = OrderItemProductSerializer(source='items', many=True, read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'createdAt', 'fullName', 'email', 'phone', 'deliveryType',
                  'paymentType', 'totalCost', 'status', 'city', 'address', 'products']


class OrderIdSerializer(serializers.ModelSerializer):
    orderId = serializers.IntegerField(source='id')

    class Meta:
        model = Order
        fields = ['orderId']





class CreateOrderSerializer(serializers.Serializer):
    """Сериализатор для создания заказа из корзины"""
    # Поля для товаров
    id = serializers.IntegerField()
    category = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    count = serializers.IntegerField(min_value=1)
    date = serializers.DateTimeField()
    title = serializers.CharField()
    description = serializers.CharField()
    freeDelivery = serializers.BooleanField()
    images = serializers.ListField()
    tags = serializers.ListField()
    reviews = serializers.IntegerField()
    rating = serializers.CharField()

