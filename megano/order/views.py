import logging
from typing import Optional

from django.db import transaction
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from megano.decorators import catch_all_errors
from megano.permissions import IsAuth

from .models import Order
from .serializers import CreateOrderSerializer, OrderIdSerializer, OrderSerializer
from .services import create_order_from_basket, update_order_details
from .utils import check_basket_not_empty, check_profile, get_user_basket

logger = logging.getLogger(__name__)


class OrderView(APIView):

    @extend_schema(
        summary="Получение заказов",
        description="Возвращает список заказов",
        tags=["order"],
        responses=OrderSerializer(many=True),
    )
    @catch_all_errors
    def get(self, request: Request) -> Response:
        logger.info(
            f"GET Пользователь {request.user.username if request.user.is_authenticated else 'anonymous'} "
            f"запрашивает заказы"
        )
        # Проверяем профиль
        profile, error = check_profile(request)  # вынесен в utils чтобы сократить код
        if error:
            return error

        orders = Order.objects.filter(profile=profile).order_by("-created_at")  # заказы пользователя, сначала новые
        serializer = OrderSerializer(orders, many=True)  # отправляем в сериализатор профиль и там происходит валидация
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Создание заказа",
        tags=["order"],
        request=CreateOrderSerializer,
        responses={200: OrderIdSerializer},
        examples=[
            OpenApiExample(
                "Пример создания заказа",
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
                    "tags": [{"id": 0, "name": "Hello world"}],
                    "reviews": 5,
                    "rating": 4.6,
                },
            ),
            OpenApiExample(
                "Пример тела ответа",
                response_only=True,
                value={"orderId": 123},
            ),
        ],
    )
    @catch_all_errors
    @transaction.atomic
    def post(self, request: Request) -> Response:
        logger.info(
            f"Пользователь {request.user.username if request.user.is_authenticated else 'anonymous'} "
            f"пытается создать заказ"
        )

        profile = request.user.profile if request.user.is_authenticated else None

        # Получаем или создаём session_key для анонимных пользователей
        session_key = request.session.session_key
        if not session_key:
            request.session.save()  # создаём сессию, если её ещё нет
            session_key = request.session.session_key

        basket, error = get_user_basket(profile, session_key)
        if error:
            return error

        # Проверяем, что корзина не пуста
        is_empty, error = check_basket_not_empty(basket)
        if is_empty:
            return error

        # Валидируем входящие данные от фронтенда
        products_serializer = CreateOrderSerializer(data=request.data, many=True)
        if not products_serializer.is_valid():
            logger.warning(f"Ошибка валидации входящих данных: {products_serializer.errors}")
            return Response(products_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        products_from_frontend = products_serializer.validated_data

        # в сервисе логика создания заказа из корзинки
        order = create_order_from_basket(
            basket=basket, products_data=products_from_frontend, profile=profile, session_key=session_key
        )
        logger.info(f"Заказ #{order.id} успешно создан")
        return Response({"orderId": order.id}, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    permission_classes = [IsAuth]

    @extend_schema(
        summary="Получение деталей заказа",
        description="Возвращает информацию о конкретном заказе по его ID",
        tags=["order"],
        parameters=[
            OpenApiParameter(
                name="id",
                description="ID заказа",
                required=True,
                type=int,
                location="path",
            ),
        ],
        responses={200: OrderSerializer, 404: "Заказ не найден"},
    )
    @catch_all_errors
    def get(self, request: Request, id: Optional[int] = None) -> Response:
        logger.info(f"Пользователь запрашивает данные по заказу id={id}")
        profile, error = check_profile(request)
        if error:
            return error
        order = Order.objects.get(id=id, profile=profile)
        # Пересчитываем актуальную стоимость товаров и доставки
        order.calculate_total_cost()
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Заполнение деталей заказа",
        tags=["order"],
        parameters=[
            OpenApiParameter(
                name="id",
                description="ID заказа",
                required=True,
                type=int,
                location="path",
            ),
        ],
        request=OrderSerializer,
        examples=[
            OpenApiExample(
                "Пример заполнения деталей заказа",
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
                            "images": [{"src": "/3.png", "alt": "Image alt string"}],
                            "tags": [{"id": 12, "name": "Gaming"}],
                            "reviews": 5,
                            "rating": 4.6,
                        }
                    ],
                },
            ),
        ],
    )
    @catch_all_errors
    def post(self, request: Request, id: Optional[int] = None) -> Response:
        logger.info(f"POST Пользователь заполняет детали заказа id{id}")
        # Здесь пользователь ФИО, email, телефон (заполнено автоматом если в профиле заполнено)
        # Здесь пользователь заполняет Город доставки, Адрес доставки
        # Здесь пользователь заполняет Тип доставки
        # Здесь пользователь заполняет Тип оплаты
        profile, error = check_profile(request)
        if error:
            return error

        order = Order.objects.get(id=id, profile=profile)
        # Логируем конкретные поля
        logger.info(f"deliveryType: {request.data.get('deliveryType')}")
        logger.info(f"paymentType: {request.data.get('paymentType')}")
        logger.info(f"city: {request.data.get('city')}")
        logger.info(f"address: {request.data.get('address')}")

        # Частичное обновление (только переданные поля)
        serializer = OrderSerializer(
            order, data=request.data, partial=True
        )  # здесь передабтся данные в фронтэнд (c учетом доставки)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Вызов сервиса обновления
        updated_order = update_order_details(order, serializer.validated_data)

        logger.info(f"Заказ #{id} успешно обновлен, цена заказа с учетом доставки {order.total_cost}")  # цена корректна
        return Response({"orderId": updated_order.id, "totalCost": updated_order.total_cost}, status=status.HTTP_200_OK)
