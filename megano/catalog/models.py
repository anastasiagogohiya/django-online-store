from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CASCADE
from django.utils import timezone

from catalog.mixins import ImageValidatorMixin, SlugMixin


class Category(ImageValidatorMixin, SlugMixin, models.Model):
    """Категория товаров с доступными подкатегориями (до 2-х уровней)"""

    title = models.CharField(max_length=255, verbose_name="Название категории")
    image = models.ImageField(
        upload_to="catalog/categories/", blank=True, null=True, verbose_name="Изображение категории"
    )
    slug = models.SlugField(unique=True, blank=True, verbose_name="URL")
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategories",
        verbose_name="Главная категория",
        help_text="Возможны подкатегории от главной категории товаров (макс 2 уровня)",
    )  # ниже ограничение по уровням

    ordering_index = models.IntegerField(
        default=0, verbose_name="Индекс сортировки"
    )  # мы можем задать порядок сортировки (в каталог топ-товаров попадают 8 товаров по параметру индекс сортировки)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["ordering_index", "title"]

    def clean(self):
        """Валидация: запрещаем создание категорий глубже 2 уровня"""
        if self.parent and self.parent.parent:
            raise ValidationError(
                "Максимальная глубина вложенности — 2 уровня (нельзя создать подкатегорию для подкатегории)"
            )

    def save(self, *args, **kwargs):
        """Вызываем валидацию"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title  # pragma: no cover


class Tag(models.Model):
    name = models.CharField(max_length=45, verbose_name="Название тэга")

    class Meta:
        verbose_name = "Тэг"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name  # pragma: no cover


class ProductImage(ImageValidatorMixin, models.Model):
    image = models.ImageField(upload_to="catalog/product_images/", verbose_name="Изображение товара")
    alt = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Изображение"
        verbose_name_plural = "Изображения"

    def __str__(self):
        return f"Изображение {self.image.name} - {self.alt}"  # pragma: no cover

    def save(self, *args, **kwargs):
        """Создаем alt автоматически и валидируем изображение"""
        if not self.alt and self.image.name:
            self.alt = self.image.name.split("/")[-1].split(".")[0]
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.image:
            self.validate_image(self.image, field_name="image", max_size_mb=10, min_width=300, min_height=300)


class Specification(models.Model):
    """Спецификация (размер например)"""

    name = models.CharField(max_length=100, verbose_name="Название")  # например Размер
    value = models.CharField(max_length=100, verbose_name="Значение")  # например XL

    class Meta:
        verbose_name = "Спецификация"
        verbose_name_plural = "Спецификации"

    def __str__(self):
        return f"Спецификация: {self.name} {self.value}"  # pragma: no cover


class Product(SlugMixin, models.Model):
    """Класс с информацией по товарам"""

    title = models.CharField(max_length=100, verbose_name="Название товара")
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products", db_index=True, verbose_name="Категория"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена товара")

    # наличие обновляется через сигнал в приложении orders (при создании/отмене заказа)
    count = models.IntegerField(default=0, verbose_name="Наличие на складе")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания карточки товара")
    description = models.TextField(max_length=255, verbose_name="Краткое описание товара")
    full_description = models.TextField(
        max_length=1000, verbose_name="Полное описание товара", blank=True
    )  # может быть пустым
    free_delivery = models.BooleanField(default=True, verbose_name="Бесплатная доставка")
    images = models.ManyToManyField(ProductImage, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, db_index=True)
    specifications = models.ManyToManyField(Specification, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name="Рейтинг товара")
    reviews_count = models.IntegerField(default=0, verbose_name="Количество отзывов")
    is_active = models.BooleanField(default=True, verbose_name="Активен")  # мягкое удаление
    is_limited = models.BooleanField(
        default=False,
        verbose_name="Ограниченный тираж",
        help_text="В Limited edition попадают до 16 товаров с галочкой Ограниченный тираж",
    )  # в ограниченый тираж попадают до 16 товаров с галочкой ограниченный тираж
    ordering_index = models.IntegerField(
        default=0,
        db_index=True,
        verbose_name="Индекс сортировки",
        help_text="В каталог топ-товаров-8 первых товаров по индексу сортировки",
    )

    # количество покупок обновляется через сигнал в приложении orders
    # (при изменении статуса заказа на оплачен/доставлен)
    purchase_count = models.IntegerField(
        default=0, db_index=True, verbose_name="Количество покупок", help_text="Товары сортируются по популярности"
    )  # по заданию товары сортируются по кол-ву покупок
    slug = models.SlugField(unique=True, blank=True)  # красивый вывод url

    @property
    def current_price(self):
        """Текущая цена с учетом активной распродажи"""
        if hasattr(self, "sale") and self.sale and self.sale.is_active:
            return self.sale.sale_price
        return self.price

    @property
    def has_active_sale(self):
        """Проверяет, есть ли активная распродажа на товар"""
        return hasattr(self, "sale") and self.sale and self.sale.is_active

    @property
    def available(self):
        """True если есть в наличии (используется для фильтрации поиска)"""
        return self.count > 0

    def clean(self):
        super().clean()
        if self.price < 0:
            raise ValidationError({"price": "Цена не может быть отрицательной"})
        if self.count < 0:
            raise ValidationError({"count": "Количество не может быть отрицательным"})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["-ordering_index", "-purchase_count"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["-purchase_count"]),
            models.Index(fields=["is_limited", "ordering_index"]),
        ]

    def __str__(self):
        return f"#{self.id} - {self.title}"  # pragma: no cover

    def soft_delete(self):
        """Мягкое удаление"""
        self.is_active = False
        self.save()

    def restore(self):
        """Восстановление"""
        self.is_active = True
        self.save()

    def hard_delete(self):
        """Полное удаление из БД"""
        super().delete()


class Sale(models.Model):
    """Модель для распродажи"""

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="sale")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена по скидке")
    date_from = models.DateField(verbose_name="Дата начала")
    date_to = models.DateField(verbose_name="Дата окончания")

    class Meta:
        verbose_name = "Распродажа"
        verbose_name_plural = "Распродажи"

    @property
    def is_active(self):
        """Проверяет, активна ли распродажа сейчас"""
        today = timezone.now().date()
        return self.date_from <= today <= self.date_to

    def get_price(self):
        """Возвращает цену с учетом скидки"""
        return self.sale_price if self.is_active else self.product.price

    def clean(self):
        if self.date_from > self.date_to:
            raise ValidationError("Дата начала не может быть позже даты окончания")

        if self.date_to < timezone.now().date():
            raise ValidationError("Дата окончания не может быть в прошлом")


class Review(models.Model):
    author = models.ForeignKey("app_users.Profile", on_delete=CASCADE, related_name="reviews")
    product = models.ForeignKey(
        Product, on_delete=CASCADE, related_name="reviews"
    )  # связь с продуктом, по которому сделан отзыв
    text = models.TextField(max_length=500, verbose_name="Отзыв покупателя")
    rate = models.PositiveSmallIntegerField(verbose_name="Оценка пользователя (от 1 до 5 вкл.)")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата отзыва")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"

    def clean(self):
        if not (1 <= self.rate <= 5):
            raise ValidationError({"rate": "Оценка должна быть от 1 до 5"})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Banner(models.Model):
    """В баннере откражается товар включенный в баннер"""

    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="banner", verbose_name="Товар для баннера"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        verbose_name = "Баннер"
        verbose_name_plural = "Баннеры"

    def __str__(self):
        return f"Баннер: {self.product.title}"  # pragma: no cover
