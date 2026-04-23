""" /sales
"""
from rest_framework.views import APIView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from catalog.models import Product, Sale
from rest_framework.permissions import AllowAny
from django.http import HttpRequest, HttpResponse
import logging
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model
from catalog.serializers.sales_serializers import SalesSerializer
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiExample, OpenApiParameter
import datetime
from django.core.cache import cache



User = get_user_model()
logger = logging.getLogger(__name__)

"""Распродажа"""


class SalesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Получение товаров из распродажи",
        tags=['catalog'],
        parameters=[
            OpenApiParameter(
                name='currentPage',
                description='page',
                required=False,
                type=int,
                default=1,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: SalesSerializer(many=True)},
    )
    def get(self, request):
        logger.info(f'GET запрос на получение распродажных товаров')

        # Получаем данные
        today = datetime.date.today()
        sale_products = Product.objects.filter(is_active=True,
                                               sale__isnull=False,  # скидка не null
                                               sale__date_from__lte=today,  # скидка активна на сегодня
                                               sale__date_to__gte=today  # скидка активна на текущее время
                                               ).select_related('category').prefetch_related('images')

        logger.info(f'Найдено {sale_products.count()} товаров в распродаже')

        if sale_products.count() > 0:
            logger.info(f'Примеры товаров в распродаже (первые 5):')
            for i, product in enumerate(sale_products[:5], 1):
                logger.info(f'  {i}. ID: {product.id}, Название: {product.title}, '
                            f'Скидка: {product.sale.sale_price}, '
                            f'Старая цена: {product.price}, '
                            f'Период скидки: {product.sale.date_from} - {product.sale.date_to}')
        else:
            logger.warning(f'Не найдено товаров в распродаже')

        # Пагинация вручную
        page = request.query_params.get('currentPage', 1)
        page_size = 10

        paginator = Paginator(sale_products, page_size)

        try:
            products_page = paginator.page(page)
        except PageNotAnInteger:
            products_page = paginator.page(1)
        except EmptyPage:
            products_page = paginator.page(paginator.num_pages)

        # Сериализация
        serializer = SalesSerializer(products_page, many=True)

        # Формируем ответ
        response_data = {
            'items': serializer.data,
            'currentPage': products_page.number,
            'lastPage': paginator.num_pages,
        }

        # Кэширование
        cache_key = f'sales_products_page_{page}'
        cache.set(cache_key, response_data, 600)

        return Response(response_data)