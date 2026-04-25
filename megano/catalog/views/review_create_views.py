import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample
from catalog.models import Product, Review
from app_users.models import Profile
from catalog.serializers.review_serializers import ReviewCreateSerializer


logger = logging.getLogger(__name__)

class ReviewCreateView(APIView):
    permission_classes = [IsAuthenticated] # отзыв могут оставлять авторизованные

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
    def post(self, request, id):
        logger.info(f"Создание отзыва на товар ID: {id}")

        # Проверяем товар
        try:
            product = Product.objects.get(id=id)
        except Product.DoesNotExist:
            return Response({"error": "Товар не найден"}, status=404)

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
        return Response(ReviewCreateSerializer(review).data, status=201)