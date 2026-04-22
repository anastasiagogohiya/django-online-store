""" /products/popular  - по кол-ву покупок
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


"""В каталог топ-товаров попадают восемь первых товаров по параметру «индекс
сортировки». Если же индекс сортировки совпадает, то товары сортируются
по количеству покупок"""


class ProductsPopularView(APIView):
    permission_classes = [AllowAny] # могут просматривать все
    serializer_class = CatalogSerializer

    @extend_schema(
        summary="Получение популярных товаров (8 самых покупаемых)",
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
        """
        В каталог топ-товаров попадают восемь первых товаров по параметру «индекс
        сортировки». Если же индекс сортировки совпадает, то товары сортируются
        по количеству покупок
        """
        logger.info("GET запрос на получение списка популярных товаров")

        limit = 8 # указала по ТЗ

        # данные кэша
        cache_key = f'popular_products_limit{limit}'
        cache_data = cache.get(cache_key)

        # если есть данные в кэше, то достаем
        if cache_data is not None:
            logger.info(f'Данные вернулись из кэша')
            return Response(cache_data)

        # только активные тов по индексу сортировки убыванию покупок
        popular_products = Product.objects.filter(is_active=True).order_by('-ordering_index', '-purchase_count')[:limit]

        serializer = CatalogSerializer(popular_products, many=True)
        # В кэше храним 1 час
        cache.delete(cache_key)
        cache.set(cache_key, serializer.data, 0)

        if popular_products:
            logger.info(f"Найдено {len(popular_products)} популярных товаров")
            for i, product in enumerate(popular_products[:limit], 1):
                logger.info(f"{i}. {product.title} - {product.purchase_count} покупок")
        return Response(serializer.data)
