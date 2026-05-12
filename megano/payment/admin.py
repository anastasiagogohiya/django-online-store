from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'order', 'amount', 'status', 'payment_date', 'transaction_id_short', 'card_last4')
    list_filter = ('status', 'payment_date', 'user')
    search_fields = ('transaction_id', 'order__id', 'user__username', 'user__email', 'card_last4')
    readonly_fields = ('transaction_id', 'payment_date', 'order', 'user', 'amount', 'card_last4')
    list_select_related = ('user', 'order')
    list_per_page = 50
    ordering = ('-payment_date',)

    has_add_permission = lambda self, request: False
    has_delete_permission = lambda self, request, obj=None: False

    fieldsets = (
        ('Основное', {
            'fields': ('user', 'order', 'amount', 'status', 'payment_date')
        }),
        ('Платёжные данные', {
            'fields': ('transaction_id', 'card_last4'),
            'classes': ('collapse',)
        }),
    )

    def transaction_id_short(self, obj):
        """Отображаем сокращённый transaction_id для экономии места"""
        if obj.transaction_id:
            return obj.transaction_id[:8] + '…' if len(obj.transaction_id) > 8 else obj.transaction_id
        return '-'
    transaction_id_short.short_description = 'ID транзакции'

    # Запрещаем добавление новых платежей через админку (они создаются автоматически при оплате)
    def has_add_permission(self, request):
        return False

    # Разрешаем изменение только статуса (и то не всем пользователям)
    def get_readonly_fields(self, request, obj=None):
        readonly = super().get_readonly_fields(request, obj)
        if obj and obj.status == 'success':
            # Успешный платёж нельзя изменять вообще
            return readonly + ('status',)
        return readonly

    # Можно добавить действие для ручного подтверждения платежа (например, если не пришёл callback)
    actions = ['mark_as_success', 'mark_as_failed']

    def mark_as_success(self, request, queryset):
        count = queryset.exclude(status='success').update(status='success')
        self.message_user(request, f'{count} платежей помечено как успешные.')
    mark_as_success.short_description = 'Отметить выбранные платежи как успешные'

    def mark_as_failed(self, request, queryset):
        count = queryset.exclude(status='failed').update(status='failed')
        self.message_user(request, f'{count} платежей помечено как ошибочные.')
    mark_as_failed.short_description = 'Отметить выбранные платежи как ошибочные'