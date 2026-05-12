import logging
import random

from celery import shared_task
from django.db import transaction

from order.models import OrderStatus

from .models import Payment

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_payment_task(self, payment_id, card_number):
    """
    Асинхронная задача для обработки платежа по правилам ТЗ.
    Вызывается из очереди.
    """
    try:
        payment = Payment.objects.select_related("order").get(id=payment_id)
        order = payment.order
        logger.info(f"Обработка платежа {payment_id} для заказа {order.id}")

        # Более сложная валидация происходит здесь, в сериализаторе проверка форматов
        card_num = int(card_number)
        last_digit = card_number[-1]
        is_even = card_num % 2 == 0
        not_ends_with_zero = last_digit != "0"
        logger.info("Номер карты: должен содержать только цифры, не заканчиваться на 0, быть четным")

        if is_even and not_ends_with_zero:
            # Успешная оплата
            with transaction.atomic():
                payment.status = "success"
                payment.transaction_id = f"txn_{payment_id}_{random.randint(1000, 9999)}"
                payment.card_last4 = card_number[-4:]  # последние 4 цифры
                payment.save(update_fields=["status", "transaction_id", "card_last4"])

                order.status = OrderStatus.PAID
                order.save(update_fields=["status"])

            logger.info(f"Платеж {payment_id} успешно завершён")
            logger.info(f"Заказ #{order.id} оплачен на сумму {order.total_cost} S.")
            return {"status": "success", "payment_id": payment_id, "order_id": order.id}
        else:
            # Генерируем случайную ошибку
            error_messages = [
                "Ошибка соединения с платёжным шлюзом",
                "Недостаточно средств на карте",
                "Операция запрещена банком-эмитентом",
                "Таймаут обработки запроса",
            ]
            error_text = random.choice(error_messages)
            with transaction.atomic():
                payment.status = "failed"
                payment.error_text = error_text
                payment.save(update_fields=["status", "error_text"])

            logger.warning(f"Платеж {payment_id} не удался: {error_text}")
            return {"status": "failed", "error": error_text, "payment_id": payment_id}

    except Payment.DoesNotExist:
        logger.error(f"Платеж с id {payment_id} не найден")
        return {"error": "Payment not found"}
    except Exception as e:
        logger.exception(f"Ошибка при обработке платежа {payment_id}: {e}")
        # Повторяем задачу через 60 секунд (до 3 раз)
        raise self.retry(exc=e, countdown=60)
