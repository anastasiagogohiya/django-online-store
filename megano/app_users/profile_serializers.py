"""СЕРИАЛИЗАТОРЫ для профиля"""
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from app_users.models import Avatar, Profile


"""Для profile/"""
class AvatarSerializer(serializers.ModelSerializer):
    """Преобразование объекта аватар в JSON
    Аватар - вложенный объект в ProfileSerializer"""
    src = serializers.SerializerMethodField() # спец поле

    class Meta:
        model = Avatar
        fields = ["src", "alt"] # JSON будут {"src":..alt..}

    def get_src(self, obj) -> str:
        """Возвращает URL аватара"""
        return obj.src.url if obj.src else None


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Пример профиля',
            value={
                'full_name': 'Annoying Orange',
                'email': 'no-reply@mail.ru',
                'phone': '88002000600',
                'avatar': {
                    'src': 'https://proprikol.ru/wp-content/uploads/2020/12/kartinki-ryabchiki-14.jpg',
                    'alt': 'hello alt'
                }
            },
            request_only=False,
        ),
    ]
)
class ProfileSerializer(serializers.ModelSerializer):
    avatar = AvatarSerializer(read_only=True) # сериализация изображения, чтобы было не id, read_only=True - не позволяет изменять, только для GET

    class Meta:
        model = Profile
        fields = ["full_name", "email", "phone", "avatar"]