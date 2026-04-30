from rest_framework import serializers
from catalog.models import Category, Product, Tag, ProductImage
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample, extend_schema_field
from catalog.serializers.tag_serializers import TagSerializer
from catalog.serializers.specification_serializer import SpecificationSerializer
from catalog.serializers.product_image_serializer import ProductImageSerializer
from catalog.serializers.review_serializers import ReviewSerializer


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Пример карточки товара',
            value={
                "id": 123,
                "category": 55,
                "price": 500.67,
                "count": 12,
                "date": "Thu Feb 09 2023 21:39:52 GMT+0100 (Central European Standard Time)",
                "title": "video card",
                "description": "description of the product",
                "fullDescription": "full description of the product",
                "freeDelivery": True,
                "images": [
                    {
                        "src": "https://psk68.ru/files/metod/uchebnik_Informatika/user-images/video.png",
                        "alt": "hello alt",
                    },
                    {
                        "src": "https://www.asus.com/microsite/2014/vga/gaming_graphics_cards/img/quietly-cool/dust-proof-card.png",
                        "alt": "hello alt",
                    },
                    {
                        "src": "https://psk68.ru/files/metod/uchebnik_Informatika/user-images/video.png",
                        "alt": "hello alt",
                    }
                ],
                "tags": [
                    {
                        "id": 0,
                        "name": "Hello world"
                    }
                ],
                "reviews": [
                    {
                        "author": "Annoying Orange",
                        "email": "no-reply@mail.ru",
                        "text": "rewrewrwerewrwerwerewrwerwer",
                        "rate": 4,
                        "date": "2023-05-05 12:12"
                    }
                ],
                "specifications": [
                    {
                        "name": "Size",
                        "value": "XL"
                    }
                ],
                "rating": 4.6
            }
        ),
    ]
)
class ProductSerializer(serializers.ModelSerializer):
    """Сериализатор карточки товара по id"""
    images = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    specifications = SpecificationSerializer(many=True, read_only=True)  # ← была проблема с отступом
    # Переопределяем поле price
    price = serializers.SerializerMethodField()
    rating = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    freeDelivery = serializers.BooleanField(source='free_delivery', read_only=True)
    fullDescription = serializers.CharField(source='full_description', read_only=True)  # ← Text → TextField

    class Meta:
        model = Product
        fields = ['id', 'category', 'price', 'count', 'date', 'title', 'description',
                  'fullDescription', 'freeDelivery', 'images', 'tags', 'reviews',
                  'specifications', 'rating']

    def get_price(self, obj):
        """Возвращает цену с учетом активной распродажи, иначе возвращается старая цена"""
        return obj.current_price # метод в модели у меня такой

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_images(self, obj):
        """Возвращает массив изображений"""
        images_data = []

        # Получаем все изображения товара
        for img in obj.images.all():
            if img.image and img.image.name:
                images_data.append({
                    "src": img.image.url,
                    "alt": obj.title
                })

        # псевдоизображение, иначе фронтэнд пишет ошибку
        if not images_data:
            images_data.append({
                "src": "https://noimage/",
                "alt": obj.title
            })

        return images_data