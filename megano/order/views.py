from rest_framework.permissions import AllowAny, IsAuthenticated
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

logger = logging.getLogger(__name__)



class OrderView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Получение заказов",
        description="Возвращает список заказов",
        tags=['order'],
        responses=OrderSerializer(many=True))
    def get(self, request):
        try:
            logger.info(f'GET Пользователь {request.user.username} запрашивает заказы')
            profile = request.user.profile
            orders = Order.objects.filter(profile=profile).order_by('-created_at') # заказы пользователя, сначала новые
            serializer = OrderSerializer(orders, many=True) # отправляем в сериализатор профиль и там происходит валидация
            return Response(serializer.data, status=status.HTTP_200_OK)
        except AttributeError:
            logger.error(f"У пользователя {request.user.id} нет профиля")
            return Response(
                {"error": "Профиль пользователя не найден"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Ошибка при получении заказов: {str(e)}")
            return Response(
                {"error": "Внутренняя ошибка сервера"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    def post(self, request):
        logger.info(f'Пользователь {request.user.username} пытается создать заказ')

        # Проверяем наличие профиля
        try:
            profile = request.user.profile
            logger.info(f'Профиль найден: ID={profile.id}')
        except AttributeError:
            logger.error('У пользователя нет профиля!')
            return Response(
                {"error": "У пользователя не заполнен профиль. Пожалуйста, заполните профиль."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Валидируем товары из корзины
        products_serializer = CreateOrderSerializer(data=request.data, many=True)

        if not products_serializer.is_valid():
            logger.warning(f'Ошибка валидации: {products_serializer.errors}')
            return Response(products_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f'Валидация переданных данных из фронтэнда успешно прошла.')

        # Получаем валидированные товары
        products_data = products_serializer.validated_data

        # Рассчитываем общую стоимость
        total_cost = sum(item['price'] * item['count'] for item in products_data)

        # Создаем заказ
        try:
            new_order = Order.objects.create(
                profile=profile,
                delivery_type='delivery',
                payment_type='online',
                city='',
                address_delivery='',
                total_cost=total_cost,
                status=''
            )
            logger.info(f'Заказ успешно создан: ID={new_order.id}')
        except Exception as e:
            logger.error(f'Ошибка при создании заказа: {e}')
            return Response({"error": f"Не удалось создать заказ: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Добавляем товары в заказ
        logger.info(f'Всего товаров для добавления: {len(products_data)}')

        for idx, item_data in enumerate(products_data, 1):
            logger.info(f'Данные товара: {item_data}')

            try:
                basket_item_id = item_data.get('id')  # Это ID записи в корзине (BasketItem.id)
                quantity = item_data.get('count')
                price_from_frontend = item_data.get('price')

                logger.info(f'BasketItem ID: {basket_item_id}')
                logger.info(f'Quantity: {quantity}')

                # Получаем реальный товар из базы данных по BasketItem
                try:
                    basket_item = BasketItem.objects.select_related('product', 'basket').get(
                        id=basket_item_id,
                        basket__profile=profile  # Проверяем, что корзина принадлежит пользователю
                    )

                    product = basket_item.product
                    real_product_id = product.id
                    real_quantity = basket_item.count
                    real_price = product.price

                    # Проверяем соответствие данных (лог предупреждения, но не блокируем)
                    if real_quantity != quantity:
                        logger.warning(
                            f'Количество не совпадает: фронтэнд={quantity}, корзина={real_quantity}. Использую из корзины.')
                        quantity = real_quantity

                    if real_price != price_from_frontend:
                        logger.warning(
                            f'Цена не совпадает: фронтэнд={price_from_frontend}, БД={real_price}. Использую из БД.')

                except BasketItem.DoesNotExist:
                    logger.error(f'BasketItem с ID={basket_item_id} не найден или не принадлежит пользователю!')
                    # Удаляем заказ и возвращаем ошибку
                    new_order.delete()
                    return Response(
                        {"error": f"Товар в корзине не найден. Возможно, корзина была изменена."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Создаем OrderItem с реальными данными из БД
                logger.info('Пытаемся создать OrderItem...')

                order_item = OrderItem.objects.create(
                    order=new_order,
                    product=product,  # Передаем объект Product, не ID
                    quantity=quantity,
                    price_at_time=real_price  # Используем цену из БД
                )

            except Exception as e:
                # Логируем состояние БД перед удалением заказа
                logger.info(f'Проверка заказа #{new_order.id} перед удалением:')
                logger.info(f'  - Заказ существует: {Order.objects.filter(id=new_order.id).exists()}')

                # Удаляем заказ
                logger.info(f'Удаляем заказ #{new_order.id} из-за ошибки...')
                deleted_count, _ = new_order.delete()
                logger.info(f'Заказ удален. Количество удаленных объектов: {deleted_count}')

                return Response(
                    {"error": f"Ошибка при добавлении товара: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        logger.info(f'ТОВАРЫ УСПЕШНО ДОБАВЛЕНЫ! Всего добавлено: {len(products_data)} товаров')

        # Очищаем корзину
        try:
            # Получаем корзину пользователя
            basket = Basket.objects.get(profile=profile)
            # Удаляем все товары из корзины
            deleted_count = BasketItem.objects.filter(basket=basket).delete()
            logger.info(
                f"Корзина пользователя {profile.user.username} очищена. Удалено записей: {deleted_count[0] if isinstance(deleted_count, tuple) else deleted_count}")
        except Basket.DoesNotExist:
            logger.warning(f"Корзина для профиля {profile.id} не найдена")

        return Response({"orderId": new_order.id}, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

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
    def get(self, request, id=None):
        logger.info(f'Пользователь запрашивает данные по заказу id={id}')
        try:
            order = Order.objects.get(id=id, profile=request.user.profile)
            return Response(OrderSerializer(order).data)
        except Order.DoesNotExist:
            return Response({"error": "Заказ не найден"}, status=status.HTTP_404_NOT_FOUND)
        except AttributeError:
            return Response({"error": "Профиль пользователя не найден"}, status=status.HTTP_400_BAD_REQUEST)

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
    def post(self, request, id=None):
        logger.info(f'POST Пользователь заполняет детали заказа id{id}')
        # Здесь пользователь ФИО, email, телефон (заполнено автоматом если в профиле заполнено)
        # Здесь пользователь заполняет Город доставки, Адрес доставки
        # Здесь пользователь заполняет Тип доставки
        # Здесь пользователь заполняет Тип оплаты


        try:
            order = Order.objects.get(id=id, profile=request.user.profile)
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
                return Response({'id': order.id}, status=status.HTTP_200_OK)
            else:
                logger.error(f'Ошибка валидации: {serializer.errors}')
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Order.DoesNotExist:
            return Response({"error": "Заказ не найден"}, status=status.HTTP_404_NOT_FOUND)