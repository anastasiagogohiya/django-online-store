from django.contrib import admin
from .models import Category, Product, ProductImage, Tag, Specification, Review, Banner, Sale


class ProductImageInline(admin.TabularInline):
    """Для добавления нескольких изображений прямо на странице продукта"""
    model = Product.images.through  # связующая таблица ManyToMany
    extra = 3  # 3 пустых поля для загрузки изображений
    verbose_name = "Изображение"
    verbose_name_plural = "Изображения"


class SpecificationInline(admin.TabularInline):
    """Для добавления характеристик прямо на странице продукта"""
    model = Product.specifications.through
    extra = 2
    verbose_name = "Характеристика"
    verbose_name_plural = "Характеристики"


class TagInline(admin.TabularInline):
    """Для добавления тегов прямо на странице продукта"""
    model = Product.tags.through
    extra = 2
    verbose_name = "Тег"
    verbose_name_plural = "Теги"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'image_preview', 'parent', 'ordering_index')
    list_filter = ('parent',)
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('ordering_index',)  # можно менять порядок прямо в списке

    def image_preview(self, obj):
        """Показывает миниатюру изображения в списке"""
        if obj.image:
            return f'<img src="{obj.image.url}" width="50" height="50" style="object-fit: cover;" />'
        return "Нет изображения"

    image_preview.allow_tags = True
    image_preview.short_description = "Изображение"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'count', 'is_active',
                    'is_limited', 'rating', 'purchase_count')
    list_filter = ('is_active', 'is_limited', 'category', 'free_delivery')
    search_fields = ('title', 'category__title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('price', 'count', 'is_active', 'is_limited')  # быстрая правка
    list_per_page = 20  # пагинация в админке
    date_hierarchy = 'date'  # навигация по датам

    # Inline формы для связанных объектов
    inlines = [ProductImageInline, SpecificationInline, TagInline]

    # Поля для детальной страницы
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'slug', 'category', 'description', 'full_description')
        }),
        ('Цена и наличие', {
            'fields': ('price', 'count', 'free_delivery')
        }),
        ('Статус товара', {
            'fields': ('is_active', 'is_limited', 'ordering_index')
        }),
        ('Статистика', {
            'fields': ('rating', 'reviews_count', 'purchase_count'),
            'classes': ('collapse',)  # сворачиваемый блок
        }),
    )

    # Фильтр по категориям с поиском
    autocomplete_fields = ['category']

    def save_model(self, request, obj, form, change):
        """Кастомное сохранение с логированием"""
        if not change:  # если создается новый объект
            obj.purchase_count = 0
            obj.rating = 0
            obj.reviews_count = 0
        super().save_model(request, obj, form, change)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'image_preview', 'alt', 'product_name')
    list_filter = ('product__category',)
    search_fields = ('alt', 'product__title')

    def product_name(self, obj):
        """Показывает название товара"""
        product = obj.product_set.first()
        return product.title if product else "Не привязано"

    product_name.short_description = "Товар"

    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" width="50" height="50" style="object-fit: cover;" />'
        return "Нет изображения"

    image_preview.allow_tags = True
    image_preview.short_description = "Превью"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_count')
    search_fields = ('name',)

    def product_count(self, obj):
        return obj.product_set.count()

    product_count.short_description = "Кол-во товаров"


@admin.register(Specification)
class SpecificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'product_count')
    search_fields = ('name', 'value')

    def product_count(self, obj):
        return obj.product_set.count()

    product_count.short_description = "Кол-во товаров"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('author', 'product', 'rate', 'date', 'short_text')
    list_filter = ('rate', 'date')
    search_fields = ('author__full_name', 'product__title', 'text')
    date_hierarchy = 'date'

    def short_text(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text

    short_text.short_description = "Отзыв"


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('product', 'sale_price', 'date_from', 'date_to', 'is_active')
    list_filter = ('date_from', 'date_to')
    search_fields = ('product__title',)
    list_editable = ('sale_price',)
    date_hierarchy = 'date_from'
    raw_id_fields = ('product',)

    fieldsets = (
        ('Товар и цена', {
            'fields': ('product', 'sale_price')}),
        ('Период действия', {
            'fields': ('date_from', 'date_to')}),)

    def is_active(self, obj):
        """Показывает активна ли сейчас распродажа"""
        from django.utils import timezone
        today = timezone.now().date()
        return obj.date_from <= today <= obj.date_to

    is_active.boolean = True
    is_active.short_description = "Активна"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('product', 'product_price', 'product_category')
    search_fields = ('product__title',)
    raw_id_fields = ('product',)

    def product_price(self, obj):
        return obj.product.price

    product_price.short_description = "Цена товара"

    def product_category(self, obj):
        return obj.product.category

    product_category.short_description = "Категория"