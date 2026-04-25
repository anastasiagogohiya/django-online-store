""" auth/:
    Авторизация существующего пользователя POST
    Регистрация нового пользователя POST, создание токена.
    Выход из личного кабинета.
"""
from django.contrib.auth import authenticate, logout, login
from django.http import HttpRequest, HttpResponse
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
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
	permission_classes = [AllowAny]
	def post(self, request: HttpRequest) -> HttpResponse:
		# для swagger
		if request.content_type == 'application/json' and isinstance(request.data, dict):
			data = request.data
		else:  # для фронтэнда
			json_string = list(request.data.keys())[0]  # фронтэнд отправляет строку, нужен первый индекс
			data = json.loads(json_string)

		print(f"Попытка входа.....")
		username = data.get("username")
		password = data.get("password")


		print(f"Попытка входа: username={username}")

		user = authenticate(request, username=username, password=password)

		# Проверяем есть ли такой пользователь, если есть получает токен, если нет создаем токен
		if user is not None:
			login(request, user) # Вход через сессию (устанавливает sessionid в cookies)
			token, created = Token.objects.get_or_create(user=user)
			return Response({
				'token': token.key,
				"sessionid": {request.session.session_key},
				'user_id': user.id,
				'username': user.username
			}, status=status.HTTP_200_OK)
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
	permission_classes = [AllowAny] # любой чел может зарегистрироваться
	def post(self, request: HttpRequest) -> HttpResponse:
		# для swagger
		if request.content_type == 'application/json' and isinstance(request.data, dict):
			data = request.data
		else: # для фронтэнда
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
		profile, created = Profile.objects.get_or_create(user=user, full_name=name)

		# логинимся и создаем токен для пользователя
		login(request, user)
		token = Token.objects.create(user=user)

		return Response({"token": token.key,  "user_id": user.id,}, status=status.HTTP_201_CREATED)


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
