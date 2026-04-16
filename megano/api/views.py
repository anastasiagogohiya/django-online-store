from django.shortcuts import render
from django.http import JsonResponse
from random import randrange
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpRequest
from drf_spectacular.utils import extend_schema

User = get_user_model()


"""Авторизация существующего пользователя POST"""
# Название путей auth в swagger
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
		#serialized_data = list(request.data.keys())[0] # первый элемент из списка словаря
		#user_data = json.loads(serialized_data) # из строки в словарь

		username = request.data.get("username")
		password = request.data.get("password")

		user = authenticate(request, username=username, password=password)

		# Проверяем есть ли такой пользователь, если есть получает токен, если нет создаем токен
		if user is not None:
			token, created = Token.objects.get_or_create(user=user)
			return Response({'token': token.key}, status=status.HTTP_200_OK)
		else:
			return Response({'error': 'Неверный username или пароль'}, status=status.HTTP_401_UNAUTHORIZED)



"""Регистрация нового пользователя POST, создание токена."""
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
		full_name = request.data.get("name")
		username = request.data.get('username')
		password = request.data.get('password')

		# Проверка обязательных полей
		if not all([full_name, username, password]):
			return Response(
				{'error': 'Поля name, username и password обязательны'},
				status=status.HTTP_400_BAD_REQUEST
			)

		name_parts = full_name.split(' ', 1) # делю на части имя
		first_name = name_parts[0]
		last_name = name_parts[1] if len(name_parts) > 1 else ''

		if User.objects.filter(username=username).exists():
			return Response(
				{'error': 'Пользователь с таким username уже существует'},
				status=status.HTTP_400_BAD_REQUEST)

		user = User.objects.create_user(username=username,
										first_name=first_name,
										last_name=last_name,
										password=password)

		# Создаем токен для пользователя
		token = Token.objects.create(user=user)

		return Response({"token": token.key}, status=status.HTTP_201_CREATED)


@extend_schema(summary="Выход из системы, удаление токена",
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
	def post(self, request):
		# Если это авторизованный пользователь, то выходим и удаляем токен
		if request.user.is_authenticated:
			request.user.auth_token.delete() # токен удаляем
			logout(request) # выходим
		return Response({'message': 'Вы вышли из системы'}, status=status.HTTP_200_OK)



def banners(request):
	data = [
		{
			"id": "123",
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
					"alt": "any alt text",
				}
			],
			"tags": [
				"string"
			],
			"reviews": 5,
			"rating": 4.6
		},
	]
	return JsonResponse(data, safe=False)

def categories(request):
	data = [
		 {
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
		 }
	 ]
	return JsonResponse(data, safe=False)


def catalog(request):
	print(request.GET)
	price = request.GET.get('filter[maxPrice]')
	print(price)
	data = {
		 "items": [
				 {
					 "id": 123,
					 "category": 123,
					 "price": price,
					 "count": 12,
					 "date": "Thu Feb 09 2023 21:39:52 GMT+0100 (Central European Standard Time)",
					 "title": "video card",
					 "description": "description of the product",
					 "freeDelivery": True,
					 "images": [
					 		{
					 			"src": "https://www.wallpaperbetter.com/wallpaper/620/909/135/cute-gray-kitten-walk-grass-1080P-wallpaper-middle-size.jpg",
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
				 }
		 ],
		 "currentPage": randrange(1, 4),
		 "lastPage": 3
	 }
	return JsonResponse(data)

def productsPopular(request):
	data = [
		{
			"id": "123",
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
		}
	]
	return JsonResponse(data, safe=False)

def productsLimited(request):
	data = [
		{
			"id": "123",
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
		}
	]
	return JsonResponse(data, safe=False)

def sales(request):
	data = {
		'items': [
			{
				"id": 123,
				"price": 500.67,
				"salePrice": 200.67,
				"dateFrom": "05-08",
				"dateTo": "05-20",
				"title": "video card",
				"images": [
						{
							"src": "https://proprikol.ru/wp-content/uploads/2020/12/kartinki-ryabchiki-14.jpg",
							"alt": "hello alt",
						}
				 ],
			}
		],
		'currentPage': randrange(1, 4),
		'lastPage': 3,
	}
	return JsonResponse(data)

def basket(request):
	if(request.method == "GET"):
		print('[GET] /api/basket/')
		data = [
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
			}
		]
		return JsonResponse(data, safe=False)

	elif (request.method == "POST"):
		body = json.loads(request.body)
		id = body['id']
		count = body['count']
		print('[POST] /api/basket/   |   id: {id}, count: {count}'.format(id=id, count=count))
		data = [
			{
				"id": id,
				"category": 55,
				"price": 500.67,
				"count": 13,
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
			}
		]
		return JsonResponse(data, safe=False)

	elif (request.method == "DELETE"):
		body = json.loads(request.body)
		id = body['id']
		print('[DELETE] /api/basket/')
		data = [
			{
			"id": id,
			"category": 55,
			"price": 500.67,
			"count": 11,
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
			}
		]
		return JsonResponse(data, safe=False)





def product(request, id):
	data = {
		"id": 123,
		"category": 55,
		"price": 500.67,
		"count": 12,
		"date": "Thu Feb 09 2023 21:39:52 GMT+0100 (Central European Standard Time)",
		"title": "video card",
		"description": "description of the product",
		"fullDescription": "full description of the product",
		"freeDelivery": True,
		"images": [
				{
					"src": "https://psk68.ru/files/metod/uchebnik_Informatika/user-images/video.png",
					"alt": "hello alt",
				},
								{
					"src": "https://www.asus.com/microsite/2014/vga/gaming_graphics_cards/img/quietly-cool/dust-proof-card.png",
					"alt": "hello alt",
				},
								{
					"src": "https://psk68.ru/files/metod/uchebnik_Informatika/user-images/video.png",
					"alt": "hello alt",
				}
		 ],
		 "tags": [
				{
					"id": 0,
					"name": "Hello world"
				}
		 ],
		"reviews": [
			{
				"author": "Annoying Orange",
				"email": "no-reply@mail.ru",
				"text": "rewrewrwerewrwerwerewrwerwer",
				"rate": 4,
				"date": "2023-05-05 12:12"
			}
		],
		"specifications": [
			{
				"name": "Size",
				"value": "XL"
			}
		],
		"rating": 4.6
	}
	return JsonResponse(data)

def tags(request):
	data = [
		{ "id": 0, "name": 'tag0' },
		{ "id": 1, "name": 'tag1' },
		{ "id": 2, "name": 'tag2' },
	]
	return JsonResponse(data, safe=False)

def productReviews(request, id):
	data = [
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
	return JsonResponse(data, safe=False)

def profile(request):
	if(request.method == 'GET'):
		data = {
			"fullName": "Annoying Orange",
			"email": "no-reply@mail.ru",
			"phone": "88002000600",
			"avatar": {
				"src": "https://proprikol.ru/wp-content/uploads/2020/12/kartinki-ryabchiki-14.jpg",
				"alt": "hello alt",
			}
		}
		return JsonResponse(data)

	elif(request.method == 'POST'):
		data = {
			"fullName": "Annoying Green",
			"email": "no-reply@mail.ru",
			"phone": "88002000600",
			"avatar": {
				"src": "https://proprikol.ru/wp-content/uploads/2020/12/kartinki-ryabchiki-14.jpg",
				"alt": "hello alt",
			}
		}
		return JsonResponse(data)

	return HttpResponse(status=500)

def profilePassword(request):
	print(request.body)
	return HttpResponse(status=200)

def orders(request):
	if(request.method == 'GET'):
		data = [
			{
        "id": 123,
        "createdAt": "2023-05-05 12:12",
        "fullName": "Annoying Orange",
        "email": "no-reply@mail.ru",
        "phone": "88002000600",
        "deliveryType": "free",
        "paymentType": "online",
        "totalCost": 567.8,
        "status": "accepted",
        "city": "Moscow",
        "address": "red square 1",
        "products": [
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
                "alt": "Image alt string"
              }
            ],
            "tags": [
              {
                "id": 12,
                "name": "Gaming"
              }
            ],
            "reviews": 5,
            "rating": 4.6
          }
        ]
      },
			{
        "id": 123,
        "createdAt": "2023-05-05 12:12",
        "fullName": "Annoying Orange",
        "email": "no-reply@mail.ru",
        "phone": "88002000600",
        "deliveryType": "free",
        "paymentType": "online",
        "totalCost": 567.8,
        "status": "accepted",
        "city": "Moscow",
        "address": "red square 1",
        "products": [
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
                "alt": "Image alt string"
              }
            ],
            "tags": [
              {
                "id": 12,
                "name": "Gaming"
              }
            ],
            "reviews": 5,
            "rating": 4.6
          }
        ]
      }
		]
		return JsonResponse(data, safe=False)

	elif(request.method == 'POST'):
		data = {
			"orderId": 123,
		}
		return JsonResponse(data)

	return HttpResponse(status=500)

def order(request, id):
	if(request.method == 'GET'):
		data = {
			"id": 123,
			"createdAt": "2023-05-05 12:12",
			"fullName": "Annoying Orange",
			"email": "no-reply@mail.ru",
			"phone": "88002000600",
			"deliveryType": "free",
			"paymentType": "online",
			"totalCost": 567.8,
			"status": "accepted",
			"city": "Moscow",
			"address": "red square 1",
			"products": [
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
						"alt": "Image alt string"
						}
					],
					"tags": [
						{
						"id": 12,
						"name": "Gaming"
						}
					],
					"reviews": 5,
					"rating": 4.6
				},
			]
		}
		return JsonResponse(data)

	elif(request.method == 'POST'):
		data = { "orderId": 123 }
		return JsonResponse(data)

	return HttpResponse(status=500)

def payment(request, id):
	print('qweqwewqeqwe', id)
	return HttpResponse(status=200)

def avatar(request):
	if request.method == "POST":
# 		print(request.FILES["avatar"])
		return HttpResponse(status=200)