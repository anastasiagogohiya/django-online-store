import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from catalog.models import Product, Review
from app_users.models import Profile
from catalog.serializers.review_serializers import ReviewCreateSerializer, ReviewSerializer, ReviewGetSerializer
from megano.permissions import IsAuth, AllowAll
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from megano.decorators import catch_all_errors

logger = logging.getLogger(__name__)

class ReviewCreateView(APIView):
    permission_classes = [AllowAll]

    @extend_schema(
        summary="Создание отзыва на товар",
        tags=['product'],
        request=ReviewCreateSerializer,
        responses=ReviewCreateSerializer,
        examples=[
            OpenApiExample(
                name="Пример тела запроса",
                value={
                    "author": "Annoying Orange",
                    "email": "no-reply@mail.ru",
                    "text": "Отличный товар! Всем рекомендую!",
                    "rate": 5,
                    "date": "Thu Feb 09 2023 21:39:52 GMT+0100"
                },
            ),
        ]
    )
    @catch_all_errors
    def post(self, request, id: int) -> Response:
        logger.info(f"Создание отзыва на товар ID: {id}")

        # Проверяем товар
        product = get_object_or_404(Product, id=id)

        # Проверяем профиль
        try:
            profile = request.user.profile
        except (Profile.DoesNotExist, AttributeError):
            return Response({"error": "Профиль пользователя не найден"}, status=404)

        # Валидация данных
        serializer = ReviewCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "error": "Ошибка валидации данных",
                "details": serializer.errors}, status=400)

        # Создаём отзыв
        review = Review.objects.create(
            product=product,
            author=profile,
            text=serializer.validated_data['text'],
            rate=serializer.validated_data['rate'])

        logger.info(f"Отзыв создан: ID={review.id}")

        # Очищаем кэш товара иначе отзыва нового не видно
        cache_key = f'product_detail_{id}'
        cache.delete(cache_key)
        logger.info(f"Кэш товара {id} очищен")

        # Также очистить кэш популярных и ограниченных товаров
        cache.delete('popular_products_limit_8')
        cache.delete('products_limited_limit_16')

        return Response(ReviewSerializer(review).data, status=200)

    @extend_schema(
        summary="Получение отзывов на товар",
        tags=['product'],
        responses=ReviewGetSerializer(many=True)
    )
    @catch_all_errors
    def get(self, request, id: int) -> Response:
        logger.info(f"Получение отзывов на товар ID: {id}")

        product = get_object_or_404(Product, id=id)
        reviews = Review.objects.filter(product=product).order_by('-date')

        serializer = ReviewGetSerializer(reviews, many=True)
        return Response(serializer.data)