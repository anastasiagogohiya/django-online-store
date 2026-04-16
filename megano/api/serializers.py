from rest_framework import serializers
from app_users.models import Avatar, Profile

"""СЕРИАЛИЗАТОРЫ"""

class AvatarSerializer(serializers.ModelSerializer):
    """Преобразование объекта аватар в JSON
    Аватар - вложенный объект в ProfileSerializer"""
    src = serializers.SerializerMethodField() # спец поле

    class Meta:
        model = Avatar
        fields = ["src", "alt"] # JSON будут {"src":..alt..}

    def get_src(self, obj):
        """Возвращает URL аватара"""
        return obj.src.url if obj.src else None


class ProfileSerializer(serializers.ModelSerializer):
    avatar = AvatarSerializer() # сериализация изображения, чтобы было не id

    class Meta:
        model = Profile
        fields = ["full_name", "email", "phone", "avatar"]
