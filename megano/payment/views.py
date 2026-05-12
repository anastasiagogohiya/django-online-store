import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from megano.decorators import catch_all_errors
from megano.permissions import IsAuth
from order.models import Order, OrderStatus

from .models import Payment
from .queue import process_payment_task
from .serializers import PaymentSerializer

logger = logging.getLogger(__name__)


# Добавить очередь в оплату
class PaymentView(APIView):
    permission_classes = [IsAuth]

    @extend_schema(
        summary="Оплата заказа",
        request=PaymentSerializer,
        examples=[
            OpenApiExample(
                "Пример оплаты",
                request_only=True,
                value={
                    "number": "66666666",
                    "name": "Annoying Orange",
                    "month": "02",
                    "year": "2025",
                    "code": "123",
                },
            )
        ],
        tags=["payment"],
    )
    @catch_all_errors
    @transaction.atomic
    def post(self, request, id):
        """Для оплаты заказа введите id заказа"""
        logger.info(f"POST Попытка оплатить заказ {id} ...")

        # Проверяем существование заказа
        profile = request.user.profile

        order = get_object_or_404(Order, id=id, profile=profile)
        logger.info(f"Заказ {id} найден, сумма: {order.total_cost}")

        # Проверяем, не оплачен ли уже заказ
        if order.status == OrderStatus.PAID:
            logger.warning(f"Попытка повторной оплаты заказа {id}")
            return Response({"error": "Заказ уже оплачен"}, status=status.HTTP_400_BAD_REQUEST)

        # Передаем данные карты в сериализатор
        serializer = PaymentSerializer(data=request.data)

        if not serializer.is_valid():
            logger.error(f"Ошибка валидации: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        card_number = serializer.validated_data["number"]
        payment = Payment.objects.create(user=request.user, order=order, amount=order.total_cost, status="pending")
        logger.info(f"Создан платеж #{payment.id} для заказа {id}")

        if settings.TESTING:
            # Синхронный вызов для тестов (без очереди и без on_commit)
            process_payment_task(payment.id, card_number)
        else:
            # Продакшн – асинхронно через очередь и on_commit
            transaction.on_commit(lambda: process_payment_task.delay(payment.id, card_number))
        return Response(
            {
                "status": "pending",
                "payment_id": payment.id,
                "order_id": order.id,
                "message": "Ждём подтверждения оплаты от платёжной системы.",
            },
            status=status.HTTP_200_OK,
        )
