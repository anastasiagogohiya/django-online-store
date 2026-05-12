"""/products/popular  - по кол-ву покупок"""

import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Product
from catalog.serializers.catalog_serializers import CatalogSerializer
from megano.decorators import catch_all_errors
from megano.permissions import AllowAll

User = get_user_model()
logger = logging.getLogger(__name__)


"""В каталог топ-товаров попадают восемь первых товаров по параметру «индекс
сортировки». Если же индекс сортировки совпадает, то товары сортируются
по количеству покупок"""


class ProductsPopularView(APIView):
    permission_classes = [AllowAll]  # могут просматривать все
    serializer_class = CatalogSerializer
    LIMITED_COUNT = 8  # максимум товаров
    CACHE_TIME = 3600  # 1 час

    @extend_schema(
        summary="Получение популярных товаров (8 самых покупаемых)",
        tags=["catalog"],
        examples=[
            OpenApiExample(
                "Пример популярного товара",
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
                        "tags": [{"id": 0, "name": "Hello world"}],
                        "reviews": 5,
                        "rating": 4.6,
                    }
                ],
            ),
        ],
    )
    @catch_all_errors
    def get(self, request: HttpRequest) -> HttpResponse:
        """
        В каталог топ-товаров попадают восемь первых товаров по параметру «индекс
        сортировки». Если же индекс сортировки совпадает, то товары сортируются
        по количеству покупок
        """
        logger.info("GET запрос на получение списка популярных товаров")

        # данные кэша
        cache_key = f"popular_products_limit_{self.LIMITED_COUNT}"
        cache_data = cache.get(cache_key)

        # если есть данные в кэше, то достаем
        if cache_data is not None:
            logger.info("Данные вернулись из кэша")
            return Response(cache_data)

        # только активные тов по индексу сортировки убыванию покупок
        popular_products = Product.objects.filter(is_active=True).order_by("-ordering_index", "-purchase_count")[
            : self.LIMITED_COUNT
        ]

        serializer = CatalogSerializer(popular_products, many=True)

        cache.set(cache_key, serializer.data, self.CACHE_TIME)

        logger.info(f"Найдено {popular_products.count()} популярных товаров")

        return Response(serializer.data)
