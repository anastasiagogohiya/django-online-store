# order/mixins.py
import logging

from django.core.exceptions import ValidationError
from django.db import transaction

logger = logging.getLogger(__name__)


class OrderStockCheckMixin:
    """Миксин для проверки наличия товаров перед созданием заказа"""

    def check_products_stock(self, basket_items):
        """
        Проверяет, достаточно ли товаров на складе.
        """
        errors = []

        for item in basket_items:
            product = item.product
            requested_qty = item.count

            if requested_qty > product.count:
                errors.append(
                    {
                        "product_id": product.id,
                        "title": product.title,
                        "available": product.count,
                        "requested": requested_qty,
                        "error": f"Недостаточно товара '{product.title}'. "
                        f"Доступно: {product.count}, заказано: {requested_qty}",
                    }
                )
                logger.warning(
                    f"Недостаточно товара: '{product.title}' (ID={product.id}), "
                    f"доступно={product.count}, заказано={requested_qty}"
                )

        is_available = len(errors) == 0
        return is_available, errors

    def validate_basket_before_order(self, basket):
        """Полная проверка корзины перед созданием заказа"""
        basket_items = basket.items.select_related("product").all()

        if not basket_items.exists():
            raise ValidationError("Корзина пуста")

        is_available, errors = self.check_products_stock(basket_items)

        if not is_available:
            raise ValidationError({"stock_errors": errors})

        return basket_items


class OrderStockDecreaseMixin:
    """Миксин для уменьшения количества товаров на складе при создании заказа"""

    def decrease_products_stock(self, order_items):
        """
        Уменьшает количество товаров на складе.
        """
        changes = []

        for order_item in order_items:
            product = order_item.product
            old_count = product.count

            # Уменьшаем количество
            product.count -= order_item.quantity
            product.save(update_fields=["count"])

            # Увеличиваем счетчик покупок
            product.purchase_count += order_item.quantity
            product.save(update_fields=["purchase_count"])

            changes.append(
                {
                    "product_id": product.id,
                    "title": product.title,
                    "old_count": old_count,
                    "new_count": product.count,
                    "ordered": order_item.quantity,
                    "new_purchase_count": product.purchase_count,
                }
            )

            logger.info(
                f"Товар '{product.title}' (ID={product.id}): "
                f"было={old_count}, стало={product.count}, "
                f"заказано={order_item.quantity}, "
                f"всего покупок={product.purchase_count}"
            )

        return changes

    def restore_products_stock(self, order):
        """
        Восстанавливает количество товаров (при отмене заказа).
        """
        for order_item in order.items.select_related("product"):
            product = order_item.product
            old_count = product.count

            # Восстанавливаем количество
            product.count += order_item.quantity
            product.save(update_fields=["count"])

            # Уменьшаем счетчик покупок (опционально)
            product.purchase_count -= order_item.quantity
            product.save(update_fields=["purchase_count"])

            logger.info(
                f"Восстановлен товар '{product.title}' (ID={product.id}): было={old_count}, стало={product.count}"
            )


class OrderCreationMixin(OrderStockCheckMixin, OrderStockDecreaseMixin):
    @transaction.atomic
    def create_order_from_basket(self, basket, profile, products_data, delivery_data, session_key):
        from .models import Order, OrderItem, OrderStatus

        basket_items = basket.items.select_related("product").all()
        if not basket_items.exists():
            raise ValidationError("Корзина пуста")

        is_available, errors = self.check_products_stock(basket_items)
        if not is_available:
            raise ValidationError({"stock_errors": errors})

        order = Order.objects.create(
            profile=profile,
            session_key=session_key if profile is None else None,
            delivery_type=delivery_data.get("deliveryType", "free"),
            payment_type=delivery_data.get("paymentType", "online"),
            city=delivery_data.get("city", ""),
            address_delivery=delivery_data.get("address", ""),
            status=OrderStatus.CREATED,
            total_cost=0,
        )

        order_items = []
        for basket_item in basket_items:
            order_item = OrderItem.objects.create(
                order=order,
                product=basket_item.product,
                quantity=basket_item.count,
                price_at_time=basket_item.product.current_price,
            )
            order_items.append(order_item)

        self.decrease_products_stock(order_items)

        # Единый метод пересчёта итога (товары + доставка)
        order.calculate_total_cost()

        basket.items.all().delete()

        logger.info(f"Заказ #{order.id} успешно создан. Итоговая сумма без доставки: {order.total_cost}")
        return order
