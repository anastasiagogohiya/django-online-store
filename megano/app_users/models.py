"""
Расширенная модель пользователя для интернет-магазина
приложения app_users.
"""

from django.db import models
from django.contrib.auth.models import User

"""Регистрация и авторизация по username"""
class Avatar(models.Model):
    """Модель для хранения аватара пользователя"""
    src = models.ImageField(
        upload_to="app_users/avatars/user_avatars/",
        default="app_users/avatars/default.png",
        verbose_name="Ссылка на аватарку",
    )
    alt = models.CharField(max_length=128, blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Аватар"
        verbose_name_plural = "Аватары"


class Profile(models.Model):
    """"Профиль пользователя
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="Пользователь")
    full_name = models.CharField(max_length=128, verbose_name="Полное имя")
    email = models.EmailField(blank=True, null=True, verbose_name="Электронная почта")
    phone = models.PositiveIntegerField(
        blank=True, null=True, unique=True, verbose_name="Номер телефона")
    is_active = models.BooleanField(default=True, verbose_name="Активен")  # для мягкого удаления
    avatar = models.ForeignKey(Avatar, on_delete=models.SET_NULL, null=True, related_name="profile", blank=True, verbose_name="Аватар") # при удалении аватара, в БД будет NULL, пользователь не будет удален
    balance = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name="Баланс")


    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"


    def __str__(self):
        return self.full_name or self.user.username

    def get_name(self) -> str:
        """Возвращает имя пользователя"""
        return self.full_name