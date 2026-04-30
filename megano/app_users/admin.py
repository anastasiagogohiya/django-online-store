from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Profile, Avatar


class AvatarAdmin(admin.ModelAdmin):
    """Админка для аватаров"""
    list_display = ('id', 'src', 'alt', 'get_image_preview')
    list_display_links = ('id', 'src')
    search_fields = ('alt',)
    fields = ('src', 'alt')

    def get_image_preview(self, obj):
        """Превью аватара в админке"""
        if obj.src:
            return f'<img src="{obj.src.url}" width="50" height="50" style="border-radius: 50%;" />'
        return "Нет изображения"

    get_image_preview.allow_tags = True
    get_image_preview.short_description = "Превью"


class ProfileInline(admin.StackedInline):
    """Встраиваемая форма профиля в страницу пользователя"""
    model = Profile
    can_delete = False
    verbose_name_plural = 'Профиль'
    fieldsets = (
        ('Основная информация', {
            'fields': ('full_name', 'phone', 'balance')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Аватар', {
            'fields': ('avatar',)
        }),
    )


class ProfileAdmin(admin.ModelAdmin):
    """Админка для профилей пользователей"""
    list_display = ('id', 'user', 'full_name', 'get_user_email', 'phone', 'is_active', 'balance', 'avatar_preview')
    list_display_links = ('id', 'user', 'full_name')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'full_name', 'phone')
    list_editable = ('is_active',)
    readonly_fields = ('get_avatar_preview',)

    fieldsets = (
        ('Связь с пользователем', {
            'fields': ('user', 'get_avatar_preview')
        }),
        ('Личная информация', {
            'fields': ('full_name', 'phone')
        }),
        ('Аватар', {
            'fields': ('avatar',)
        }),
        ('Финансы', {
            'fields': ('balance',)
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
    )

    def get_user_email(self, obj):
        """Получить email из связанного пользователя"""
        return obj.user.email

    get_user_email.short_description = "Email"
    get_user_email.admin_order_field = 'user__email'

    def avatar_preview(self, obj):
        """Превью аватара в списке"""
        if obj.avatar and obj.avatar.src:
            return f'<img src="{obj.avatar.src.url}" width="40" height="40" style="border-radius: 50%;" />'
        return "Нет аватара"

    avatar_preview.allow_tags = True
    avatar_preview.short_description = "Аватар"

    def get_avatar_preview(self, obj):
        """Превью аватара на странице редактирования"""
        if obj.avatar and obj.avatar.src:
            return f'<img src="{obj.avatar.src.url}" width="100" height="100" style="border-radius: 50%;" />'
        return "Аватар не загружен"

    get_avatar_preview.allow_tags = True
    get_avatar_preview.short_description = "Текущий аватар"


class CustomUserAdmin(UserAdmin):
    """Кастомная админка пользователя с встроенным профилем"""
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'has_profile', 'get_profile_phone')
    list_filter = ('is_staff', 'is_active', 'profile__is_active')
    search_fields = ('username', 'email', 'profile__full_name', 'profile__phone')

    def has_profile(self, obj):
        """Проверка наличия профиля у пользователя"""
        return hasattr(obj, 'profile')

    has_profile.boolean = True
    has_profile.short_description = "Профиль заполнен"

    def get_profile_phone(self, obj):
        """Получить телефон из профиля"""
        if hasattr(obj, 'profile') and obj.profile.phone:
            return obj.profile.phone
        return "Не указан"

    get_profile_phone.short_description = "Телефон"


# Перерегистрируем модели в админке
admin.site.unregister(User)  # Отключаем стандартную регистрацию User
admin.site.register(User, CustomUserAdmin)  # Регистрируем с кастомной админкой
admin.site.register(Profile, ProfileAdmin)
admin.site.register(Avatar, AvatarAdmin)