from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Sum

from catalog.models import Product

from .mixins import OrderCreationMixin


# 200/75 = 2.67 - обычная доставка
# 500/75 = 6.67 - экспресс
# 2000/75 = 26.67 - порог бесплатной доставки для обычной
class DeliveryCosts(models.Model):
    ordinary_delivery_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("2.67"),
        verbose_name="Стоимость обычной доставки (при сумме < порога)",
    )
    free_threshold_for_ordinary_delivery = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("26.67"), verbose_name="Порог бесплатной обычной доставки"
    )
    express_delivery_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("6.67"), verbose_name="Стоимость экспресс-доставки"
    )

    class Meta:
        verbose_name = "Расходы на доставку"
        verbose_name_plural = "Расходы на доставку"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return (
            f"Доставка: обычная = {self.ordinary_delivery_price}, "
            f"экспресс = {self.express_delivery_price}, "
            f"порог для обычной = {self.free_threshold_for_ordinary_delivery}"
        )


# Типы доставки
class DeliveryType:
    FREE, EXPRESS, ORDINARY = "free", "express", "ordinary"
    CHOICES = [(FREE, "Бесплатная доставка"), (EXPRESS, "Экспресс доставка"), (ORDINARY, "Обычная доставка")]


# Типы оплаты
class PaymentType:
    ONLINE, SOMEONE = "online", "someone"
    CHOICES = [(ONLINE, "Онлайн картой"), (SOMEONE, "Онлайн со случайного чужого счета")]


# Статусы заказа
class OrderStatus:
    CREATED, ACCEPTED, PAID, DELIVERED, CANCELLED = "created", "accepted", "paid", "delivered", "cancelled"
    CHOICES = [
        (CREATED, "Создан"),
        (ACCEPTED, "Принят"),
        (PAID, "Оплачен"),
        (DELIVERED, "Доставлен"),
        (CANCELLED, "Отменён"),
    ]


class Order(OrderCreationMixin, models.Model):
    """Заказ"""

    profile = models.ForeignKey(
        "app_users.Profile",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="Пользователь",
    )
    delivery_type = models.CharField(
        max_length=100, choices=DeliveryType.CHOICES, default=DeliveryType.FREE, verbose_name="Тип доставки"
    )
    payment_type = models.CharField(
        max_length=100, choices=PaymentType.CHOICES, default=PaymentType.ONLINE, verbose_name="Тип оплаты"
    )
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Стоимость доставки")
    status = models.CharField(
        max_length=100, choices=OrderStatus.CHOICES, default=OrderStatus.CREATED, verbose_name="Статус заказа"
    )
    city = models.CharField(max_length=100, verbose_name="Город доставки")
    address_delivery = models.CharField(max_length=255, verbose_name="Адрес доставки")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания заказа")
    products = models.ManyToManyField("catalog.Product", through="OrderItem", verbose_name="Товары в заказе")
    is_deleted = models.BooleanField(default=False, verbose_name="Удален")  # мягкое удаление
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")
    session_key = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["profile", "status"]),
            models.Index(fields=["session_key", "status"]),
        ]

    def __str__(self):
        return f"Заказ #{self.id} от {self.created_at.strftime('%d.%m.%Y')}"

    def calculate_delivery_cost(self):
        delivery_costs = DeliveryCosts.get_solo()
        if self.delivery_type == DeliveryType.EXPRESS:
            return delivery_costs.express_delivery_price
        elif self.delivery_type == DeliveryType.ORDINARY:
            products_price = self.calculate_products_price()
            return (
                delivery_costs.ordinary_delivery_price
                if products_price < delivery_costs.free_threshold_for_ordinary_delivery
                else 0
            )
        else:
            return 0

    def calculate_products_price(self):
        """Цена товаров без доставки"""
        total_products = self.items.aggregate(total=Sum(F("price_at_time") * F("quantity")))["total"] or 0
        return total_products

    def calculate_total_cost(self):
        """Пересчет общей стоимости заказа с доставкой"""
        products_price = self.calculate_products_price()
        delivery = self.calculate_delivery_cost()
        self.delivery_price = delivery
        self.total_cost = products_price + delivery
        self.save(update_fields=["total_cost", "delivery_price"])

    # Для того чтобы применялся миксин
    @classmethod
    def create_from_basket(cls, basket, profile, products_data, delivery_data=None, session_key=None):
        """Создает заказ из корзины (метод класса)"""
        temp_order = cls()
        if delivery_data is None:
            delivery_data = {
                "city": "",
                "address": "",
                "deliveryType": "free",
                "paymentType": "online",
            }
        return temp_order.create_order_from_basket(basket, profile, products_data, delivery_data, session_key)

    def cancel(self):
        """Отмена заказа с восстановлением остатков (из миксина)"""
        self.cancel_order_with_restore(self)


class OrderItem(models.Model):
    """Товары в заказе"""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Заказ")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="Количество")
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена на момент покупки")

    class Meta:
        verbose_name = "Товар в заказе"
        verbose_name_plural = "Товары в заказе"

    def save(self, *args, **kwargs):
        if not self.price_at_time and self.product_id:
            product = Product.objects.get(id=self.product_id)
            self.price_at_time = product.current_price
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        if not self.product_id:
            raise ValidationError({"product": "Товар не выбран"})
        # Проверяем активность товара, но не загружаем объект, чтобы избежать ошибки
        if not Product.objects.filter(id=self.product_id, is_active=True).exists():
            raise ValidationError({"product": "Нельзя добавить в заказ удалённый товар"})

    def __str__(self):
        return f"{self.product.title} x{self.quantity} = {self.price_at_time * self.quantity} долларов"
