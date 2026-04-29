"""megano/app_users/profile_views.py
profile/:
ПРОФИЛЬ: Получение, обновление данных, изменение пароля, обновление аватара"""
from drf_spectacular.utils import extend_schema
import logging
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from app_users.models import Profile, Avatar

from app_users.profile_serializers import ProfileSerializer


User = get_user_model()
logger = logging.getLogger(__name__)


class ProfileView(APIView):
	permission_classes = [IsAuthenticated] # только для авторизованных пользователей

	@extend_schema(
		summary="Получение профиля",
		responses={200: ProfileSerializer},
		tags=['profile'],
	)
	def get(self, request):
		logger.info(f"GET /api/profile/ - User: {request.user.username}")
		# profile = Profile.objects.get(user=request.user)
		profile, created = Profile.objects.get_or_create(
			user=request.user,
			defaults={'full_name': request.user.username})

		serializer = ProfileSerializer(profile) # объект в json
		logger.debug(f"Profile data: {serializer.data}")
		return Response(serializer.data) # отправка json в фронтэнд

	@extend_schema(
		summary="Обновление профиля",
		request=ProfileSerializer,
		responses={200: ProfileSerializer, 400: None},
		tags=['profile'],
	)
	def post(self, request):
		"""В данном методе не ловится avatar, в сериализаторе read_only=True"""
		logger.info(f"POST /api/profile/ - User: {request.user.username}")
		logger.info(f"Received data: {request.data}")

		# profile = Profile.objects.get(user=request.user)

		profile, created = Profile.objects.get_or_create(
			user=request.user,
			defaults={
				'full_name': request.user.username,
				'email': request.user.email or ''
			}
		)
		if created:
			logger.info(f"Created new profile for user: {request.user.username}")

		print(f"VIEW: Текущий profile.full_name = '{profile.full_name}'")

		serializer = ProfileSerializer(profile, data=request.data, partial=True)

		if serializer.is_valid(): # проверка данных от пользователя
			serializer.save()
			logger.info(f"Profile updated successfully for user: {request.user.username}")
			logger.debug(f"Updated data: {serializer.data}")
			return Response(serializer.data)
		return Response({"message": "Введите корректные данные."}, serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Смена пароля пользователя",
    request={
        'application/json': {
            'properties': {
                'currentPassword': {'type': 'string', 'description': 'Текущий пароль', 'example': 'oldpassword'},
                'newPassword': {'type': 'string', 'description': 'Новый пароль', 'example': 'newpassword'}
            },
		'required': ['currentPassword', 'newPassword']
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
		logger.info(f"POST /api/profile/password/ - User: {request.user.username}")

		user = request.user # юзер из токена
		current_password = request.data.get('currentPassword')
		new_password = request.data.get('newPassword')

		if not current_password or not new_password:
			return Response({"message": "Текущий и новый пароль обязательны"}, status=status.HTTP_400_BAD_REQUEST)

		# Проверка старого пароля
		if not user.check_password(current_password):
			return Response({"message": "Вы ввели неправильный текущий пароль"}, status=status.HTTP_400_BAD_REQUEST)

		user.set_password(new_password) # хэширование автоматом
		user.save()
		logger.info(f"Password changed successfully for user: {request.user.username}")

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
		file = request.FILES.get('avatar')
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

		logger.info(f"Avatar uploaded successfully for user: {request.user.username}")

		return Response({
			'src': avatar.src.url,
			'alt': avatar.alt
		}, status=status.HTTP_200_OK)
