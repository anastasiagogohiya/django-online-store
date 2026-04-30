"""для /product/{id} /product/{id}/review"""
import logging
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from catalog.models import Product
from django.shortcuts import get_object_or_404
from catalog.serializers.product_serializer import ProductSerializer
from catalog.serializers.review_serializers import ReviewSerializer
from megano.permissions import AllowAll
from django.core.cache import cache
from megano.decorators import catch_all_errors




logger = logging.getLogger(__name__)


class ProductView(APIView):
    permission_classes = [AllowAll] # инфу по товару могут посмотреть все
    CACHE_TIME = 3600  # 1 час

    @extend_schema(
        summary="Получение детальной информации по товару по id",
        tags=['product'],
        responses=ProductSerializer)
    @catch_all_errors
    def get(self, request, id: int) -> Response:
        logger.info(f"Получение карточки товара по id {id}...")

        cache_key = f'product_detail_{id}'
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.info(f"Товар {id} из кэша")
            return Response(cached_data)

        # Получение Product
        product_data = get_object_or_404(
            Product.objects.filter(is_active=True).prefetch_related(
                'images',
                'tags',
                'reviews',
                'specifications'
            ),id=id)

        # Если товар неактивен, но админ может его видеть
        if not product_data.is_active and not request.user.is_staff:
            return Response({"error": "Товар не доступен"}, status=404)


        serializer = ProductSerializer(product_data, context={'request': request})
        cache.set(cache_key, serializer.data, self.CACHE_TIME)
        return Response(serializer.data)