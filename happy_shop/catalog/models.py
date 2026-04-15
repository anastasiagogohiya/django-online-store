from django.db import models
from django.utils.text import slugify


class SlugMixin:
    """Миксин для авто создания slug (красивый url)
       применяется в Category и Product.
    """
    def save(self, *args, **kwargs):
        if not self.slug:  # если slug пустой
            self.slug = slugify(self.name)  # создать из названия катергории или продукта
        super().save(*args, **kwargs)  # сохранение


class Category(SlugMixin, models.Model):
    """Категория товаров с доступными подкатегориями (до 2-х уровней)"""
    name = models.CharField(max_length=200, verbose_name="Название категории")
    icon = models.ImageField(upload_to='category_icons/', blank=True, null=True, verbose_name="Иконка")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    slug = models.SlugField(unique=True, blank=True)  # красивый вывод url
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name="Главная категория", help_text="Возможны подкатегории от главной категории товаров (макс 2 уровня)")  # возможны подкатегории от главной категории товаров
    ordering_index = models.IntegerField(default=0, verbose_name="Индекс сортировки") # мы можем задать порядок сортировки (в каталог топ-товаров попадают восемь первых товаров по параметру индекс сортировки)


    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['ordering_index', 'name']

    def __str__(self):
        return self.name


class Product(SlugMixin, models.Model):
    """Класс с информацией по товарам"""
    name = models.CharField(max_length=100, verbose_name='Название товара')
    slug = models.SlugField(unique=True, blank=True)  # красивый вывод url
    image = models.ImageField(upload_to='product_images/', verbose_name='Изображение товара') # одно изображение
    description = models.TextField(verbose_name='Полное описание товара', blank=True) # может быть пустым
    short_description = models.TextField(verbose_name='Краткое описание товара')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена товара')
    reviews_count = models.IntegerField(default=0, verbose_name='Количество отзывов')
    is_active = models.BooleanField(default=True, verbose_name='Активен') # мягкое удаление
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Категория")
    is_limited = models.BooleanField(default=False, verbose_name='Ограниченный тираж', help_text="В Limited edition попадают до 16 товаров с галочкой Ограниченный тираж")  # в ограниченый тираж попадают до 16 товаров с галочкой ограниченный тираж
    ordering_index = models.IntegerField(default=0, verbose_name='Индекс сортировки', help_text="В каталог топ-товаров попадают 8 первых товаров по параметру индекс сортировки")
    purchase_count = models.IntegerField(default=0, verbose_name='Количество покупок', help_text="Товары сортируются по популярности") # по заданию товары сортируются по кол-ву покупок
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')


    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['-ordering_index', '-purchase_count']

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    """МНОГО изображений на один товар (best practice выводить в отдельный класс)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name="Товар") # привязка продукт - изображение
    image = models.ImageField(upload_to='product_images/', verbose_name="Изображение")
    is_main = models.BooleanField(default=False, verbose_name="Главное изображение")

    class Meta:
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"

    def __str__(self):
        return f"{self.product.name} - {self.pk}"
