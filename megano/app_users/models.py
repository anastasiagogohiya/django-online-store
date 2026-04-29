"""
Расширенная модель пользователя для интернет-магазина
приложения app_users.
"""

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

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

"""Автосоздание профиля"""

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Сигнал: автоматически создает профиль при создании нового пользователя.
    Срабатывает при любом способе создания пользователя.
    """
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={'full_name': instance.username or f"User_{instance.id}"})
        print(f"Создан профиль для пользователя: {instance.username}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Сигнал: сохраняет профиль при сохранении пользователя.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # Если профиля нет по какой-то причине, создаем его
        Profile.objects.get_or_create(
            user=instance,
            defaults={'full_name': instance.username or f"User_{instance.id}"})