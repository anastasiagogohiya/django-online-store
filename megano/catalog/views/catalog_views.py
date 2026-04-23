""" categories/, catalog/
"""
import logging
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework import serializers
from drf_spectacular.utils import inline_serializer
from catalog.serializers.catalog_serializers import CategorySerializer, CatalogSerializer, TagSerializer
from catalog.models import Category, Product
from rest_framework.response import Response
from rest_framework import generics
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
import json


"""Запрос на фильтрацию и сортировку данных"""

User = get_user_model()

logger = logging.getLogger(__name__)


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
                required=False,
                description='page',
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



        # Применяем фильтры название в названии товара, описании, полном описании (в модели поля title, description, full_description)
        if filters.get('name'):
            user_input = filters['name']
            # Разбиваем на отдельные слова
            search_words = user_input.split()
            logger.info(f'Пользователь ищет по названию {user_input},{search_words}')
            q_objects = Q()
            for word in search_words:
                q_objects |= Q(title__icontains=word) | Q(description__icontains=word) | Q(
                    full_description__icontains=word)

            queryset = queryset.filter(q_objects)
            logger.info(f'Найдено по названию {queryset.count()}')

        if filters.get('minPrice'):
            try:
                min_price = float(filters['minPrice'])
                logger.info(f'Пользователь выбрал цену ОТ: {min_price}')
                queryset = queryset.filter(price__gte=min_price)
            except (ValueError, TypeError):
                pass

        if filters.get('maxPrice'):
            try:
                max_price = float(filters['maxPrice'])
                logger.info(f'Пользователь выбрал цену ДО {max_price}')
                queryset = queryset.filter(price__lte=max_price)
            except (ValueError, TypeError):
                pass



        if filters.get('available') is not None:
            logger.info(f'Пользователь выбрал фильтр Только товары в наличии')
            if isinstance(filters['available'], str):
                available_bool = filters['available'].lower() == 'true'
            else:
                available_bool = bool(filters['available'])
            logger.info(f"Фильтр по наличию: {available_bool}")

            if available_bool:
                queryset = queryset.filter(count__gt=0) # только в наличии
            else:
                queryset = queryset.filter(count=0)
            logger.info(f"После фильтра available: {queryset.count()} товаров")

        # Фильтр по бесплатной доставке, фронтэнд по умолчанию высылает freeDelivery==false
        if filters.get('freeDelivery') is not None:
            if isinstance(filters['freeDelivery'], str):
                free_delivery_bool = filters['freeDelivery'].lower() == 'true'
            else:
                free_delivery_bool = bool(filters['freeDelivery'])

            # Фильтр если только true
            if free_delivery_bool:
                logger.info(f'Пользователь выбрал С бесплатной доставкой')
                queryset = queryset.filter(free_delivery=True)
                logger.info(f"После фильтра freeDelivery: {queryset.count()} товаров")
            else:
                logger.info(f'Фильтр freeDelivery=false, игнорируем')

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

        # Фильтр по тегам (фронтенд отправляет tags[])
        tags_param = self.request.query_params.getlist('tags[]') or self.request.query_params.getlist('tags')

        if tags_param:
            try:
                logger.info(f"Фильтрация по тегам: {tags_param}")
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

            logger.info(f"Итоговое количество товаров: {queryset.count()}")

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