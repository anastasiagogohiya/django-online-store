""" auth/:
    Авторизация существующего пользователя POST
    Регистрация нового пользователя POST, создание токена.
    Выход из личного кабинета.
"""
from django.contrib.auth import authenticate, logout
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import json
from app_users.models import Profile, Avatar

User = get_user_model()


@extend_schema(
    summary="Авторизация существующего пользователя",
    request={
        'application/json': {
            'properties': {
                'username': {'type': 'string'},
                'password': {'type': 'string'}
            }
        }
    },
	responses={
		200: {
			'type': 'object',
			'properties': {
				'token': {'type': 'string'}
			}
		},
		401: {
			'type': 'object',
			'properties': {
				'error': {'type': 'string'}
			}
		}
	},
	tags=['auth'],
)
class SignInView(APIView):
	def post(self, request: HttpRequest) -> HttpResponse:
		json_string = list(request.data.keys())[0]  # фронтэнд отправляет строку, нужен первый индекс
		data = json.loads(json_string)

		username = data.get("username")
		password = data.get("password")

		user = authenticate(request, username=username, password=password)

		# Проверяем есть ли такой пользователь, если есть получает токен, если нет создаем токен
		if user is not None:
			token, created = Token.objects.get_or_create(user=user)
			return Response({'token': token.key}, status=status.HTTP_200_OK)
		else:
			return Response({'error': 'Неверный username или пароль'}, status=status.HTTP_401_UNAUTHORIZED)


@extend_schema(
    summary="Регистрация нового пользователя",
    request={
        'application/json': {
            'properties': {
                'name': {'type': 'string', 'description': 'Имя пользователя'},
                'username': {'type': 'string', 'format': 'username'},
                'password': {'type': 'string', 'format': 'password'}
            },
        }
    },
	responses={
		201: {
			'type': 'object',
			'properties': {
				'token': {'type': 'string'}
			}
		},
		400: {
			'type': 'object',
			'properties': {
				'error': {'type': 'string'}
			}
		}
	},
	tags=['auth'],
)
class SignUpView(APIView):
	def post(self, request: HttpRequest) -> HttpResponse:
		print("=" * 60)
		print("PATH:", request.path)
		print("CONTENT_TYPE:", request.content_type)
		print("DATA:", request.data)
		print("POST:", request.POST)
		print("GET:", request.GET)
		print("=" * 60)

		json_string = list(request.data.keys())[0] # фронтэнд отправляет строку, нужен первый индекс
		data = json.loads(json_string)
		name = data.get('fullName') or data.get('name')
		username = data.get('username')
		password = data.get('password')

		# Проверка
		if not all([name, username, password]):
			return Response(
				{
					'error': f'Поля name, username и password обязательны. Получено: name={name}, username={username}, password={"*" if password else None}'},
				status=status.HTTP_400_BAD_REQUEST
			)

		if User.objects.filter(username=username).exists():
			return Response(
				{'error': 'Пользователь с таким username уже существует'},
				status=status.HTTP_400_BAD_REQUEST)

		user = User.objects.create_user(username=username,
										password=password)
		profile = Profile.objects.create(user=user, full_name=name)

		# Создаем токен для пользователя
		token = Token.objects.create(user=user)

		return Response({"token": token.key}, status=status.HTTP_201_CREATED)


@extend_schema(summary="Выход из системы, удаление токена",
				request=None,
				responses={
						200: {
							'type': 'object',
							'properties': {
								'message': {'type': 'string'}
							}
						}
					},
			   tags=['auth'],)
class SignOutView(APIView):
	permission_classes = [IsAuthenticated]
	def post(self, request):
		if request.user.is_authenticated:
			request.user.auth_token.delete() # токен удаляем
			logout(request) # выходим
		return Response({'message': 'Вы вышли из системы'}, status=status.HTTP_200_OK)
