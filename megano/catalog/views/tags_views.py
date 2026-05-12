import logging

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Category, Tag
from catalog.serializers.catalog_serializers import TagSerializer
from megano.decorators import catch_all_errors
from megano.permissions import AllowAll

logger = logging.getLogger(__name__)


class TagsView(APIView):
    """Класс получения тегов по categoryId"""

    permission_classes = [AllowAll]

    @extend_schema(
        summary="Получение тегов",
        tags=["tags"],
        parameters=[
            OpenApiParameter(
                name="category",
                description="categoryId",
                required=False,
                type=int,
                default=2,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: TagSerializer(many=True)},
    )
    @catch_all_errors
    def get(self, request) -> Response:
        category_id = request.query_params.get("category")
        logger.info(f"GET запрос на получение тегов по categoryId: {category_id}")

        tags = Tag.objects.all()

        if category_id:
            # Валидируем category_id
            category_id = int(category_id)

            # Проверяем существование категории
            if not Category.objects.filter(id=category_id).exists():
                logger.warning(f"Категория {category_id} не найдена")
                return Response([])  # возвращаем пустой список

            # Получаем теги через товары категории
            tags = (
                tags.filter(
                    product__category_id=category_id,
                    product__is_active=True,  # только активные товары
                )
                .distinct()
                .order_by("id")
            )

            logger.info(f"Категория {category_id}: найдено тегов={tags.count()}")

        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)
