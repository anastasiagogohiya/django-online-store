from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'phone', 'avatar', 'is_active',)
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',) # сортировка по email
    list_filter = ('is_staff', 'is_active', 'date_joined') # Фильтрация по полям для удобства

    # можно провалиться в email и там будет следующая информация
    fieldsets = (
        ('Личная информация', {'fields': ('first_name', 'last_name', 'phone', 'avatar')}),
        ('Аутентификация', {'fields': ('email', 'password')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')})
         ) # добавила поле с правами доступа чтобы можно наделять пользователей правами

