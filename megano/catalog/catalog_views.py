""" categories/, catalog/
"""
from django.http import HttpRequest, HttpResponse
import logging
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.db.models import Prefetch
from rest_framework import serializers
from drf_spectacular.utils import inline_serializer
from catalog.serializers import CategorySerializer, CatalogSerializer, TagSerializer
from catalog.models import Category, Product
from rest_framework.response import Response
from rest_framework import generics
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiTypes
from drf_spectacular.types import OpenApiTypes
import json




User = get_user_model()

logger = logging.getLogger(__name__)


class CategoriesView(APIView):
    permission_classes = [AllowAny] # потом проверить

    @extend_schema(summary="Получение списка категорий",
                   responses={200: CategorySerializer(many=True)},
                   tags=['catalog'])
    def get(self, request: HttpRequest) -> HttpResponse:
        # Получаем только корневые категории (где parent = null, (WHERE parent IS NULL))
        # и предзагружаем подкатегории через related_name='subcategories'
        categories = Category.objects.filter(parent__isnull=True).prefetch_related(
            Prefetch('subcategories', queryset=Category.objects.all()),
            Prefetch('subcategories__subcategories', queryset=Category.objects.all()),
        )

        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)



# не получается пока в swagger первым полем фильтр сделать
class CatalogView(generics.ListAPIView):
    """Каталог товаров"""
    queryset = Product.objects.filter(is_active=True)
    serializer_class = CatalogSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="get_catalog_items",
        description="get catalog items",
        parameters=[
            OpenApiParameter(
                name='filter',
                description='search text',
                required=False,
                location=OpenApiParameter.QUERY,
                type=inline_serializer(
                    name='FilterParams',
                    fields={
                        'name': serializers.CharField(required=False),
                        'minPrice': serializers.DecimalField(required=False, max_digits=10, decimal_places=2,
                                                             default=0),
                        'maxPrice': serializers.DecimalField(required=False, max_digits=10, decimal_places=2,
                                                             default=0),
                        'freeDelivery': serializers.BooleanField(required=False, default=False),
                        'available': serializers.BooleanField(required=False),
                    }
                )
            ),

            OpenApiParameter(
                name='currentPage',
                required=False,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                default=1,
            ),
            OpenApiParameter(
                name='category',
                required=False,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name='sort',
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=['date', 'price', 'rating', 'title'],
                default='date'
            ),
            OpenApiParameter(
                name='sortType',
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=['inc', 'dec'],
                default='dec'
            ),

            OpenApiParameter(
                name='tags',
                description='page\n\nArray of tag objects',
                required=False,
                location=OpenApiParameter.QUERY,
                many=True,
                type=inline_serializer(
                    name='TagFilter',
                    fields={
                        'id': serializers.IntegerField(),
                        'name': serializers.CharField(),
                    }
                )
            ),

            OpenApiParameter(
                name='limit',
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                default=20
            ),
        ],
        responses={
            200: OpenApiTypes.OBJECT,
        }
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        logger.info("Запрос пользователя на фильтрацию данных.....")

        queryset = super().get_queryset()

        # Собираем фильтры
        filters = {}

        # filter с JSON
        filter_param = self.request.query_params.get('filter')
        if filter_param:
            try:
                json_filters = json.loads(filter_param)
                filters.update(json_filters)
            except json.JSONDecodeError:
                pass

        # вложенные фильтры filter[name], filter[minPrice]
        nested_filters = {
            'name': self.request.query_params.get('filter[name]'),
            'minPrice': self.request.query_params.get('filter[minPrice]'),
            'maxPrice': self.request.query_params.get('filter[maxPrice]'),
            'freeDelivery': self.request.query_params.get('filter[freeDelivery]'),
            'available': self.request.query_params.get('filter[available]'),
        }

        # Добавляем непустые значения из вложенных параметров
        filters.update({k: v for k, v in nested_filters.items() if v and v != ''})

        queryset = super().get_queryset()



        # Применяем фильтры
        if filters.get('name'):
            queryset = queryset.filter(title__icontains=filters['name'])

        if filters.get('minPrice'):
            try:
                min_price = float(filters['minPrice'])
                queryset = queryset.filter(price__gte=min_price)
            except (ValueError, TypeError):
                pass

        if filters.get('maxPrice'):
            try:
                max_price = float(filters['maxPrice'])
                queryset = queryset.filter(price__lte=max_price)
            except (ValueError, TypeError):
                pass

        if filters.get('freeDelivery') is not None:
            if isinstance(filters['freeDelivery'], str):
                free_delivery_bool = filters['freeDelivery'].lower() == 'true'
            else:
                free_delivery_bool = bool(filters['freeDelivery'])
            queryset = queryset.filter(free_delivery=free_delivery_bool)

        if filters.get('available') is not None:
            if isinstance(filters['available'], str):
                available_bool = filters['available'].lower() == 'true'
            else:
                available_bool = bool(filters['available'])

            if available_bool:
                queryset = queryset.filter(count__gt=0)
            else:
                queryset = queryset.filter(count=0)

        # Сортировка
        sort_field = self.request.query_params.get('sort')
        sort_type = self.request.query_params.get('sortType', 'inc')

        if sort_field:
            if sort_type == 'dec':
                sort_field = f'-{sort_field}'
            queryset = queryset.order_by(sort_field)

        # Фильтр по категории
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Фильтр по тегам
        tags_param = self.request.query_params.get('tags')
        if tags_param:
            try:
                # Пробуем распарсить JSON
                tags = json.loads(tags_param) if isinstance(tags_param, str) else tags_param
                if isinstance(tags, list):
                    tag_ids = []
                    for tag in tags:
                        if isinstance(tag, dict) and 'id' in tag:
                            tag_ids.append(tag['id'])
                        elif isinstance(tag, (int, str)):
                            tag_ids.append(int(tag))

                    if tag_ids:
                        queryset = queryset.filter(tags__id__in=tag_ids).distinct()
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Ошибка парсинга tags: {e}")

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        total = queryset.count()

        # Пагинация
        try:
            limit = int(request.query_params.get('limit', 20))  # изменено на 20 по умолчанию
            current_page = int(request.query_params.get('currentPage', 1))
        except ValueError:
            limit = 20
            current_page = 1

        # Вычисляем lastPage
        last_page = (total + limit - 1) // limit if limit > 0 else 1

        start = (current_page - 1) * limit
        end = start + limit

        paginated_queryset = queryset[start:end]
        serializer = self.get_serializer(paginated_queryset, many=True)

        # Формируем ответ в нужном формате
        response_data = {
            'items': serializer.data,
            'currentPage': current_page,
            'lastPage': last_page,}

        logger.info(f"Ответ на запрос пользователя:")

        logger.info(
            f"Ответ JSON: {json.dumps(response_data, ensure_ascii=False)[:500]}...")  # первые 500 символов

        return Response(response_data)