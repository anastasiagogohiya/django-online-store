from rest_framework.views import APIView
import logging
from rest_framework.permissions import AllowAny
from catalog.models import Product, Tag, Category
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from catalog.serializers.catalog_serializers import TagSerializer


logger = logging.getLogger(__name__)

class TagsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Получение тегов",
        tags=['tags'],
        parameters=[
            OpenApiParameter(
                name='category',
                description='categoryId',
                required=False,
                type=int,
                default=2,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: TagSerializer(many=True)},
    )
    def get(self, request):
        category_id = request.query_params.get('category')
        logger.info(f"GET запрос на получение тегов по categoryId {category_id}")

        tags = Tag.objects.all() # выгружаем все тэги

        if category_id:
            # Проверяем существование категории, так как может не быть
            category_exists = Category.objects.filter(id=category_id).exists()
            logger.info(f"Категория {category_id}: существует={category_exists}")

            # Получаем теги через Product
            tags = tags.filter(product__category_id=category_id).distinct().order_by('id')

            # Логируем результат чтобы убедиться что правильные теги выдает
            tag_names = list(tags.values_list('name', flat=True))
            logger.info(f"Категория {category_id}: найдено тегов={len(tag_names)}, список={tag_names}")

        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)