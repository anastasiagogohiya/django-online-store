""" /products/limited
"""
from rest_framework.views import APIView
from catalog.models import Product
from rest_framework.permissions import AllowAny
from django.http import HttpRequest, HttpResponse
import logging
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model
from catalog.serializers.catalog_serializers import CatalogSerializer
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiExample
from django.core.cache import cache


User = get_user_model()
logger = logging.getLogger(__name__)


"""В блок «Ограниченный тираж» попадают до 16 товаров с галочкой
«ограниченный тираж». Отображаются эти товары в виде слайдера:
интерфейса, который показывает товары в виде прокручиваемой ленты"""

class ProductsLimitedView(APIView):
    permission_classes = [AllowAny] # могут просматривать все
    serializer_class = CatalogSerializer

    @extend_schema(
        summary="Получение товаров Ограниченного тиража",
        tags=['catalog'],
        examples=[
            OpenApiExample(
                'Пример популярного товара',
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
    def get(self, request: HttpRequest) -> HttpResponse:
        """В блок «Ограниченный тираж» попадают до 16 товаров с галочкой
        «ограниченный тираж». Отображаются эти товары в виде слайдера."""

        logger.info("GET запрос на получение списка товаров Ограниченного тиража")

        limit = 16

        # данные кэша
        cache_key = f'products_limited_limit{limit}'
        cache_data = cache.get(cache_key)

        # если есть данные в кэше, то достаем
        if cache_data is not None:
            logger.info(f'Данные вернулись из кэша')
            return Response(cache_data)

        # достает из БД лимитированные товары, сортировку поставила как для popular товаров
        limited_products = Product.objects.filter(is_active=True, is_limited=True).order_by('-ordering_index', '-purchase_count')[:limit]  # сортировка для слайдера
        serializer = CatalogSerializer(limited_products, many=True)

        # В кэше храним 1 час
        cache.delete(cache_key)
        cache.set(cache_key, serializer.data, 0)

        if limited_products:
            logger.info(f"Найдено {len(limited_products)} товаров ограниченного тиража")
            for i, product in enumerate(limited_products[:limit], 1):
                logger.info(f"{i}. {product.title} - {product.is_limited}")
        return Response(serializer.data)








