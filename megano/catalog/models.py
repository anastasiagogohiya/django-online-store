from django.db import models
from django.db.models import CASCADE
from django.utils.text import slugify
from django.core.exceptions import ValidationError

class SlugMixin:
    """Миксин для авто создания slug (красивый url)
       применяется в Category и Product.
    """
    def save(self, *args, **kwargs):
        if not self.slug:  # если slug пустой
            self.slug = slugify(self.title)  # создать из названия катергории или продукта
        super().save(*args, **kwargs)  # сохранение


class Category(SlugMixin, models.Model):
    """Категория товаров с доступными подкатегориями (до 2-х уровней)"""
    title = models.CharField(max_length=255, verbose_name="Название категории")
    image = models.ImageField(upload_to='catalog/categories/', blank=True, null=True, verbose_name="Изображение категории") # можно оставить пустым
    slug = models.SlugField(unique=True, blank=True, verbose_name="URL")

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories',
        verbose_name="Главная категория",
        help_text="Возможны подкатегории от главной категории товаров (макс 2 уровня)"
    ) # ниже ограничение по уровням

    ordering_index = models.IntegerField(default=0,
                                         verbose_name="Индекс сортировки")  # мы можем задать порядок сортировки (в каталог топ-товаров попадают восемь первых товаров по параметру индекс сортировки)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['ordering_index', 'title']

    def clean(self):
        """Валидация: запрещаем создание категорий глубже 2 уровня"""
        if self.parent and self.parent.parent:
            raise ValidationError(
                "Максимальная глубина вложенности — 2 уровня (нельзя создать подкатегорию для подкатегории)")

    def save(self, *args, **kwargs):
        """Вызываем валидацию"""
        self.full_clean()
        super().save(*args, **kwargs)


    def __str__(self):
        return self.title


class Tag(models.Model):
    name = models.CharField(max_length=45, verbose_name='Название тэга')

    class Meta:
        verbose_name = "Тэг"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    image = models.ImageField(upload_to='catalog/product_images/', verbose_name="Изображение товара")
    alt = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Изображение"
        verbose_name_plural = "Изображения"


class Specification(models.Model):
    """Спецификация (размер например)"""
    name = models.CharField(max_length=100, verbose_name='Название') # например Размер
    value = models.CharField(max_length=100, verbose_name='Значение') # например XL

    class Meta:
        verbose_name = "Спецификация"
        verbose_name_plural = "Спецификации"


class Product(SlugMixin, models.Model):
    """Класс с информацией по товарам"""
    title = models.CharField(max_length=100, verbose_name='Название товара')
    category =  models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name="Категория")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена товара')

    # наличие обновляется через сигнал в приложении orders (при создании/отмене заказа)
    count = models.IntegerField(default=0, verbose_name='Наличие на складе')
    date = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания карточки товара')
    description = models.TextField(max_length=255, verbose_name='Краткое описание товара')
    full_description = models.TextField(max_length=500, verbose_name='Полное описание товара', blank=True) # может быть пустым
    free_delivery = models.BooleanField(default=True, verbose_name='Бесплатная доставка')
    images = models.ManyToManyField(ProductImage, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    specifications = models.ManyToManyField(Specification, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0, verbose_name="Рейтинг товара")
    reviews_count = models.IntegerField(default=0, verbose_name='Количество отзывов')
    is_active = models.BooleanField(default=True, verbose_name='Активен')  # мягкое удаление
    is_limited = models.BooleanField(default=False, verbose_name='Ограниченный тираж',
                                     help_text="В Limited edition попадают до 16 товаров с галочкой Ограниченный тираж")  # в ограниченый тираж попадают до 16 товаров с галочкой ограниченный тираж
    ordering_index = models.IntegerField(default=0, db_index=True ,verbose_name='Индекс сортировки',
                                         help_text="В каталог топ-товаров попадают 8 первых товаров по параметру индекс сортировки")

    # кол-во покупок # количество покупок обновляется через сигнал в приложении orders (при изменении статуса заказа на оплачен/доставлен)
    purchase_count = models.IntegerField(default=0, db_index=True, verbose_name='Количество покупок',
                                         help_text="Товары сортируются по популярности")  # по заданию товары сортируются по кол-ву покупок
    slug = models.SlugField(unique=True, blank=True)  # красивый вывод url

    # reviews удалила

    @property
    def available(self):
        """True если есть в наличии (используется для фильтрации поиска)"""
        return self.count > 0

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['-ordering_index', '-purchase_count']

    def __str__(self):
        return self.title


class Review(models.Model):
    author = models.ForeignKey("app_users.Profile", on_delete=CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=CASCADE, related_name='reviews') # связь с продуктом, по которому сделан отзыв
    text = models.TextField(max_length=500, verbose_name="Отзыв покупателя")
    rate = models.PositiveSmallIntegerField(verbose_name="Оценка пользователя (от 1 до 5 включительно)")
    date = models.DateTimeField(auto_now_add=True, verbose_name='Дата отзыва')

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"