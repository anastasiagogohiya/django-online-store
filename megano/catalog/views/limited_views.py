""" /products/limited
"""
from rest_framework.views import APIView
from catalog.models import Product
from django.http import HttpRequest, HttpResponse
import logging
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model
from catalog.serializers.catalog_serializers import CatalogSerializer
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiExample
from django.core.cache import cache
from megano.permissions import AllowAll
from megano.decorators import catch_all_errors


User = get_user_model()
logger = logging.getLogger(__name__)


"""В блок «Ограниченный тираж» попадают до 16 товаров с галочкой
«ограниченный тираж». Отображаются эти товары в виде слайдера:
интерфейса, который показывает товары в виде прокручиваемой ленты"""

class ProductsLimitedView(APIView):
    permission_classes = [AllowAll] # могут просматривать все
    serializer_class = CatalogSerializer
    LIMITED_COUNT = 16  # максимум товаров
    CACHE_TIME = 3600  # 1 час

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
        ])
    @catch_all_errors
    def get(self, request: HttpRequest) -> HttpResponse:
        """В блок «Ограниченный тираж» попадают до 16 товаров с галочкой
        «ограниченный тираж». Отображаются эти товары в виде слайдера."""

        logger.info("GET запрос на получение списка товаров Ограниченного тиража")

        # данные кэша
        cache_key = f'products_limited_limit_{self.LIMITED_COUNT}'
        cache_data = cache.get(cache_key)

        # если есть данные в кэше, то достаем
        if cache_data is not None:
            logger.info(f'Данные вернулись из кэша')
            return Response(cache_data)

        # достает из БД лимитированные товары, сортировку поставила как для popular товаров
        limited_products = Product.objects.filter(is_active=True, is_limited=True).order_by('-ordering_index', '-purchase_count')[:self.LIMITED_COUNT]  # сортировка для слайдера
        serializer = CatalogSerializer(limited_products, many=True)

        # В кэше храним 1 час
        cache.set(cache_key, serializer.data, self.CACHE_TIME)

        logger.info(f"Найдено {limited_products.count()} товаров ограниченного тиража")

        return Response(serializer.data)