from django.db import models

# Имитация работы склада, получение Задания на сбор заказов

class PickingTask(models.Model):
    order_id = models.PositiveIntegerField(unique=True, verbose_name="ID заказа")
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Ожидает сборки'),
            ('processing', 'В процессе сборки'),
            ('done', 'Собран'),
        ],
        default='pending',
        verbose_name="Статус сборки"
    )
    order_data = models.JSONField(default=dict, verbose_name="Данные заказа")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Задание на сборку"
        verbose_name_plural = "Задания на сборку"

    def __str__(self):
        return f"Сборка заказа №{self.order_id}"