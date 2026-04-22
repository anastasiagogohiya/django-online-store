from django.db.models import Prefetch
from django.http import HttpRequest, HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from catalog.models import Category
from catalog.serializers.catalog_serializers import CategorySerializer


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
