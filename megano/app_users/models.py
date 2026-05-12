"""
Расширенная модель пользователя для интернет-магазина
приложения app_users. Регистрация и авторизация по username.
Профиль создается автоматически при регистрации пользователя.
"""
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import os



class Avatar(models.Model):
    """Модель для хранения аватара пользователя"""
    src = models.ImageField(
        upload_to="app_users/avatars/user_avatars/",
        default="app_users/avatars/default.png",
        verbose_name="Ссылка на аватарку",)
    alt = models.CharField(max_length=128, blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Аватар"
        verbose_name_plural = "Аватары"

    def __str__(self):
        return f"Avatar {self.id}: {self.src}"

    def delete(self, *args, **kwargs):
        # Удаляем файл
        if self.src and os.path.isfile(self.src.path):
            os.remove(self.src.path)
        super().delete(*args, **kwargs)




class Profile(models.Model):
    """"Профиль пользователя
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="Пользователь")
    full_name = models.CharField(max_length=128, verbose_name="Полное имя")
    phone = models.PositiveIntegerField(blank=True, null=True, unique=True, verbose_name="Номер телефона")
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

    def soft_delete(self):
        """Мягкое удаление"""
        self.is_active = False
        self.save()
        # Деактивируем пользователя, иначе может он все равно зайти!
        if self.user:
            self.user.is_active = False
            self.user.save()

    def restore(self):
        """Восстановление"""
        self.is_active = True
        self.save()
        # Активируем пользователя обратно
        if self.user:
            self.user.is_active = True
            self.user.save()

    def hard_delete(self):
        """Полное удаление из БД"""
        super().delete()

"""Автосоздание профиля"""

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Сигнал: автоматически создает профиль при создании нового пользователя.
    Срабатывает при любом способе создания пользователя.
    В админке профиль автоматом не создается, то есть сигнал игнорируется.
    """
    if created and not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Сигнал: сохраняет профиль при сохранении пользователя.
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()