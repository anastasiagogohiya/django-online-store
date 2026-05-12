from django.contrib import admin
from .models import Basket, BasketItem
from app_users.models import Profile
from django.db.models import Q


class BasketItemInline(admin.TabularInline):
    model = BasketItem
    extra = 0
    readonly_fields = ('total_price',)
    fields = ('product', 'count', 'total_price')
    can_delete = True
    show_change_link = False


@admin.register(Basket)
class BasketAdmin(admin.ModelAdmin):
    def short_session_key(self, obj): # не убираю поле с сессией так как фронтэнд работатет с анонимными пользователями
        return obj.session_key[:8] + '…' if obj.session_key else '-'
    short_session_key.short_description = 'Сессия'

    list_display = ('id', 'profile', 'short_session_key', 'get_total_items', 'get_total_price', 'created_at')
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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'profile':
            kwargs['queryset'] = Profile.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Показываем корзины активных профилей и анонимов
        return qs.filter(Q(profile__is_active=True) | Q(profile__isnull=True))


