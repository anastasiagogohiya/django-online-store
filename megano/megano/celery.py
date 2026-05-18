import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "megano.settings")
app = Celery("megano")

# Загружаем настройки из Django (включая CELERY_BROKER_URL)
app.config_from_object("django.conf:settings", namespace="CELERY")


app.autodiscover_tasks()
