from django.conf import settings
from .producer import publish_message, delivery_report
import logging

logger = logging.getLogger(__name__)

def publish_order_paid(order):
    """Отправляет событие об оплате заказа в Kafka"""
    logger.info(f"Kafka: формирование сообщения для заказа {order.id}")
    try:
        # Формируем данные события
        event_data = {
            "event_type": "order_paid",
            "order_id": order.id,
            "user_id": order.profile.user.id,
            "delivery_type": order.delivery_type,
            "total_cost": float(order.total_cost),
            "city": order.city,
            "address_delivery": order.address_delivery,
            "created_at": order.created_at.isoformat(),
            "items": [
                {
                    "product_id": item.product.id,
                    "quantity": item.quantity,
                    "price": float(item.price_at_time)
                }
                for item in order.items.all()
            ]
        }
        # Ключ для партиционирования (все сообщения по одному заказу попадут в одну партицию)
        key = str(order.id)
        topic = settings.KAFKA_ORDER_TOPIC

        # Отправляем сообщение
        publish_message(topic=topic, key=key, value=event_data, callback=delivery_report)
        logger.info(f"Событие order_paid для заказа {order.id} опубликовано в топик {topic}")
    except Exception as e:
        logger.error(f"Не удалось опубликовать событие для заказа {order.id}: {e}")
        # Не перевыбрасываем исключение, чтобы не нарушить работу Celery