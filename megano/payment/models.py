from django.db import models
from django.contrib.auth.models import User

# В данном маркете оплата только онлайн банкингом

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь') # связь напрямую с USER, не Profile
    order = models.ForeignKey('order.Order', on_delete=models.CASCADE, related_name='payments')

    # Храним только результат платежа, данные карты нельзя хранить, это уголовная ответственность
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[('pending', 'В обработке'), ('success', 'Успешно'), ('failed', 'Ошибка'),], default='pending')
    payment_date = models.DateTimeField(auto_now_add=True)
    card_last4 = models.CharField(max_length=4, blank=True, verbose_name='Последние 4 цифры')


    class Meta:
        verbose_name = "Оплата"
        verbose_name_plural = "Оплаты"

    def __str__(self):
        return f"Оплата {self.order}, статус оплаты {self.status}, пользователь {self.user}"
