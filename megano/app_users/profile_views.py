"""megano/app_users/profile_views.py
profile/:
ПРОФИЛЬ: Получение, обновление данных, изменение пароля, обновление аватара"""
from drf_spectacular.utils import extend_schema
import logging
from rest_framework import status
from rest_framework.request import Request
from django.contrib.auth import get_user_model
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from app_users.models import Profile, Avatar
from app_users.profile_serializers import ProfileSerializer, AvatarUploadSerializer
from megano.permissions import IsAuth
from app_users.utils import get_profile
from megano.decorators import catch_all_errors

User = get_user_model()
logger = logging.getLogger(__name__)


class ProfileView(APIView):
	permission_classes = [IsAuth] # только для авторизованных пользователей

	@extend_schema(
		summary="Получение профиля",
		responses={200: ProfileSerializer},
		tags=['profile'],
	)
	@catch_all_errors
	def get(self, request: Request) -> Response:
		logger.info(f"GET /api/profile/ - User: {request.user.username}")
		profile = get_profile(request.user)
		serializer = ProfileSerializer(profile) # объект в json
		logger.debug(f"Profile data: {serializer.data}")
		return Response(serializer.data) # отправка json в фронтэнд

	@extend_schema(
		summary="Обновление профиля",
		request=ProfileSerializer,
		responses={200: ProfileSerializer, 400: None},
		tags=['profile'],
	)
	@catch_all_errors
	def post(self, request: Request) -> Response:
		"""В данном методе не ловится avatar, в сериализаторе read_only=True"""
		logger.info(f"POST /api/profile/ - User: {request.user.username}")

		profile = get_profile(request.user)
		serializer = ProfileSerializer(profile, data=request.data, partial=True)

		if serializer.is_valid(): # проверка данных от пользователя
			serializer.save()
			logger.info(f"Profile updated successfully for user: {request.user.username}")
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
	permission_classes = [IsAuth] # только для авторизованный пользователей

	@catch_all_errors
	def post(self, request: Request) -> Response:
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
				'avatar': {
					'type': 'string',
					'format': 'binary',
					'description': 'Файл изображения'
				},
				'alt': {
					'type': 'string',
					'description': 'Описание изображения'
				}
			},
			'required': ['avatar']
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
	permission_classes = [IsAuth]
	parser_classes = [MultiPartParser, FormParser]  # для загрузки файлов

	@catch_all_errors
	def post(self, request: Request) -> Response:
		logger.info(f'Пользователь пытается загрузить аватар...')
		serializer = AvatarUploadSerializer(data=request.data)
		if not serializer.is_valid():
			return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

		validated_data = serializer.validated_data
		file = validated_data['avatar']
		alt = validated_data.get('alt', '')

		profile = Profile.objects.get(user=request.user)

		# удаляем старый аватар, иначе он засоряет БД
		if profile.avatar:
			old_avatar = profile.avatar
			profile.avatar = None  # разрываем связь
			profile.save()  # сохраняем профиль
			old_avatar.delete()

		# Создаем аватар
		avatar = Avatar.objects.create(
			src=file,
			alt=request.data.get('alt', ''))

		profile.avatar = avatar
		profile.save()

		logger.info(f"Avatar uploaded successfully for user: {request.user.username}")

		return Response({
			'src': avatar.src.url,
			'alt': avatar.alt
		}, status=status.HTTP_200_OK)