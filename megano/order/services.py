# order/services.py
import logging

from django.core.exceptions import ValidationError
from django.db import transaction

from basket.models import Basket

from .models import Order, OrderStatus

logger = logging.getLogger(__name__)


@transaction.atomic
def create_order_from_basket(basket: Basket, products_data: list, profile=None, session_key=None) -> Order:
    """Создает заказ на основе корзины с профилем или сессией, с проверкой"""
    # 1. Удаление зависших заказов
    Order.objects.filter(
        profile=profile if profile else None,
        session_key=session_key if not profile else None,
        status=OrderStatus.CREATED,
    ).delete()

    # 2. Проверка соответствия товаров из запроса реальной корзине
    basket_item_ids = set(basket.items.values_list("id", flat=True))
    frontend_item_ids = {item["id"] for item in products_data}
    if not frontend_item_ids.issubset(basket_item_ids):
        missing = frontend_item_ids - basket_item_ids
        raise ValidationError(f"Товары с id={missing} отсутствуют в корзине")

    # 3. Логирование расхождений в количестве
    basket_dict = {item.id: item for item in basket.items.select_related("product")}
    for frontend_item in products_data:
        basket_item = basket_dict.get(frontend_item["id"])
        if basket_item and frontend_item["count"] != basket_item.count:
            logger.warning(
                f"Количество товара {frontend_item['id']} не совпадает: "
                f"фронт {frontend_item['count']}, корзина {basket_item.count}"
            )

    # 4. Подготовка пустых данных доставки (заполнятся позже)
    delivery_data = {
        "city": "",
        "address": "",
        "deliveryType": "",
        "paymentType": "",
    }

    # 5. Вызов метода модели, который внутри использует миксин
    order = Order.create_from_basket(
        basket=basket,
        profile=profile,
        products_data=products_data,
        delivery_data=delivery_data,
        session_key=session_key,
    )
    return order


@transaction.atomic
def update_order_details(order, validated_data: dict) -> Order:
    """Обновление деталей заказа"""
    for attr, value in validated_data.items():
        if hasattr(order, attr):
            setattr(order, attr, value)
    order.calculate_total_cost()  # пересчет с доставкой
    if order.status == OrderStatus.CREATED:
        order.status = OrderStatus.ACCEPTED
    order.save()
    return order
