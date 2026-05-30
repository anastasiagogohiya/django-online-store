from dataclasses import dataclass
from django.conf import settings


@dataclass(frozen=True)
class KafkaConfig:
    """Конфигурация для работы с Kafka"""
    bootstrap_servers: str # адрес брокера
    order_topic: str # имя топика

# данные из settings.py
kafka_settings = KafkaConfig(
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
    order_topic=settings.KAFKA_ORDER_TOPIC,
)