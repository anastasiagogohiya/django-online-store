import logging

from basket.models import Basket

logger = logging.getLogger(__name__)


class BasketMixin:
    """Миксин для получения корзины (используется во всех вью ф-циях корзины)"""

    def get_or_create_basket(self, request):
        """Получить или создать корзину для авторизованного пользователя или сессии"""
        if request.user.is_authenticated:
            logger.info(f"Получение корзины пользователя {request.user}")
            basket, created = Basket.objects.get_or_create(
                profile=request.user.profile, defaults={"session_key": request.session.session_key}
            )
            # Если корзина существовала, но без session_key - обновляем
            if not created and not basket.session_key and request.session.session_key:
                basket.session_key = request.session.session_key
                basket.save(update_fields=["session_key"])
        else:
            if not request.session.session_key:
                request.session.create()
                logger.info(f"Сессия создана: {request.session.session_key}")

            logger.info(f"Получение корзины по сессии: {request.session.session_key}")
            basket, created = Basket.objects.get_or_create(
                session_key=request.session.session_key, defaults={"profile": None}
            )

        return basket
