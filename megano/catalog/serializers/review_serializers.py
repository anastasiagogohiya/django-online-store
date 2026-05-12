import logging

from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from catalog.models import Review

logger = logging.getLogger(__name__)


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            name="Пример отзыва",
            value=[
                {
                    "author": "Annoying Orange",
                    "email": "no-reply@mail.ru",
                    "text": "rewrewrwerewrwerwerewrwerwer",
                    "rate": 4,
                    "date": "2023-05-05 12:12",
                },
                {
                    "author": "2Annoying Orange",
                    "email": "no-reply@mail.ru",
                    "text": "rewrewrwerewrwerwerewrwerwer",
                    "rate": 5,
                    "date": "2023-05-05 12:12",
                },
            ],
        ),
    ]
)
class ReviewSerializer(serializers.ModelSerializer):
    """Сериализатор для отзывов"""

    author = serializers.CharField(source="author.user.username")
    email = serializers.EmailField(source="author.user.email")
    date = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["author", "email", "text", "rate", "date"]

    def get_date(self, obj):
        """Форматирует дату в нужный формат"""
        local_dt = timezone.localtime(obj.date)
        return local_dt.strftime("%Y-%m-%d %H:%M")


class ReviewCreateSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.full_name", read_only=True)
    email = serializers.EmailField(source="author.email", read_only=True)
    date = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)

    class Meta:
        model = Review
        fields = ["author", "email", "text", "rate", "date"]

    def create(self, validated_data):
        request = self.context.get("request")
        review = Review.objects.create(
            product=validated_data.get("product"),
            author=request.user.profile,
            text=validated_data["text"],
            rate=validated_data["rate"],
        )
        return review


class ReviewGetSerializer(serializers.ModelSerializer):
    """Сериализатор для получения отзывов (GET)"""

    author = serializers.CharField(source="author.user.username", read_only=True)
    email = serializers.EmailField(source="author.user.email", read_only=True)
    date = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["author", "email", "text", "rate", "date", "avatar"]

    def get_date(self, obj):
        """Форматирует дату в нужный формат"""
        local_dt = timezone.localtime(obj.date)
        return local_dt.strftime("%Y-%m-%d %H:%M")

    def get_avatar(self, obj):
        try:
            if obj.author.avatar and obj.author.avatar.src:
                url = obj.author.avatar.src.url
                logger.info(f"Avatar URL for {obj.author.user.username}: {url}")
                return url
        except Exception as e:
            logger.error(f"Error getting avatar for {obj.author.user.username}: {e}")
        return None
