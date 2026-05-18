"""СЕРИАЛИЗАТОРЫ для профиля"""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers

from app_users.models import Avatar, Profile

User = get_user_model()


"""Для profile/"""


class AvatarSerializer(serializers.ModelSerializer):
    """Преобразование объекта аватар в JSON
    Аватар - вложенный объект в ProfileSerializer"""

    src = serializers.SerializerMethodField()  # спец поле

    class Meta:
        model = Avatar
        fields = ["src", "alt"]  # JSON будут {"src":..alt..}

    def get_src(self, obj) -> str | None:
        """Возвращает URL аватара"""
        return obj.src.url if obj.src else None


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Пример профиля",
            value={
                "fullName": "Annoying Orange",
                "email": "no-reply@mail.ru",
                "phone": "88002000600",
                "avatar": {
                    "src": "https://proprikol.ru/wp-content/uploads/2020/12/kartinki-ryabchiki-14.jpg",
                    "alt": "hello alt",
                },
            },
            request_only=False,
        ),
    ]
)
class ProfileSerializer(serializers.ModelSerializer):
    avatar = AvatarSerializer(
        read_only=True
    )  # сериализация изображения, чтобы было не id, read_only=True - не позволяет изменять, только для GET
    fullName = serializers.CharField(source="full_name", required=False)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # ← строковое поле для фронтенда
    email = serializers.EmailField(source="user.email", required=False)

    class Meta:
        model = Profile
        fields = ["fullName", "email", "phone", "avatar"]

    def validate(self, data):
        """Проверка уникальности телефона и email"""
        phone = data.get("phone")
        if phone:
            if Profile.objects.exclude(id=self.instance.id if self.instance else None).filter(phone=phone).exists():
                raise serializers.ValidationError({"phone": "Телефон уже используется"})

        # Проверка email
        email = data.get("user", {}).get("email") if "user" in data else None
        if email and self.instance:
            if User.objects.exclude(id=self.instance.user.id).filter(email=email).exists():
                raise serializers.ValidationError({"email": "Email уже используется"})

        return data

    def update(self, instance, validated_data):
        # Обновляем поля
        instance.full_name = validated_data.get("full_name", instance.full_name)
        instance.phone = validated_data.get("phone", instance.phone)

        if "user" in validated_data and "email" in validated_data["user"]:
            instance.user.email = validated_data["user"]["email"]
            instance.user.save()

        instance.save()
        return instance


class AvatarUploadSerializer(serializers.Serializer):
    """Сериализатор для загрузки аватара"""

    avatar = serializers.ImageField()
    alt = serializers.CharField(required=False, allow_blank=True)

    def validate_avatar(self, value):
        """Валидация файла аватара"""
        # Проверка размера (2 MB)
        if value.size > 2 * 1024 * 1024:
            raise serializers.ValidationError("Файл слишком большой. Максимум 2MB")

        # Проверка типа
        allowed_types = ["image/jpeg", "image/png", "image/gif"]
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Поддерживаются только JPEG, PNG, GIF")

        # Проверка расширения
        ext = value.name.split(".")[-1].lower()
        if ext not in ["jpg", "jpeg", "png", "gif"]:
            raise serializers.ValidationError("Недопустимое расширение файла")

        return value
