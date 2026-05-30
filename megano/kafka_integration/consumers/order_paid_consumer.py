import os
import json
import logging
from confluent_kafka import Consumer, KafkaError

# Устанавливаем переменную окружения для Django (для запуска скрипта напрямую)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'megano.settings')
import django
django.setup()

from django.conf import settings
from kafka_integration.models import PickingTask

logger = logging.getLogger(__name__)

def run_consumer():
    conf = {
        'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'warehouse_consumer_group',   # уникальный идентификатор группы
        'auto.offset.reset': 'earliest',          # читаем все сообщения с начала
        'enable.auto.commit': True,               # автоматически фиксируем offset
    }
    consumer = Consumer(conf)
    consumer.subscribe([settings.KAFKA_ORDER_TOPIC])  # подписываемся на топик order-events

    logger.info(f"Запущен consumer для склада, слушаем топик {settings.KAFKA_ORDER_TOPIC}")

    try:
        while True:
            msg = consumer.poll(1.0)  # ждём сообщение до 1 секунды
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    logger.error(f"Ошибка consumer: {msg.error()}")
                    break

            # Декодируем сообщение
            try:
                event_data = json.loads(msg.value().decode('utf-8'))
                event_type = event_data.get('event_type')
                if event_type == 'order_paid':
                    order_id = event_data['order_id']
                    # Создаём или пропускаем (идемпотентность)
                    task, created = PickingTask.objects.get_or_create(
                        order_id=order_id,
                        defaults={'order_data': event_data}
                    )
                    if created:
                        logger.info(f"✅ Создано задание на сборку для заказа {order_id}")
                    else:
                        logger.debug(f"Задание для заказа {order_id} уже существует")
                else:
                    logger.warning(f"Неизвестный тип события: {event_type}")
            except Exception as e:
                logger.exception(f"Ошибка обработки сообщения: {e}")
    except KeyboardInterrupt:
        logger.info("Consumer остановлен пользователем")
    finally:
        consumer.close()

if __name__ == "__main__":
    run_consumer()