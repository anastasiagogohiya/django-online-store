from rest_framework import serializers
from catalog.models import Review
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample


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
              "date": "2023-05-05 12:12"
            },
            {
              "author": "2Annoying Orange",
              "email": "no-reply@mail.ru",
              "text": "rewrewrwerewrwerwerewrwerwer",
              "rate": 5,
              "date": "2023-05-05 12:12"
            },
            ]
                    ),
                ])
class ReviewSerializer(serializers.ModelSerializer):
	"""Сериализатор для отзывов"""
	author = serializers.CharField(source='author.username', read_only=True)
	email = serializers.EmailField(source='author.email', read_only=True)
	date = serializers.SerializerMethodField()

	class Meta:
		model = Review
		fields = ['author', 'email', 'text', 'rate', 'date']

	def get_date(self, obj):
		"""Форматирует дату в нужный формат"""
		# Формат: "Thu Feb 09 2023 21:39:52 GMT+0100 (Central European Standard Time)"
		return obj.date.strftime("%a %b %d %Y %H:%M:%S")




class ReviewCreateSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='author.full_name', read_only=True)
    email = serializers.EmailField(source='author.email', read_only=True)
    date = serializers.DateTimeField(format="%Y-%m-%d %H:%M", read_only=True)

    class Meta:
        model = Review
        fields = ['author', 'email', 'text', 'rate', 'date']

    def create(self, validated_data):
        request = self.context.get('request')
        review = Review.objects.create(
            product=validated_data.get('product'),
            author=request.user.profile,
            text=validated_data['text'],
            rate=validated_data['rate']
        )
        return review