from django.core.management.base import BaseCommand
from kafka_integration.consumers.order_paid_consumer import run_consumer

class Command(BaseCommand):
    help = 'Запускает Kafka consumer для создания заданий склада'

    def handle(self, *args, **options):
        self.stdout.write("Запускаем consumer склада...")
        run_consumer()