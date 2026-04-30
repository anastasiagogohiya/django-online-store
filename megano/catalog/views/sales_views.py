""" /sales
"""
from rest_framework.views import APIView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from catalog.models import Product, Sale
import logging
from django.http import HttpRequest, HttpResponse
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model
from catalog.serializers.sales_serializers import SalesSerializer
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiExample, OpenApiParameter
import datetime
from django.core.cache import cache
from megano.permissions import AllowAll
from megano.decorators import catch_all_errors



User = get_user_model()
logger = logging.getLogger(__name__)

"""Распродажа"""


class SalesView(APIView):
    """Получение товаров из распродажи с пагинацией и кэшированием"""
    permission_classes = [AllowAll]
    CACHE_TIME = 3600  # 1 час
    PAGE_SIZE = 8  # товаров на странице

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
    @catch_all_errors
    def get(self, request: HttpRequest) -> HttpResponse:
        logger.info(f'GET запрос на получение распродажных товаров')

        # Получаем номер страницы
        try:
            page = int(request.query_params.get('currentPage', 1))
        except ValueError:
            page = 1

        # Кэширование
        cache_key = f'sales_products_page_{page}'
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.info(f'Данные вернулись из кэша')
            return Response(cached_data)


        # Получаем данные
        today = datetime.date.today()
        sale_products = Product.objects.filter(is_active=True,
                                               sale__isnull=False,  # скидка не null
                                               sale__date_from__lte=today,  # скидка активна на сегодня
                                               sale__date_to__gte=today  # скидка активна на текущее время
                                               ).select_related('category', 'sale').prefetch_related('images')

        logger.info(f'Найдено {sale_products.count()} товаров в распродаже')

        # Пагинация
        paginator = Paginator(sale_products, self.PAGE_SIZE)
        products_page = paginator.get_page(page) # get_page() встроенный метод в Джанго

        # Сериализация
        serializer = SalesSerializer(products_page, many=True)

        # Формируем ответ
        response_data = {
            'items': serializer.data,
            'currentPage': products_page.number,
            'lastPage': paginator.num_pages,}

        cache.set(cache_key, response_data, self.CACHE_TIME)

        return Response(response_data)