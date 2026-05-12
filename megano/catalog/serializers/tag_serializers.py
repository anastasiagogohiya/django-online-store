from rest_framework import serializers

from catalog.models import Tag


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов"""

    class Meta:
        model = Tag
        fields = ["id", "name"]
