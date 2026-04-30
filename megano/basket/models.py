from django.db import models
from django.db.models import Sum, F
from app_users.models import Profile
from catalog.models import Product


class Basket(models.Model):
    """Корзина пользователя"""
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, null=True, blank=True, related_name='basket', verbose_name="Пользователь")
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True, verbose_name="Ключ сессии") # если пользователь не авторизован
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self):
        if self.profile:
            return f"Корзина {self.profile.user.username}"
        return f"Корзина (сессия: {self.session_key})"

    def attach_profile(self, profile):
        """Прикрепление профиля к корзине на уровне модели"""
        if profile and not self.profile:
            self.profile = profile
            self.save(update_fields=['profile'])
            return True
        return False

    def get_total_price(self):
        """Общая цена с учетом актуальной цены"""
        total = 0
        for item in self.items.select_related('product__sale'):
            total += item.product.current_price * item.count # с учетом распродажной цены
        return round(total, 2)

    def get_total_items(self):
        """Общее количество товаров в корзине"""
        return self.items.aggregate(total=Sum('count'))['total'] or 0


class BasketItem(models.Model):
    """Товар в корзине"""
    basket = models.ForeignKey(Basket, on_delete=models.CASCADE, related_name='items', verbose_name="Корзина")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='basket_items', verbose_name="Товар")
    count = models.PositiveIntegerField(default=1, verbose_name="Количество")

    class Meta:
        verbose_name = "Товар в корзине"
        verbose_name_plural = "Товары в корзине"
        unique_together = ['basket', 'product']  # один товар в корзине может быть только один раз

    def __str__(self):
        return f"{self.product.title} x {self.count}"

    @property
    def total_price(self):
        """Стоимость товара с учётом количества"""
        return round(self.product.current_price * self.count, 2) # с учетом распродажной цены