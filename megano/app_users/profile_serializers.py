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
                'fullName': 'Annoying Orange',
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
    fullName = serializers.CharField(source='full_name', required=False)
    phone = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # ← строковое поле для фронтенда

    class Meta:
        model = Profile
        fields = ["fullName", "email", "phone", "avatar"]

    def validate(self, data):
        return data

    def update(self, instance, validated_data):
        print(f"SERIALIZER update - validated_data: {validated_data}")

        # Обновляем full_name
        if 'full_name' in validated_data:
            instance.full_name = validated_data['full_name']

        # Обновляем phone
        if 'phone' in validated_data:
            instance.phone = validated_data['phone']

        # Обновляем email пользователя
        if 'email' in validated_data:
            instance.email = validated_data['email']

        instance.save()

        return instance
