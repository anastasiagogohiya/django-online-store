from rest_framework import serializers
from .models import BasketItem, Basket
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from catalog.models import Product
from catalog.serializers.tag_serializers import TagSerializer


class BasketItemSerializer(serializers.Serializer):
	id = serializers.IntegerField()
	count = serializers.IntegerField()

	def validate_count(self, value):
		if value < 1:
			raise serializers.ValidationError("Количество должно быть положительным")
		return value

	def _check_stock(self, product, requested_count, current_count=0):
		"""Проверка остатков на складе"""
		new_total = current_count + requested_count
		if new_total > product.count:
			available = product.count - current_count
			raise serializers.ValidationError(
				{
					"id": f"Недостаточно товара на складе. Можно добавить не более {available} шт. (доступно всего: {product.count})"})
		return True

	def save(self, **kwargs):
		"""Добавление или увеличение количества"""
		basket = kwargs['basket']
		user_profile = kwargs['profile']
		item_id = self.validated_data['id']
		count = self.validated_data['count']

		# Если есть profile и корзина без профиля - привязываем
		if user_profile and not basket.profile:
			basket.profile = user_profile
			basket.save(update_fields=['profile'])


		# обновление существующей позиции
		try:
			basket_item = BasketItem.objects.get(id=item_id, basket=basket)

			if not basket_item.product.available:
				raise serializers.ValidationError(
					{"id": f"Товар '{basket_item.product.title}' недоступен"})

			self._check_stock(basket_item.product, count, basket_item.count)

			basket_item.count += count
			basket_item.save()
			return basket_item

		except BasketItem.DoesNotExist:
			pass

		# добавление нового товара
		try:
			product = Product.objects.get(id=item_id)

			if not product.available:
				raise serializers.ValidationError(
					{"id": f"Товар '{product.title}' недоступен"})

			existing_item = BasketItem.objects.filter(basket=basket, product=product).first()
			current_count = existing_item.count if existing_item else 0

			self._check_stock(product, count, current_count)

			basket_item, created = BasketItem.objects.get_or_create(
				basket=basket,
				product=product,
				defaults={'count': count})

			if not created:
				basket_item.count += count
				basket_item.save()

			return basket_item

		except Product.DoesNotExist:
			raise serializers.ValidationError(
				{"id": f"Товар с ID {item_id} не найден"})

	def delete(self, **kwargs):
		"""Удаление или уменьшение количества товара"""
		basket = kwargs['basket']
		user_profile = kwargs['profile']
		item_id = self.validated_data['id']
		count = self.validated_data['count']

		if user_profile and not basket.profile:
			basket.profile = user_profile
			basket.save(update_fields=['profile'])


		# Пробуем найти basket_item по id (позиция в корзине)
		try:
			basket_item = BasketItem.objects.get(id=item_id, basket=basket)

			# Если count == 0 или count >= текущего количества - удаляем полностью
			if count == 0 or count >= basket_item.count:
				basket_item.delete()
				return None  # Возвращаем None, если товар удалён
			else:
				# Иначе уменьшаем количество
				basket_item.count -= count
				basket_item.save()
				return basket_item

		except BasketItem.DoesNotExist:
			# Пробуем как product_id
			try:
				product = Product.objects.get(id=item_id)
				basket_item = BasketItem.objects.get(basket=basket, product=product)

				if count == 0 or count >= basket_item.count:
					basket_item.delete()
					return None
				else:
					basket_item.count -= count
					basket_item.save()
					return basket_item

			except (Product.DoesNotExist, BasketItem.DoesNotExist):
				raise serializers.ValidationError(
					{"id": f"Товар с ID {item_id} не найден в корзине"})

@extend_schema_serializer(
examples=[
            OpenApiExample(
                'Пример корзины',
				response_only=True,
                value=[
			{
				"id": 123,
				"category": 55,
				"price": 500.67,
				"count": 12,
				"date": "Thu Feb 09 2023 21:39:52 GMT+0100 (Central European Standard Time)",
				"title": "video card",
				"description": "description of the product",
				"freeDelivery": True,
				"images": [
						{
							"src": "https://proprikol.ru/wp-content/uploads/2020/12/kartinki-ryabchiki-14.jpg",
							"alt": "hello alt",
						}
				 ],
				 "tags": [
						{
							"id": 0,
							"name": "Hello world"
						}
				 ],
				"reviews": 5,
				"rating": 4.6
			},
			{
				"id": 124,
				"category": 55,
				"price": 201.675,
				"count": 5,
				"date": "Thu Feb 09 2023 21:39:52 GMT+0100 (Central European Standard Time)",
				"title": "video card",
				"description": "description of the product",
				"freeDelivery": True,
				"images": [
						{
							"src": "https://proprikol.ru/wp-content/uploads/2020/12/kartinki-ryabchiki-14.jpg",
							"alt": "hello alt",
						}
				 ],
				 "tags": [
						{
							"id": 0,
							"name": "Hello world"
						}
				 ],
				"reviews": 5,
				"rating": 4.6
			}],)])
class BasketItemDetailSerializer(serializers.ModelSerializer):
	"""Для отображения товаров в корзине с полной информацией о продукте"""

	category = serializers.IntegerField(source='product.category.id', read_only=True)
	price = serializers.SerializerMethodField()
	date = serializers.DateTimeField(source='product.date', read_only=True)
	title = serializers.CharField(source='product.title', read_only=True)
	description = serializers.CharField(source='product.description', read_only=True)
	freeDelivery = serializers.BooleanField(source='product.free_delivery', read_only=True)
	images = serializers.SerializerMethodField()
	tags = TagSerializer(source='product.tags', many=True, read_only=True)
	reviews = serializers.IntegerField(source='product.reviews_count', read_only=True)
	rating = serializers.DecimalField(source='product.rating', max_digits=3, decimal_places=2, read_only=True)

	class Meta:
		model = BasketItem
		fields = ['id', 'count', 'category', 'price', 'date', 'title',
				  'description', 'freeDelivery', 'images', 'tags', 'reviews', 'rating']

	def get_price(self, obj):
		"""Возвращает актуальную цену товара (в моделе продукта свойство)"""
		return obj.product.current_price

	def get_images(self, obj):
		"""Возвращает массив изображений продукта с полными URL"""
		request = self.context.get('request')
		product = obj.product
		images_data = []

		for img in product.images.all():
			if img.image and img.image.name:
				image_url = img.image.url
				if request:
					image_url = request.build_absolute_uri(image_url)
				images_data.append({
					"src": image_url,
					"alt": img.alt if hasattr(img, 'alt') and img.alt else product.title
				})

		# Если нет изображений, возвращаем заглушку
		if not images_data:
			default_url = "/static/images/no-image.jpg"
			if request:
				default_url = request.build_absolute_uri(default_url)
			images_data.append({
				"src": default_url,
				"alt": product.title
			})

		return images_data