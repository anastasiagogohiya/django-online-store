"""СЕРИАЛИЗАТОРЫ CatalogSerializer, CategorySerializer"""
from rest_framework import serializers
from catalog.models import Category, Product, Tag, ProductImage
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample, extend_schema_field

@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Пример категории',
            value={
			 "id": 123,
			 "title": "video card",
			 "image": {
				"src": "https://proprikol.ru/wp-content/uploads/2020/12/kartinki-ryabchiki-14.jpg",
				 "alt": "Image alt string"
			 },
			 "subcategories": [
				 {
					 "id": 123,
					 "title": "video card",
					 "image": {
							"src": "https://proprikol.ru/wp-content/uploads/2020/12/kartinki-ryabchiki-14.jpg",
						 	"alt": "Image alt string"
					 }
				 }
			 ]
		 },
        ),
    ]
)
class CategorySerializer(serializers.ModelSerializer):
	image = serializers.SerializerMethodField() # вложенное поле

	class Meta:
		model = Category
		fields = ['id', 'title', 'image'] # поле subcategories динамическое

	@extend_schema_field(OpenApiTypes.OBJECT) # терминал писал предупрждение
	def get_image(self, obj):
		"""Возвращает словарь с src и alt для изображения"""
		if obj.image and obj.image.name:
			return {
				"src": obj.image.url,
				"alt": obj.title}
		return {
			"src": "",
			"alt": obj.title}

	def to_representation(self, instance):
		"""Переопределяем метод для динамического добавления subcategories"""
		data = super().to_representation(instance)

		# Получаем подкатегории
		subcategories = instance.subcategories.all()

		# Добавляем поле subcategories только если есть подкатегории
		if subcategories.exists():
			data['subcategories'] = CategorySerializer(
				subcategories,
				many=True,
				context=self.context
			).data

		return data


class ProductImageSerializer(serializers.ModelSerializer):
	"""Сериализатор для изображений товара"""
	src = serializers.ImageField(source='image', read_only=True)
	alt = serializers.CharField(read_only=True)

	class Meta:
		model = ProductImage
		fields = ['src', 'alt']


class TagSerializer(serializers.ModelSerializer):
	"""Сериализатор для тегов"""

	class Meta:
		model = Tag
		fields = ['id', 'name']


class CatalogSerializer(serializers.ModelSerializer):
	"""Сериализатор для каталога"""
	images = serializers.SerializerMethodField()
	tags = TagSerializer(many=True, read_only=True)
	reviews = serializers.IntegerField(source='reviews_count', read_only=True)
	rating = serializers.DecimalField(max_digits=3, decimal_places=2, read_only=True)
	freeDelivery = serializers.BooleanField(source='free_delivery', read_only=True)

	class Meta:
		model = Product
		fields = ['id', 'category', 'price', 'count', 'date', 'title', 'description',
				  'freeDelivery', 'images', 'tags', 'reviews', 'rating']

	@extend_schema_field(OpenApiTypes.OBJECT)
	def get_images(self, obj):
		"""Возвращает массив изображений"""
		images_data = []

		# Получаем все изображения товара
		for img in obj.images.all():
			if img.image and img.image.name:
				images_data.append({
					"src": img.image.url,
					"alt": obj.title
				})

		# псевдоизоюбражение, иначе фронтэнд пишет у меня ошибку
		if not images_data:
			images_data.append({
				"src": "https://noimage/",
				"alt": obj.title
			})

		return images_data

