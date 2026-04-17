"""СЕРИАЛИЗАТОРЫ для каталога"""
from rest_framework import serializers
from catalog.models import Category

from drf_spectacular.utils import extend_schema_serializer, OpenApiExample

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

