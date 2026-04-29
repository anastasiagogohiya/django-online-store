from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
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
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "Нет изображения"

    image_preview.short_description = "Изображение"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'price_display', 'current_price_display',
                    'count', 'is_active', 'is_limited', 'rating', 'purchase_count')
    list_filter = ('is_active', 'is_limited', 'category', 'free_delivery')
    search_fields = ('title', 'category__title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('count', 'is_active', 'is_limited')  # убрал price отсюда, т.к. цена теперь отображается
    list_per_page = 20
    date_hierarchy = 'date'

    inlines = [ProductImageInline, SpecificationInline, TagInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'slug', 'category', 'description', 'full_description')
        }),
        ('Цена и наличие', {
            'fields': ('price', 'count', 'free_delivery'),
            'description': 'Если товар участвует в распродаже, будет отображаться актуальная цена со скидкой'
        }),
        ('Статус товара', {
            'fields': ('is_active', 'is_limited', 'ordering_index')
        }),
        ('Статистика', {
            'fields': ('rating', 'reviews_count', 'purchase_count'),
            'classes': ('collapse',)
        }),
    )

    autocomplete_fields = ['category']

    def price_display(self, obj):
        """Отображает обычную цену товара"""
        return f"{obj.price} $"
    price_display.short_description = 'Обычная цена'

    def current_price_display(self, obj):
        """Отображает актуальную цену с учетом распродажи"""
        if obj.has_active_sale:
            return format_html(
                '<span style="color: red; font-weight: bold;">{} $</span> <span style="color: gray; text-decoration: line-through;">{} $</span>',
                obj.current_price,
                obj.price
            )
        return f"{obj.price} $"
    current_price_display.short_description = 'Актуальная цена'

    def save_model(self, request, obj, form, change):
        """Кастомное сохранение с логированием"""
        if not change:
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
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "Нет изображения"
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
    list_display = ('product', 'sale_price', 'date_from', 'date_to', 'is_active', 'discount_percent')
    list_filter = ('date_from', 'date_to')
    search_fields = ('product__title',)
    list_editable = ('sale_price',)
    date_hierarchy = 'date_from'
    raw_id_fields = ('product',)
    autocomplete_fields = ['product']  # Добавляем autocomplete для удобства

    fieldsets = (
        ('Товар и цена', {
            'fields': ('product', 'sale_price')
        }),
        ('Период действия', {
            'fields': ('date_from', 'date_to')
        }),
    )

    def is_active(self, obj):
        """Показывает активна ли сейчас распродажа"""
        from django.utils import timezone
        today = timezone.now().date()
        return obj.date_from <= today <= obj.date_to
    is_active.boolean = True
    is_active.short_description = "Активна"

    def discount_percent(self, obj):
        """Показывает процент скидки"""
        if obj.product and obj.product.price:
            discount = ((obj.product.price - obj.sale_price) / obj.product.price) * 100
            return f"{discount:.0f}%"
        return "-"
    discount_percent.short_description = "Скидка"

    def save_model(self, request, obj, form, change):
        """При сохранении распродажи можно добавить валидацию"""
        if obj.sale_price >= obj.product.price:
            from django.core.exceptions import ValidationError
            raise ValidationError('Цена по скидке должна быть меньше обычной цены')
        super().save_model(request, obj, form, change)


from django.contrib import admin
from django.utils.html import format_html
from .models import Banner


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'product_title', 'product_image_preview')
    search_fields = ('product__title',)
    autocomplete_fields = ['product']  # удобный поиск по товарам

    fields = ('product',)  # только поле product

    def product_title(self, obj):
        """Название товара"""
        return obj.product.title if obj.product else "-"

    product_title.short_description = "Товар"

    def product_image_preview(self, obj):
        """Показывает изображение товара"""
        if obj.product:
            first_image = obj.product.images.first()
            if first_image and first_image.image:
                return format_html(
                    '<img src="{}" width="80" height="60" style="object-fit: cover;" />',
                    first_image.image.url
                )
        return "Нет изображения"

    product_image_preview.short_description = "Изображение товара"