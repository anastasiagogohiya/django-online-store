import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from basket.models import Basket

logger = logging.getLogger(__name__)


def check_profile(request: Request):
    """
    Проверяет наличие профиля у пользователя.
    Возвращает (profile, error_response) или (None, error_response) если ошибка.
    """
    if not hasattr(request.user, "profile"):  # должно создаваться автоматом при регистрации, на всякий случай
        logger.error(f"У пользователя {request.user.id} нет профиля")
        return None, Response({"error": "Профиль пользователя не найден"}, status=status.HTTP_400_BAD_REQUEST)
    return request.user.profile, None


def get_user_basket(profile, session_key):
    """
    Получает или создаёт корзину пользователя.
    - Если profile передан (авторизованный пользователь) – ищет по profile.
    - Если profile = None – ищет по session_key (аноним).
    Возвращает (basket, error_response) или (None, error_response) при ошибке.
    """
    try:
        if profile:
            basket, _ = Basket.objects.get_or_create(profile=profile)
        else:
            basket, _ = Basket.objects.get_or_create(session_key=session_key)
        return basket, None
    except Exception as e:
        logger.error(f"Ошибка получения/создания корзины: {e}")
        return None, Response({"error": "Ошибка при работе с корзиной"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def check_basket_not_empty(basket):
    """
    Проверяет, что корзина не пуста.
    Возвращает (is_empty, error_response).
    """
    if not basket.items.exists():
        return True, Response({"error": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)
    return False, None
