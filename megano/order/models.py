from django.db import models
from django.core.validators import MinValueValidator


# Типы доставки
class DeliveryType:
    FREE, EXPRESS, ORDINARY = 'free', 'express', 'ordinary'
    CHOICES = [(FREE, 'Бесплатная доставка'), (EXPRESS, 'Экспресс доставка'), (ORDINARY, 'Обычная доставка')]

# Типы оплаты
class PaymentType:
    CASH, ONLINE, CARD, SOMEONE  = 'cash', 'online', 'card', 'someone'
    CHOICES = [(CASH, 'Наличные'), (ONLINE, 'Онлайн картой'), (CARD, 'Карта курьеру'), (SOMEONE, 'Онлайн со случайного чужого счета')]

# Статусы заказа
class OrderStatus:
    CREATED, ACCEPTED, PAID, DELIVERED, CANCELLED = 'created', 'accepted', 'paid', 'delivered', 'cancelled'
    CHOICES = [(CREATED, 'Создан'), (ACCEPTED, 'Принят'), (PAID, 'Оплачен'), (DELIVERED, 'Доставлен'), (CANCELLED, 'Отменён')]



class Order(models.Model):
    """Заказ"""
    profile = models.ForeignKey('app_users.Profile', on_delete=models.CASCADE, related_name='orders', verbose_name='Пользователь')
    delivery_type = models.CharField(max_length=100, choices=DeliveryType.CHOICES, default=DeliveryType.FREE,verbose_name='Тип доставки')
    payment_type = models.CharField(max_length=100, choices=PaymentType.CHOICES, default=PaymentType.ONLINE, verbose_name='Тип оплаты')
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=100, choices=OrderStatus.CHOICES, default=OrderStatus.CREATED, verbose_name='Статус заказа')
    city = models.CharField(max_length=100, verbose_name='Город доставки')
    address_delivery = models.CharField(max_length=255, verbose_name='Адрес доставки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания заказа')
    products = models.ManyToManyField('catalog.Product', through='OrderItem', verbose_name='Товары в заказе') # данные из модели Product

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заказ #{self.id} от {self.created_at.strftime("%d.%m.%Y")}'

class OrderItem(models.Model):
    """Товары в заказе"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заказ')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, verbose_name='Товар')
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)], verbose_name='Количество')
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена на момент покупки')

    class Meta:
        verbose_name = 'Товар в заказе'
        verbose_name_plural = 'Товары в заказе'

    def save(self, *args, **kwargs):
        # Если цена не установлена, берем текущую цену с учетом распродажи
        if not self.price_at_time and self.product:
            self.price_at_time = self.product.current_price  # используем свойство
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.product.title} x{self.quantity} = {self.price_at_time * self.quantity} долларов'
