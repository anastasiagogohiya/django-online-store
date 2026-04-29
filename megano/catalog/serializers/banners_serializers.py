from rest_framework import serializers
from catalog.models import Category, Product, Tag, ProductImage
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample, extend_schema_field
from catalog.serializers.tag_serializers import TagSerializer
from catalog.serializers.product_image_serializer import ProductImageSerializer
from catalog.models import Banner

@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Получение баннеров',
            value=[
                {
                    "id": "123",
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
                            "alt": "hello alt",
                        }
                    ],
                    "tags": [
                        {
                            "id": 0,
                            "name": "Hello world"
                        }
                    ],
                    "reviews": 5,
                    "rating": 4.6
                }
            ]
        ),
    ]
)
class BannerSerializer(serializers.ModelSerializer):
    """Сериализатор для каталога"""
    images = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    reviews = serializers.IntegerField(source='reviews_count', read_only=True)
    rating = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)
    freeDelivery = serializers.BooleanField(source='free_delivery', read_only=True)


    class Meta:
        model = Product
        fields = ['id', 'category', 'price', 'count', 'date', 'title', 'description',
                  'freeDelivery', 'images', 'tags', 'reviews', 'rating']

    def get_images(self, obj):
        """Возвращает первое изображение товара"""
        first_image = obj.images.first()
        if not first_image:
            return []

        # Используем ProductImageSerializer и передаем контекст
        serializer = ProductImageSerializer(first_image, context=self.context)
        return [serializer.data]


class BannerImageSerializer(serializers.ModelSerializer):
    """Сериализатор для изображений баннера"""
    class Meta:
        model = Banner
        fields = ['src']



