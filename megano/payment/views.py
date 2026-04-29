from rest_framework.views import APIView
from .serializers import PaymentSerializer
from rest_framework.permissions import IsAuthenticated
from .models import Payment
from order.models import Order
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiExample
from rest_framework import status
from drf_spectacular.utils import extend_schema
from app_users.models import Profile
import logging

logger = logging.getLogger(__name__)



class PaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Оплата заказа",
        request=PaymentSerializer,
        examples=[
            OpenApiExample(
                'Пример оплаты',
                request_only=True,
                value={
                    "number": "9999999999999999",
                    "name": "Annoying Orange",
                    "month": "02",
                    "year": "2025",
                    "code": "123"
                }
            )
        ],
        tags=['payment'],
    )
    def post(self, request, id):
        logger.info(f'POST Попытка оплатить заказ {id} ...')

        # 1. Проверяем существование заказа
        try:
            # Получаем профиль пользователя
            profile = request.user.profile

            # Ищем заказ
            order = Order.objects.get(id=id, profile=profile)
            logger.info(f'Заказ {id} найден, сумма: {order.total_cost}')

        except Profile.DoesNotExist:
            logger.error(f'Профиль не найден для пользователя {request.user.username}')
            return Response(
                {'error': 'Профиль пользователя не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Order.DoesNotExist:
            logger.warning(f'Заказ {id} не найден для пользователя {request.user.username}')
            return Response(
                {'error': 'Заказ не найден'},
                status=status.HTTP_404_NOT_FOUND)

        # Проверяем, не оплачен ли уже заказ
        if order.status == 'paid':
            logger.warning(f'Попытка повторной оплаты заказа {id}')
            return Response(
                {'error': 'Заказ уже оплачен'},
                status=status.HTTP_400_BAD_REQUEST)

        # Передаем данные карты в сериализатор
        serializer = PaymentSerializer(data=request.data)

        if not serializer.is_valid():
            logger.error(f'Ошибка валидации: {serializer.errors}')
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        payment = Payment.objects.create(
            user=request.user,
            order=order,
            amount=order.total_cost,
            status='pending')

        logger.info(f'Создан платеж #{payment.id} для заказа {id}')

        card_data = serializer.validated_data

        try:
            # Пока заглушка
            transaction_id = f"txn_{payment.id}"
            payment_status = 'success'
            card_last4 = str(card_data['number'])[-4:]

            # Обновляем платеж
            payment.transaction_id = transaction_id
            payment.status = payment_status
            payment.card_last4 = card_last4
            payment.save()

            # Обновляем статус заказа
            order.status = 'paid'
            order.save()

            logger.info(f'Платеж {payment.id} успешно обработан для заказа {id}')

            return Response({
                'payment_id': payment.id,
                'status': payment.status,
                'transaction_id': payment.transaction_id,
                'amount': str(payment.amount),
                'order_id': order.id,
                'card_last4': card_last4,
                'message': 'Оплата прошла успешно'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # Если ошибка - меняем статус
            payment.status = 'failed'
            payment.save()
            logger.error(f'Ошибка оплаты для заказа {id}: {str(e)}')
            return Response(
                {'error': f'Ошибка при обработке платежа: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST)