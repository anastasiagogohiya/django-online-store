"""
Расширенная модель пользователя для интернет-магазина
приложения app_users.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager

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


class CustomUser(AbstractUser):
    """"Модель пользователя
    (Валидация некоторых полей будет вынесена в отдельный код)
    Из Абстрактого класса User унаследованы:
        - username: имя пользователя
        - first_name (str): Имя.
        - last_name (str): Фамилия.
        - password (str): Пароль (захешированный).
        - last_login (datetime): Дата последнего входа.
        - date_joined (datetime): Дата регистрации.
        - is_staff (bool): Доступ к админ-панели.
        - is_superuser (bool): Права суперпользователя.
        - groups, user_permissions: Связи с группами и правами.
    """
    email = models.EmailField(blank=True, null=True, verbose_name="Электронная почта")
    is_active = models.BooleanField(default=True, verbose_name="Активен")  # для мягкого удаления
    phone = models.PositiveIntegerField(
        blank=True, null=True, unique=True, verbose_name="Номер телефона")
    avatar = models.ForeignKey(Avatar, on_delete=models.SET_NULL, null=True, related_name="users", blank=True, verbose_name="Аватар") # при удалении аватара, в БД будет NULL, пользователь не будет удален
    balance = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name="Баланс")


    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ['-date_joined']  # Сортировка по дате регистрации (новые сверху)


    def __str__(self):
        return self.username


    def get_name(self) -> str:
        """Возвращает имя пользователя.
        """
        return self.first_name