from django.contrib import admin
from .models import Basket, BasketItem


class BasketItemInline(admin.TabularInline):
    model = BasketItem
    extra = 1
    readonly_fields = ('total_price',)
    fields = ('product', 'count', 'total_price')
    can_delete = True
    show_change_link = False


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    list_display = ('id', 'profile', 'session_key', 'get_total_items', 'get_total_price', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [BasketItemInline]
    list_filter = ('created_at', 'profile')
    search_fields = ('profile__user__username', 'session_key')

    def get_total_items(self, obj):
        return obj.get_total_items()

    get_total_items.short_description = "Всего товаров"
    get_total_items.admin_order_field = 'items__count'

    def get_total_price(self, obj):
        return f"${obj.get_total_price()}"

    get_total_price.short_description = "Общая стоимость"

