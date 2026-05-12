import json
import logging

from django.http import HttpRequest

from app_users.models import Profile

logger = logging.getLogger(__name__)


def parse_request_data(request: HttpRequest) -> dict:
    """Универсальный парсер данных от фронтенда и Swagger"""
    # для swagger
    if request.content_type == "application/json" and isinstance(request.data, dict):
        return request.data
    # для фронтэнда (отправляет строку JSON)
    json_string = list(request.data.keys())[0]
    return json.loads(json_string)


def get_profile(user) -> Profile:
    """Вспомогательный метод для получения/создания профиля"""
    profile, created = Profile.objects.get_or_create(user=user, defaults={"full_name": user.username})
    if created:
        logger.info(f"Created new profile for user: {user.username}")
    return profile
