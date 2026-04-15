"""
Расширенная модель пользователя для интернет-магазина.
Эта модель заменяет стандартную модель User Django, используя email в качестве
идентификатора вместо username.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):
    """
    Кастомный менеджер для модели CustomUser.
    Чтобы джанго не просил авторизацию по username, который мы удалили.
    """
    def create_user(self, email, password=None, **extra):
        """
        Принимает email, password и дополнительные параметры (email, пароль, имя, фамилия, телефон и прочее)
        Создает и возвращает пользователя.
        """
        user = self.model(email=self.normalize_email(email), **extra) # в моделе емейл приводится к нижнему регистру, распаковка других полей
        user.set_password(password) # хеширование пароля
        user.save() # сохранение пользователя в базу данных
        return user

    def create_superuser(self, email, password=None, **extra):
        """Создание суперпользователя, к данным пользователя добавляются
         доступ в админку is_staff=True и права is_superuser=True"""
        return self.create_user(email, password, is_staff=True, is_superuser=True, **extra)


class Avatar(models.Model):
    """Модель для хранения аватара пользователя"""
    src = models.ImageField(
        upload_to="app_users/avatars/user_avatars/",
        default="app_users/avatars/default.png",
        verbose_name="Ссылка на аватарку",
    )
    alt = models.CharField(max_length=128, verbose_name="Описание")

    class Meta:
        verbose_name = "Аватар"
        verbose_name_plural = "Аватары"


class CustomUser(AbstractUser):
    """"Модель пользователя
    (Валидация некоторых полей будет вынесена в отдельный код)
    Из Абстрактого класса User унаследованы:
        - first_name (str): Имя.
        - last_name (str): Фамилия.
        - password (str): Пароль (захешированный).
        - last_login (datetime): Дата последнего входа.
        - date_joined (datetime): Дата регистрации.
        - is_staff (bool): Доступ к админ-панели.
        - is_superuser (bool): Права суперпользователя.
        - groups, user_permissions: Связи с группами и правами.
    """
    username = None # отключаем авторизацию по username
    email = models.EmailField(unique=True, verbose_name="Электронная почта")
    is_active = models.BooleanField(default=True, verbose_name="Активен")  # для мягкого удаления
    phone = models.PositiveIntegerField(
        blank=True, null=True, unique=True, verbose_name="Номер телефона")
    avatar = models.ForeignKey(Avatar, on_delete=models.CASCADE, null=True, related_name="users", blank=True, verbose_name="Аватар")
    balance = models.DecimalField(decimal_places=2, max_digits=10, default=0, verbose_name="Баланс")


    # Настройка авторизации по email вместо username, вход по email (удобно для пользователей)
    USERNAME_FIELD = 'email'

    # Поля, обязательные при создании пользователя через createsuperuser
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()  # подключаем кастомный менеджер, чтобы джанго не просил авторизацию по username


    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ['-date_joined']  # Сортировка по дате регистрации (новые сверху)


    def __str__(self):
        return self.email


    def get_name(self) -> str:
        """Возвращает имя пользователя.
        """
        return self.first_name