from rest_framework import serializers

from catalog.models import ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    """Сериализатор для изображений товара"""

    src = serializers.ImageField(source="image", read_only=True)
    alt = serializers.CharField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ["src", "alt"]
