"""categories/, catalog/"""

import logging

from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import generics, serializers
from rest_framework.response import Response

from catalog.models import Product
from catalog.serializers.catalog_serializers import CatalogSerializer
from catalog.utils import apply_price_filter, apply_search_filter, extract_filters, to_bool
from megano.decorators import catch_all_errors
from megano.permissions import AllowAll

"""Запрос на фильтрацию и сортировку данных"""

User = get_user_model()
logger = logging.getLogger(__name__)


# не получается пока в swagger первым полем фильтр сделать
class CatalogView(generics.ListAPIView):
    """Каталог товаров с сортировками и фильтрами"""

    queryset = Product.objects.filter(is_active=True)
    serializer_class = CatalogSerializer
    permission_classes = [AllowAll]

    @extend_schema(
        operation_id="get_catalog_items",
        description="get catalog items",
        parameters=[
            OpenApiParameter(
                name="filter",
                description="search text",
                required=False,
                location=OpenApiParameter.QUERY,
                type=inline_serializer(
                    name="FilterParams",
                    fields={
                        "name": serializers.CharField(required=False),
                        "minPrice": serializers.DecimalField(
                            required=False, max_digits=10, decimal_places=2, default=0
                        ),
                        "maxPrice": serializers.DecimalField(
                            required=False, max_digits=10, decimal_places=2, default=0
                        ),
                        "freeDelivery": serializers.BooleanField(required=False, default=False),
                        "available": serializers.BooleanField(required=False),
                    },
                ),
            ),
            OpenApiParameter(
                name="currentPage",
                required=False,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                default=1,
            ),
            OpenApiParameter(
                name="category",
                required=False,
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="sort",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=["date", "price", "rating", "title"],
                default="date",
            ),
            OpenApiParameter(
                name="sortType",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                enum=["inc", "dec"],
                default="dec",
            ),
            OpenApiParameter(
                name="tags",
                required=False,
                description="page",
                location=OpenApiParameter.QUERY,
                many=True,
                type=inline_serializer(
                    name="TagFilter",
                    fields={
                        "id": serializers.IntegerField(),
                        "name": serializers.CharField(),
                    },
                ),
            ),
            OpenApiParameter(
                name="limit", required=False, type=OpenApiTypes.INT, location=OpenApiParameter.QUERY, default=20
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Успешный ответ",
                response=OpenApiTypes.OBJECT,
                examples=[
                    OpenApiExample(
                        "Пример ответа",
                        value={
                            "items": [
                                {
                                    "id": 123,
                                    "category": 55,
                                    "price": 500.67,
                                    "count": 12,
                                    "date": "Thu Feb 09 2023 21:39:52 GMT+0100",
                                    "title": "video card",
                                    "description": "description of the product",
                                    "freeDelivery": True,
                                    "images": [{"src": "/3.png", "alt": "Image alt string"}],
                                    "tags": [{"id": 12, "name": "Gaming"}],
                                    "reviews": 5,
                                    "rating": 4.6,
                                }
                            ],
                            "currentPage": 1,
                            "lastPage": 10,
                        },
                    )
                ],
            )
        },
    )
    @catch_all_errors
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        logger.info("Запрос пользователя на фильтрацию данных...")
        queryset = super().get_queryset()

        # Получаем фильтры
        filters = extract_filters(self.request)

        # Поиск по названию
        if filters.get("name"):
            queryset = apply_search_filter(queryset, filters["name"])
            logger.info(f"Найдено по названию: {queryset.count()}")

        # Фильтр по цене
        queryset = apply_price_filter(queryset, filters.get("minPrice"), filters.get("maxPrice"))

        # Бесплатная доставка
        if filters.get("freeDelivery") and to_bool(filters["freeDelivery"]):
            logger.info("Фильтр: бесплатная доставка")
            queryset = queryset.filter(free_delivery=True)

        # Только в наличии
        if filters.get("available") is not None:
            if to_bool(filters["available"]):
                logger.info("Фильтр: только в наличии")
                queryset = queryset.filter(count__gt=0)

        # Категория
        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Теги
        tags = self.request.query_params.getlist("tags[]")
        if tags:
            tag_ids = [int(t) for t in tags if t.isdigit()]
            if tag_ids:
                queryset = queryset.filter(tags__id__in=tag_ids).distinct()

        # Сортировка
        sort_field = self.request.query_params.get("sort", "date")
        sort_type = self.request.query_params.get("sortType", "dec")

        sort_field_mapping = {
            "reviews": "reviews_count",
            "price": "price",
            "rating": "rating",
            "date": "date",
            "title": "title",
        }

        sort_field = sort_field_mapping.get(sort_field, "date")

        if sort_field:
            if sort_type == "dec":
                sort_field = f"-{sort_field}"
            queryset = queryset.order_by(sort_field)

        logger.info(f"Итоговое количество товаров: {queryset.count()}")
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Пагинация
        page = int(request.query_params.get("currentPage", 1))
        limit = int(request.query_params.get("limit", 20))

        paginator = Paginator(queryset, limit)
        products_page = paginator.get_page(page)

        serializer = self.get_serializer(products_page, many=True)

        response_data = {
            "items": serializer.data,
            "currentPage": products_page.number,
            "lastPage": paginator.num_pages,
        }
        return Response(response_data)
