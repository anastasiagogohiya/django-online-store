from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from .models import Category, Product, ProductImage, Tag, Specification, Review, Banner, Sale


# ------------------------------------------------------------
# Форма для Sale с валидацией цены
# ------------------------------------------------------------
class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        sale_price = cleaned_data.get('sale_price')
        if product and sale_price and sale_price >= product.price:
            raise ValidationError('Цена по скидке должна быть меньше обычной цены товара')
        return cleaned_data


# ------------------------------------------------------------
# Inline-классы для ManyToMany связей
# ------------------------------------------------------------
class ProductImageInline(admin.TabularInline):
    model = Product.images.through
    extra = 3
    verbose_name = "Изображение"
    verbose_name_plural = "Изображения"
    # Показываем поле выбора изображения и, если нужно, порядок
    fields = ('productimage',)
    autocomplete_fields = ('productimage',)  # удобный поиск по изображениям


class SpecificationInline(admin.TabularInline):
    model = Product.specifications.through
    extra = 2
    verbose_name = "Характеристика"
    verbose_name_plural = "Характеристики"
    autocomplete_fields = ('specification',)

class ProductTagInline(admin.TabularInline):
    model = Product.tags.through
    extra = 1
    verbose_name = "Товар"
    verbose_name_plural = "Товары с этим тегом"
    autocomplete_fields = ('product',)

class TagInline(admin.TabularInline):
    model = Product.tags.through
    extra = 2
    verbose_name = "Тег"
    verbose_name_plural = "Теги"
    autocomplete_fields = ('tag',)


# ------------------------------------------------------------
# Админки моделей
# ------------------------------------------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'image_preview', 'parent', 'ordering_index', 'is_active')
    list_filter = ('parent', 'is_active')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('ordering_index',)
    actions = ['soft_delete', 'restore']
    has_delete_permission = lambda self, request, obj=None: False

    def soft_delete(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} категорий деактивировано')
    soft_delete.short_description = "Мягкое удаление"

    def restore(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} категорий восстановлено')
    restore.short_description = "Восстановить"

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "Нет изображения"
    image_preview.short_description = "Изображение"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'price_display', 'current_price_display',
                    'count', 'rating', 'purchase_count', 'date')
    list_filter = ('is_active', 'is_limited', 'category', 'free_delivery')
    search_fields = ('title', 'category__title', 'description', 'full_description')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('count',)
    list_per_page = 20
    date_hierarchy = 'date'
    ordering = ('-date',)
    list_display_links = ('id', 'title')
    actions = ['soft_delete', 'restore']
    has_delete_permission = lambda self, request, obj=None: False  # убрала кнопку полного удаления пользователя
    inlines = [ProductImageInline, SpecificationInline, TagInline]
    autocomplete_fields = ['category']

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

    def soft_delete(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} товаров деактивировано')
    soft_delete.short_description = "Мягкое удаление"

    def restore(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} товаров восстановлено')
    restore.short_description = "Восстановить"

    def price_display(self, obj):
        return f"{obj.price} $"
    price_display.short_description = 'Обычная цена'

    def current_price_display(self, obj):
        if obj.has_active_sale:
            return format_html(
                '<span style="color: red; font-weight: bold;">{} $</span> <span style="color: gray; text-decoration: line-through;">{} $</span>',
                obj.current_price, obj.price
            )
        return f"{obj.price} $"
    current_price_display.short_description = 'Актуальная цена'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.purchase_count = 0
            obj.rating = 0
            obj.reviews_count = 0
        super().save_model(request, obj, form, change)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'image_preview', 'alt', 'product_names')
    list_filter = ('product__category',)
    search_fields = ('alt', 'product__title')

    def product_names(self, obj):
        """Показывает все товары, связанные с изображением (ManyToMany)"""
        products = obj.product_set.all()
        if products:
            return ", ".join(p.title for p in products)
        return "Не привязано"
    product_names.short_description = "Товары"

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "Нет изображения"
    image_preview.short_description = "Превью"


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_count')
    search_fields = ('name',)
    inlines = [ProductTagInline]

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
    form = SaleForm  # Подключаем валидацию цены
    list_display = ('product', 'sale_price', 'date_from', 'date_to', 'is_active', 'discount_percent')
    list_filter = ('date_from', 'date_to')
    search_fields = ('product__title',)
    list_editable = ('sale_price',)
    date_hierarchy = 'date_from'
    autocomplete_fields = ['product']

    fieldsets = (
        ('Товар и цена', {
            'fields': ('product', 'sale_price')
        }),
        ('Период действия', {
            'fields': ('date_from', 'date_to')
        }),
    )

    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
    is_active.short_description = "Активна"

    def discount_percent(self, obj):
        if obj.product and obj.product.price and obj.product.price > 0:
            discount = ((obj.product.price - obj.sale_price) / obj.product.price) * 100
            return f"{discount:.0f}%"
        return "-"
    discount_percent.short_description = "Скидка"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('id', 'product_title', 'product_image_preview', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('product__title',)
    autocomplete_fields = ['product']
    fields = ('product', 'is_active')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product').prefetch_related('product__images')

    def product_title(self, obj):
        return obj.product.title if obj.product else "-"
    product_title.short_description = "Товар"

    def product_image_preview(self, obj):
        if obj.product:
            images = list(obj.product.images.all())
            if images and images[0].image:
                return format_html(
                    '<img src="{}" width="80" height="60" style="object-fit: cover; border-radius: 4px;" />',
                    images[0].image.url
                )
        return "Нет изображения"
    product_image_preview.short_description = "Изображение товара"