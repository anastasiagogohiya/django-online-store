from rest_framework.views import APIView
import logging
from rest_framework.response import Response
from rest_framework import status
from .models import Order, OrderItem, OrderStatus
from .serializers import OrderSerializer, CreateOrderSerializer
from .serializers import OrderIdSerializer
from basket.models import BasketItem, Basket
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.utils import OpenApiExample
from megano.permissions import IsAuth
from .utils import check_profile, get_user_basket, check_basket_not_empty
from megano.decorators import catch_all_errors
from django.db import transaction

logger = logging.getLogger(__name__)



class OrderView(APIView):
    permission_classes = [IsAuth]

    @extend_schema(
        summary="Получение заказов",
        description="Возвращает список заказов",
        tags=['order'],
        responses=OrderSerializer(many=True))
    @catch_all_errors
    def get(self, request):
        logger.info(f'GET Пользователь {request.user.username} запрашивает заказы')
        # Проверяем профиль
        profile, error = check_profile(request) # вынесен в utils чтобы сократить код
        if error:
            return error

        orders = Order.objects.filter(profile=profile).order_by('-created_at') # заказы пользователя, сначала новые
        serializer = OrderSerializer(orders, many=True) # отправляем в сериализатор профиль и там происходит валидация
        return Response(serializer.data, status=status.HTTP_200_OK)


    @extend_schema(
        summary="Создание заказа",
        tags=['order'],
        request=CreateOrderSerializer,
        responses={200: OrderIdSerializer},
        examples=[
            OpenApiExample(
                'Пример создания заказа',
                request_only=True,
                value={
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
                            "src": "https://psk68.ru/files/metod/uchebnik_Informatika/user-images/video.png",
                            "alt": "hello alt",
                        },
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
            ),
            OpenApiExample(
                "Пример тела ответа",
                response_only=True,
                value={"orderId": 123},
            ),
        ]
    )
    @catch_all_errors
    @transaction.atomic
    def post(self, request):
        logger.info(f'Пользователь {request.user.username} пытается создать заказ')

        # 1. Проверяем профиль
        profile, error = check_profile(request)
        if error:
            return error

        # 2. Получаем корзину
        basket, error = get_user_basket(profile)
        if error:
            return error

        # 3. Проверяем, что корзина не пуста
        is_empty, error = check_basket_not_empty(basket)
        if is_empty:
            return error

        # 4. Валидируем входящие данные от фронтенда
        products_serializer = CreateOrderSerializer(data=request.data, many=True)
        if not products_serializer.is_valid():
            logger.warning(f'Ошибка валидации входящих данных: {products_serializer.errors}')
            return Response(products_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        logger.info('Валидация входящих данных успешно пройдена')
        products_from_frontend = products_serializer.validated_data

        # 5. Проверяем соответствие товаров корзине
        basket_items = basket.items.select_related('product').all()
        basket_dict = {item.id: item for item in basket_items}

        for frontend_item in products_from_frontend:
            basket_item_id = frontend_item.get('id')
            if basket_item_id not in basket_dict:
                return Response(
                    {"error": f"Товар с id={basket_item_id} не найден в вашей корзине"},
                    status=status.HTTP_400_BAD_REQUEST)

        # Проверяем количество
        for frontend_item in products_from_frontend:
            basket_item_id = frontend_item.get('id')
            basket_item = basket_dict[basket_item_id]
            if frontend_item.get('count') > basket_item.count:
                logger.warning(
                    f'Количество не совпадает: фронтэнд={frontend_item.get("count")}, '
                    f'корзина={basket_item.count}. Использую из корзины.')

        # 6. Данные доставки (пока пустые, заполнятся позже в OrderDetailView)
        delivery_data = {
            'city': '',
            'address': '',
            'deliveryType': '',
            'paymentType': '',}

        # 7. Создаем заказ через миксин
        order = Order.create_from_basket(basket, profile, products_from_frontend, delivery_data)

        logger.info(f'Заказ #{order.id} успешно создан')
        return Response({"orderId": order.id}, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    permission_classes = [IsAuth]

    @extend_schema(
        summary="Получение деталей заказа",
        description="Возвращает информацию о конкретном заказе по его ID",
        tags=['order'],
        parameters=[
            OpenApiParameter(
                name='id',
                description='ID заказа',
                required=True,
                type=int,
                location='path',
            ),
        ],
        responses={200: OrderSerializer, 404: "Заказ не найден"}
    )
    @catch_all_errors
    def get(self, request, id=None):
        logger.info(f'Пользователь запрашивает данные по заказу id={id}')
        profile, error = check_profile(request)
        if error:
            return error
        order = Order.objects.get(id=id, profile=profile)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Заполнение деталей заказа",
        tags=['order'],
        parameters=[
            OpenApiParameter(
                name='id',
                description='ID заказа',
                required=True,
                type=int,
                location='path',
            ),
        ],
        request=OrderSerializer,
        examples=[
            OpenApiExample(
                'Пример заполнения деталей заказа',
                request_only=True,
                value={
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
          "src": "/3.png",
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
            ),
        ],
    )
    @catch_all_errors
    def post(self, request, id=None):
        logger.info(f'POST Пользователь заполняет детали заказа id{id}')
        # Здесь пользователь ФИО, email, телефон (заполнено автоматом если в профиле заполнено)
        # Здесь пользователь заполняет Город доставки, Адрес доставки
        # Здесь пользователь заполняет Тип доставки
        # Здесь пользователь заполняет Тип оплаты
        profile, error = check_profile(request)
        if error:
            return error

        order = Order.objects.get(id=id, profile=profile)
        # Логируем конкретные поля
        logger.info(f'deliveryType: {request.data.get("deliveryType")}')
        logger.info(f'paymentType: {request.data.get("paymentType")}')
        logger.info(f'city: {request.data.get("city")}')
        logger.info(f'address: {request.data.get("address")}')

        # Устанавливаем статус ACCEPTED (Принят)
        if order.status == OrderStatus.CREATED or not order.status:
            order.status = OrderStatus.ACCEPTED
            logger.info(f'Статус заказа #{id} изменен с created на accepted')

        order.save()

        # Частичное обновление (только переданные поля)
        serializer = OrderSerializer(order, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            logger.info(f'Заказ #{id} успешно обновлен')
            return Response({'orderId': order.id}, status=status.HTTP_200_OK)