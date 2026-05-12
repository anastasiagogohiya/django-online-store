# basket/signals.py
import logging

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from order.models import Order  # на случай, если нужно смержить заказы

from .models import Basket

logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def merge_guest_cart_on_login(sender, user, request, **kwargs):
    old_session_key = request.session.get("anonymous_session_key")
    if not old_session_key:
        logger.info("No guest cart session key found.")
        return

    # 1. Слияние корзин
    try:
        guest_basket = Basket.objects.get(session_key=old_session_key)
        user_basket, created = Basket.objects.get_or_create(profile=user.profile)
        for guest_item in guest_basket.items.all():
            user_item, item_created = user_basket.items.get_or_create(
                product=guest_item.product, defaults={"count": guest_item.count}
            )
            if not item_created:
                user_item.count += guest_item.count
                user_item.save()
        logger.info(f"Successfully merged guest cart (key: {old_session_key}) into user cart (user: {user.username})")
        # Опционально: guest_basket.delete()
    except Basket.DoesNotExist:
        logger.warning(f"Guest basket not found for session key: {old_session_key}")
    except Exception as e:
        logger.error(f"Error during cart merge for user {user.username}: {e}")

    # 2. ПЕРЕНОС ЗАКАЗОВ – ВСЕГДА, ПОСЛЕ СЛИЯНИЯ КОРЗИН
    updated = Order.objects.filter(session_key=old_session_key, profile__isnull=True).update(profile=user.profile)
    if updated:
        logger.info(f"Transferred {updated} orders from guest session to user {user.username}")

    # 3. Очистка ключа сессии
    if "anonymous_session_key" in request.session:
        del request.session["anonymous_session_key"]
        request.session.modified = True
