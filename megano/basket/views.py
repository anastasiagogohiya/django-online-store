from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
import logging
from .models import Basket, BasketItem
from .serializers import BasketItemSerializer, BasketItemDetailSerializer
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.utils import OpenApiParameter
from django.db import transaction
from rest_framework import serializers
from catalog.models import Product


logger = logging.getLogger(__name__)


class BasketMixin:
    """Миксин для получения корзины (используется во всех вью ф-циях ниже)"""

    def get_or_create_basket(self, request):
        """Получить или создать корзину для авторизованного пользователя или сессии"""
        if request.user.is_authenticated:
            logger.info(f"Получение корзины пользователя {request.user}")
            basket, created = Basket.objects.get_or_create(
                profile=request.user.profile,
                defaults={'session_key': request.session.session_key})
            # Если корзина существовала, но без session_key - обновляем
            if not created and not basket.session_key and request.session.session_key:
                basket.session_key = request.session.session_key
                basket.save(update_fields=['session_key'])
        else:
            if not request.session.session_key:
                request.session.create()
                logger.info(f"Сессия создана: {request.session.session_key}")

            logger.info(f"Получение корзины по сессии: {request.session.session_key}")
            basket, created = Basket.objects.get_or_create(
                session_key=request.session.session_key,
                defaults={'profile': None})

        return basket



class BasketView(BasketMixin, APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Получение корзины",
        tags=['basket'],
        responses=BasketItemDetailSerializer(many=True),)
    def get(self, request):
        """Получение корзины пользователя или сессии"""
        try:
            basket = self.get_or_create_basket(request)
            items = basket.items.select_related('product').all()  # оптимизация запросов
            serializer = BasketItemDetailSerializer(items, many=True)
            logger.info(f'В корзине {len(items)} позиций товаров')
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Ошибка при получении корзины: {e}", exc_info=True)
            return Response(
                {"error": "Ошибка при получении корзины"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        summary="Добавление товара в корзину",
        tags=['basket'],
        request=BasketItemSerializer,
        responses={200: BasketItemDetailSerializer(many=True)},
        examples=[
            OpenApiExample(
                name="Пример тела запроса",
                request_only=True,
                value={"id": 12, "count": 5},
            ),
            OpenApiExample(
                name="Пример успешного ответа",
                response_only=True,
                value=[
                    {
                        "id": 123,
                        "category": 55,
                        "price": 500.67,
                        "count": 12,
                        "date": "2023-02-09T20:39:52Z",
                        "title": "video card",
                        "description": "description of the product",
                        "freeDelivery": True,
                        "images": [
                            {
                                "src": "https://example.com/image.jpg",
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
            ),
        ]
    )
    @transaction.atomic
    def post(self, request):
        """Добавление товара в корзину или обновление количества"""
        logger.info('POST: Попытка добавить/обновить товар в корзину')

        serializer = BasketItemSerializer(data=request.data)

        if not serializer.is_valid():
            logger.info(f'Ошибка валидации: {serializer.errors}')
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Получаем корзину и профиль
        basket = self.get_or_create_basket(request)
        profile = request.user.profile if request.user.is_authenticated else None


        try:
            basket_item = serializer.save(basket=basket, profile=profile)

            # Возвращаем обновлённую корзину
            items = basket.items.select_related('product').all()
            basket_serializer = BasketItemDetailSerializer(items, many=True)
            return Response(basket_serializer.data, status=status.HTTP_200_OK)

        except serializers.ValidationError as e:
            logger.error(f'Ошибка валидации из сериализатора: {e.detail}')
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Неожиданная ошибка: {e}', exc_info=True)
            return Response({"error": "Внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)




    @extend_schema(
        summary="Удаление товара из корзины или уменьшение количества",
        tags=['basket'],
        responses={200: BasketItemDetailSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name='id',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description='ID товара (для тестирования в Swagger)',
            ),
            OpenApiParameter(
                name='count',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,  # Не обязательный, так как может быть в body
                description='Количество для удаления (для тестирования в Swagger)',
            ),
        ],
        examples=[
            OpenApiExample(
                name="Пример запроса через тело (реальный способ)",
                value={"id": 12, "count": 5},
                request_only=True,
                description="Реальный DELETE запрос отправляет JSON в теле",
            ),
        ]
    )
    def delete(self, request):
        """Удаление товара из корзины или уменьшение количества"""
        logger.info('DELETE: Попытка удалить/уменьшить товар в корзине')

        serializer = BasketItemSerializer(data=request.data)

        if not serializer.is_valid():
            logger.info(f'Ошибка валидации DELETE: {serializer.errors}')
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        basket = self.get_or_create_basket(request)
        profile = request.user.profile if request.user.is_authenticated else None

        try:
            # Вызываем метод delete сериализатора (передаем basket и profile)
            basket_item = serializer.delete(basket=basket, profile=profile)

            # Возвращаем обновлённую корзину
            items = basket.items.select_related('product').all()
            basket_serializer = BasketItemDetailSerializer(items, many=True)

            if basket_item is None:
                logger.info('Товар полностью удалён из корзины')
            else:
                logger.info(f'Количество товара уменьшено до {basket_item.count}')

            return Response(basket_serializer.data, status=status.HTTP_200_OK)

        except serializers.ValidationError as e:
            logger.error(f'Ошибка валидации: {e.detail}')
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Неожиданная ошибка: {e}', exc_info=True)
            return Response(
                {"error": "Внутренняя ошибка сервера"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)