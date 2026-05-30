# kafka_integration/producer.py
import json
import logging
from confluent_kafka import Producer
from django.conf import settings

logger = logging.getLogger(__name__)

"""Подключение к Kafka и отправка сообщений"""

# Глобальный экземпляр продюсера, изначально продюсер не создан
_producer_instance = None

def get_producer():
    """Создание экземпляра одного продюсера, если он не создан"""
    global _producer_instance
    if _producer_instance is None:
        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        }
        logger.info(f"DEBUG: producer conf = {conf}")
        _producer_instance = Producer(conf) # создаем экз класса и передаем конфигурацию
        logger.info(f"Kafka producer подключился к {settings.KAFKA_BOOTSTRAP_SERVERS}")
    return _producer_instance

def publish_message(topic, key, value, callback=None):
    """
    Отправляет сообщение в Kafka.
    - topic: строка ('order-events')
    - key: строка (ключ для партиционирования)
    - value: словарь (будет преобразован в JSON)
    - callback: функция обратного вызова (опционально)
    """
    producer = get_producer()
    try:
        # Сериализуем данные в JSON и кодируем в байты
        serialized_value = json.dumps(value, ensure_ascii=False).encode('utf-8')

        # Асинхронная отправка (fire-and-forget)
        producer.produce(
            topic=topic,
            key=key,
            value=serialized_value,
            callback=callback
        )

        # В лок. разработке БД Sqlite ограничивает нас в операциях
        if not settings.DEBUG:
            producer.flush()  # в проде ждём сколько нужно
        else:
            producer.flush(1)  # в разработке ждём 1 секунду или завершаем
            # producer.poll(0)

    except Exception as e:
        logger.error(f"Failed to send message to Kafka: {e}")
        if callback:
            callback(e, None)
        raise

def delivery_report(err, msg):
    """Обратный вызов для подтверждения доставки"""
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(f"Message delivered to {msg.topic()} "
                    f"[{msg.partition()}] at offset {msg.offset()}")