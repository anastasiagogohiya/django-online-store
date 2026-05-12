import logging

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Banner
from catalog.serializers.banners_serializers import BannerSerializer
from megano.decorators import catch_all_errors

logger = logging.getLogger(__name__)


class BannersView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Получение баннеров",
        description="Возвращает список баннеров для отображения. "
        "До 4 баннеров, чтобы в фронтэнде было красивое отображение",
        tags=["catalog"],
        responses=BannerSerializer(many=True),
    )
    @catch_all_errors
    def get(self, request):
        logger.info("Получение списка баннеров...")

        # Получение баннеров и связанных с ними Product
        banners = (
            Banner.objects.filter(is_active=True)
            .select_related("product")
            .prefetch_related("product__images", "product__tags")[:4]
        )  # сделала до 4, так как в фронэнде страница вправа некрасиво уходит

        products = [banner.product for banner in banners]

        serializer = BannerSerializer(products, many=True, context={"request": request})
        serialized_data = serializer.data

        return Response(serialized_data)
