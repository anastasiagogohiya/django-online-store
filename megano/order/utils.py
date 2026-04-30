import logging
from rest_framework.response import Response
from rest_framework import status
from basket.models import Basket

logger = logging.getLogger(__name__)


def check_profile(request):
    """
    Проверяет наличие профиля у пользователя.
    Возвращает (profile, error_response) или (None, error_response) если ошибка.
    """
    if not hasattr(request.user, 'profile'): # должно создаваться автоматом при регистрации, на всякий случай
        logger.error(f'У пользователя {request.user.id} нет профиля')
        return None, Response(
            {"error": "Профиль пользователя не найден"},
            status=status.HTTP_400_BAD_REQUEST)
    return request.user.profile, None


def get_user_basket(profile):
    """
    Получает корзину пользователя.
    Возвращает (basket, error_response) или (None, error_response) если ошибка.
    """
    try:
        basket = Basket.objects.get(profile=profile)
        return basket, None
    except Basket.DoesNotExist:
        logger.error(f'Корзина для профиля {profile.id} не найдена')
        return None, Response(
            {"error": "Корзина не найдена"},
            status=status.HTTP_404_NOT_FOUND
        )


def check_basket_not_empty(basket):
    """
    Проверяет, что корзина не пуста.
    Возвращает (is_empty, error_response).
    """
    if not basket.items.exists():
        return True, Response(
            {"error": "Корзина пуста"},
            status=status.HTTP_400_BAD_REQUEST
        )
    return False, None