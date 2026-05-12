"""Сериализатор для распродажи"""

from random import randrange

from drf_spectacular.utils import OpenApiExample, extend_schema_field, extend_schema_serializer
from rest_framework import serializers

from catalog.models import Product
from catalog.serializers.product_image_serializer import ProductImageSerializer


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Пример товара с распродажи",
            value=[
                {
                    "items": [
                        {
                            "id": 123,
                            "price": 500.67,
                            "salePrice": 200.67,
                            "dateFrom": "05-08",
                            "dateTo": "05-20",
                            "title": "video card",
                            "images": [
                                {
                                    "src": "https://proprikol.ru/wp-content/uploads/2020/12/kartinki-ryabchiki-14.jpg",
                                    "alt": "hello alt",
                                }
                            ],
                        }
                    ],
                    "currentPage": randrange(1, 4),
                    "lastPage": 3,
                },
            ],
        ),
    ]
)
class SalesSerializer(serializers.ModelSerializer):
    """Сериализатор для товаров со скидкой"""

    salePrice = serializers.DecimalField(source="sale.sale_price", max_digits=10, decimal_places=2)
    dateFrom = serializers.SerializerMethodField()
    dateTo = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ["id", "price", "salePrice", "dateFrom", "dateTo", "title", "images"]

    @extend_schema_field(serializers.CharField(allow_null=True))  # иначе в теримнале предупреждение об отсутсвии типа
    def get_dateFrom(self, obj):
        """Возвращает дату начала в формате MM-DD (неудобно но так написано в api)"""
        if hasattr(obj, "sale") and obj.sale:
            return obj.sale.date_from.strftime("%m-%d")
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))  # иначе в теримнале предупреждение об отсутсв
    def get_dateTo(self, obj):
        """Возвращает дату окончания в формате MM-DD"""
        if hasattr(obj, "sale") and obj.sale:
            return obj.sale.date_to.strftime("%m-%d")
        return None
