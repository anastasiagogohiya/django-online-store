""" profile/:
ПРОФИЛЬ: Получение, обновление данных, изменение пароля, обновление аватара"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from app_users.models import Profile, Avatar

from app_users.profile_serializers import ProfileSerializer


User = get_user_model()


# Не проверен код на фронтэнде, в swagger все ок.

class ProfileView(APIView):
	permission_classes = [IsAuthenticated] # только для авторизованных пользователей

	@extend_schema(
		summary="Получение профиля",
		responses={200: ProfileSerializer},
		tags=['profile'],
	)
	def get(self, request):
		profile = Profile.objects.get(user=request.user) # объект
		serializer = ProfileSerializer(profile) # объект в json
		return Response(serializer.data) # отправка json в фронтэнд

	@extend_schema(
		summary="Обновление профиля",
		request=ProfileSerializer,
		responses={200: ProfileSerializer, 400: None},
		tags=['profile'],
	)
	def post(self, request):
		"""В данном методе не ловится avatar, в сериализаторе read_only=True"""
		profile = Profile.objects.get(user=request.user)

		serializer = ProfileSerializer(profile, data=request.data, partial=True)
		if serializer.is_valid(): # проверка данных от пользователя
			serializer.save()
			return Response(serializer.data)
		return Response({"message": "Введите корректные данные."}, serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Смена пароля пользователя",
    request={
        'application/json': {
            'properties': {
                'current_password': {'type': 'string', 'description': 'Текущий пароль', 'example': 'oldpassword'},
                'new_password': {'type': 'string', 'description': 'Новый пароль', 'example': 'newpassword'}
            },
		'required': ['current_password', 'new_password']
        }
    },

    responses={
        200: {
            'properties': {
                'message': {'type': 'string'}
            }
        },
        400: {
            'properties': {
                'message': {'type': 'string'}
            }
        }
    },
    tags=['profile'],
)
class ProfilePasswordView(APIView):
	permission_classes = [IsAuthenticated] # только для авторизованный пользователей
	def post(self, request):
		user = request.user # юзер из токена
		current_password = request.data.get('current_password')
		new_password = request.data.get('new_password')

		if not current_password or not new_password:
			return Response({"message": "Текущий и новый пароль обязательны"}, status=status.HTTP_400_BAD_REQUEST)

		# Проверка старого пароля
		if not user.check_password(current_password):
			return Response({"message": "Вы ввели неправильный текущий пароль"}, status=status.HTTP_400_BAD_REQUEST)

		user.set_password(new_password) # хэширование автоматом
		user.save()

		return Response({"message": "Вы успешно поменяли пароль"}, status=status.HTTP_200_OK)


@extend_schema(
	summary="Загрузка аватара",
	request={
		'multipart/form-data': {
			'type': 'object',
			'properties': {
				'file': {
					'type': 'string',
					'format': 'binary',
					'description': 'Файл изображения'
				},
				'alt': {
					'type': 'string',
					'description': 'Описание изображения'
				}
			},
			'required': ['file']
		}
	},
	responses={
		200: {
			'type': 'object',
			'properties': {
				'src': {'type': 'string'},
				'alt': {'type': 'string'}
			}
		},
		400: {
			'type': 'object',
			'properties': {
				'error': {'type': 'string'}
			}
		}
	},
	tags=['profile'],
)
class ProfileAvatarUploadView(APIView):
	permission_classes = [IsAuthenticated]
	parser_classes = [MultiPartParser, FormParser]  # для загрузки файлов

	def post(self, request):
		file = request.FILES.get('file')
		if not file:
			return Response({'error': 'Нет файла'}, status=status.HTTP_400_BAD_REQUEST)

		# Создаем аватар
		avatar = Avatar.objects.create(
			src=file,
			alt=request.data.get('alt', '')
		)

		# Привязываем к профилю
		profile = Profile.objects.get(user=request.user)
		profile.avatar = avatar
		profile.save()

		return Response({
			'src': avatar.src.url,
			'alt': avatar.alt
		}, status=status.HTTP_200_OK)
