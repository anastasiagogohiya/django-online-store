"""для /product/{id} /product/{id}/review"""
import logging
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from catalog.models import Product
from catalog.serializers.product_serializer import ProductSerializer
from catalog.serializers.review_serializers import ReviewSerializer




logger = logging.getLogger(__name__)


class ProductView(APIView):
    permission_classes = [AllowAny] # инфу по товару могут посмотреть все

    @extend_schema(
        summary="Получение детальной информации по товару по id",
        tags=['product'],
        responses=ProductSerializer)
    def get(self, request, id):

        logger.info(f"Получение карточки товара по id {id}...")

        if not id:
            return Response({"error": "Введите id товара"}, status=400)

        # Получение Product
        try:
            product_data = Product.objects.prefetch_related(
                'images', 'tags', 'reviews', 'specifications').get(id=id)
        except Product.DoesNotExist:
            return Response({"error": "Товар не найден"}, status=404)


        serializer = ProductSerializer(product_data, context={'request': request})

        return Response(serializer.data)


