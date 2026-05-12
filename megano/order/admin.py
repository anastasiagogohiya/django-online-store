from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from catalog.models import Product

from .models import DeliveryCosts, DeliveryType, Order, OrderItem, OrderStatus, PaymentType


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    is_order_item = True
    autocomplete_fields = ["product"]  # чтотбы проще было искать товар
    # raw_id_fields = ['product']
    extra = 1
    fields = (
        "product",
        "quantity",
        "price_at_time",
        "current_price_display",
        "sale_status_display",
        "price_comparison",
        "item_total_display",
    )
    readonly_fields = (
        "price_at_time",
        "current_price_display",
        "sale_status_display",
        "price_comparison",
        "item_total_display",
    )

    def item_total_display(self, obj):
        """Сумма за эту позицию (количество × цена)"""
        if obj.price_at_time and obj.quantity:
            total = obj.price_at_time * obj.quantity
            return f"{total} $"
        return "-"

    item_total_display.short_description = "💰 Сумма позиции"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "product":
            kwargs["queryset"] = Product.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def current_price_display(self, obj):
        """Отображаем актуальную цену товара с цветом"""
        if obj.product_id:
            from catalog.models import Product

            try:
                product = Product.objects.get(id=obj.product_id)
                if product.has_active_sale:
                    return format_html(
                        '<span style="color: red; font-weight: bold;">{} ₽</span>', product.current_price
                    )
                return f"{product.current_price} ₽"
            except Product.DoesNotExist:
                return "Товар не найден"
        return "Выберите товар"

    current_price_display.short_description = "💰 Актуальная цена"

    def sale_status_display(self, obj):
        """Отображаем информацию о распродаже с эмодзи"""
        if obj.product_id:
            try:
                product = Product.objects.get(id=obj.product_id)
                if hasattr(product, "sale") and product.sale:
                    if product.sale.is_active:
                        discount = round((1 - product.sale.sale_price / product.price) * 100)
                        return format_html(
                            '<span style="color: green; font-weight: bold;">🔥 АКТИВНА! Скидка {}%</span>', discount
                        )
                    else:
                        return format_html('<span style="color: gray;">⏰ Закончилась {}</span>', product.sale.date_to)
                return "❌ Не участвует"
            except Product.DoesNotExist:
                return "Товар не найден"
        return "Выберите товар"

    sale_status_display.short_description = "🎯 Статус распродажи"

    def price_comparison(self, obj):
        """Сравнение цены в заказе с текущей ценой"""
        if obj.product_id and obj.price_at_time:
            try:
                product = Product.objects.get(id=obj.product_id)
                if obj.price_at_time != product.current_price:
                    difference = product.current_price - obj.price_at_time
                    if difference > 0:
                        return format_html('<span style="color: green;">⬇️ Дешевле на {} $</span>', abs(difference))
                    elif difference < 0:
                        return format_html('<span style="color: red;">⬆️ Дороже на {} $</span>', abs(difference))
                return "✅ Цена актуальна"
            except Product.DoesNotExist:
                return "-"
        return "-"

    price_comparison.short_description = "📊 Сравнение цен"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    change_form_template = "admin/order/change_form.html"
    list_display = (
        "id",
        "profile",
        "get_delivery_type_display",
        "get_payment_type_display",
        "total_cost",
        "current_total_cost_display",
        "get_status_display",
        "created_at",
        # "has_products_on_sale",
        "city",
        "address_delivery",
        "delivery_price",
    )
    list_filter = ("status", "delivery_type", "payment_type", "created_at", "city")
    search_fields = ("id", "profile__user__username", "profile__user__email", "city", "address_delivery")
    readonly_fields = ("created_at", "total_cost", "delivery_price", "current_total_cost_display")
    actions = ["soft_delete_orders", "restore_orders"]
    has_delete_permission = lambda self, request, obj=None: False
    inlines = [OrderItemInline]
    fieldsets = (
        ("Информация о заказе", {"fields": ("profile", "status", "created_at")}),
        ("Доставка", {"fields": ("delivery_type", "city", "address_delivery")}),
        ("Оплата", {"fields": ("payment_type",)}),
        ("Стоимость", {"fields": ("total_cost", "delivery_price", "current_total_cost_display")}),
    )

    def get_delivery_type_display(self, obj):
        return dict(DeliveryType.CHOICES).get(obj.delivery_type, obj.delivery_type)

    get_delivery_type_display.short_description = "Тип доставки"

    def get_payment_type_display(self, obj):
        return dict(PaymentType.CHOICES).get(obj.payment_type, obj.payment_type)

    get_payment_type_display.short_description = "Тип оплаты"

    def get_status_display(self, obj):
        return dict(OrderStatus.CHOICES).get(obj.status, obj.status)

    get_status_display.short_description = "Статус"

    def current_total_cost_display(self, obj):
        """Показывает актуальную стоимость заказа по текущим ценам"""
        total = 0
        has_sale = False
        for item in obj.items.all():
            if item.product:
                total += item.product.current_price * item.quantity
                if item.product.has_active_sale:
                    has_sale = True

        if has_sale:
            return format_html(
                '<span style="color: red; font-weight: bold;">'
                '{} $</span> <span style="color: gray;">(с учетом скидок)</span>',
                total,
            )
        return f"{total} $"

    current_total_cost_display.short_description = "💰 Цена без дос"

    def has_products_on_sale(self, obj):
        """Показывает, есть ли в заказе товары с распродажей"""
        for item in obj.items.all():
            if item.product and item.product.has_active_sale:
                return "✅ Есть"
        return "❌ Нет"

    has_products_on_sale.short_description = "🔥 Распродажа"

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.status == OrderStatus.PAID:
            readonly.append("delivery_type")
            readonly.append("payment_type")
            readonly.append("address_delivery")
        return readonly

    def save_related(self, request, form, formsets, change):
        """Пересчет общей стоимости после сохранения товаров"""
        super().save_related(request, form, formsets, change)
        if form.instance.id:
            form.instance.calculate_total_cost()

    def soft_delete_orders(self, request, queryset):
        count = queryset.update(
            is_deleted=True,
            deleted_at=timezone.now(),
            status=OrderStatus.CANCELLED,  # меняем статус на "Отменён"
        )
        self.message_user(request, f'{count} заказ(ов) мягко удалено (статус изменён на "Отменён")')

    def restore_orders(self, request, queryset):
        count = queryset.update(
            is_deleted=False,
            deleted_at=None,
            status=OrderStatus.CREATED,  # возвращаем в статус "Создан"
        )
        self.message_user(request, f'{count} заказ(ов) восстановлено (статус изменён на "Создан")')

    def get_queryset(self, request):
        # Показываем все заказы, включая удалённые, но можно отфильтровать
        return super().get_queryset(request)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "product",
        "quantity",
        "price_at_time",
        "current_price",
        "difference_display",
        "is_on_sale",
        "sale_price",
        "total_price",
    )
    list_filter = ("order__status", "order__delivery_type")
    search_fields = ("order__id", "product__title")
    readonly_fields = ("price_at_time",)

    def current_price(self, obj):
        """Текущая цена товара"""
        if obj.product:
            if obj.product.has_active_sale:
                return format_html(
                    '<span style="color: red; font-weight: bold;">{} ₽</span>', obj.product.current_price
                )
            return f"{obj.product.current_price} ₽"
        return "-"

    current_price.short_description = "💰 Текущая цена"

    def difference_display(self, obj):
        """Разница между ценой в заказе и текущей ценой"""
        if obj.product and obj.price_at_time:
            current = obj.product.current_price
            if obj.price_at_time != current:
                diff = current - obj.price_at_time
                if diff > 0:
                    return format_html('<span style="color: green;">⬇️ -{} ₽</span>', abs(diff))
                else:
                    return format_html('<span style="color: red;">⬆️ +{} ₽</span>', abs(diff))
            return "✅"
        return "-"

    difference_display.short_description = "📊 Разница"

    def is_on_sale(self, obj):
        """Показывает, в распродаже ли товар"""
        if obj.product and obj.product.has_active_sale:
            return "🔥 Да"  # Убираем format_html
        return "❌ Нет"

    is_on_sale.short_description = "Распродажа"

    def sale_price(self, obj):
        """Показывает цену по распродаже"""
        if obj.product and hasattr(obj.product, "sale") and obj.product.sale:
            if obj.product.sale.is_active:
                discount = round((1 - obj.product.sale.sale_price / obj.product.price) * 100)
                return f"{obj.product.sale.sale_price} ₽ (скидка {discount}%)"  # Убираем format_html
            return f"Было: {obj.product.sale.sale_price} ₽"
        return "-"

    sale_price.short_description = "🏷️ Цена со скидкой"

    def total_price(self, obj):
        """Общая стоимость позиции"""
        return f"{obj.price_at_time * obj.quantity} ₽"

    total_price.short_description = "💰 Стоимость в заказе"


@admin.register(DeliveryCosts)
class DeliveryCostsAdmin(admin.ModelAdmin):
    """Настройка отображения и редактирования цен доставки"""

    fieldsets = (
        (
            "Обычная доставка",
            {
                "fields": ("ordinary_delivery_price", "free_threshold_for_ordinary_delivery"),
                "description": "При сумме заказа меньше порога – доставка платная, иначе бесплатная.",
            },
        ),
        (
            "Экспресс доставка",
            {
                "fields": ("express_delivery_price",),
                "description": "Фиксированная стоимость экспресс-доставки (всегда платная).",
            },
        ),
    )
    verbose_name_plural = "Расходы на доставку"

    def has_add_permission(self, request):
        """Запрещаем создание более одной записи"""
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        """Запрещаем удаление единственной записи"""
        return False
