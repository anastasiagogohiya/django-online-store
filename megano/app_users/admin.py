from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django import forms
from django.utils.safestring import mark_safe
from .models import Profile, Avatar


class IsActiveFilter(admin.SimpleListFilter):
    """Простой фильтр для отображения активных/неактивных профилей"""
    title = 'Статус профиля'
    parameter_name = 'profile_status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Активные'),
            ('inactive', 'Неактивные (удаленные)'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(profile__is_active=True)
        if self.value() == 'inactive':
            return queryset.filter(profile__is_active=False)
        return queryset


class CustomUserCreationForm(UserCreationForm):
    """Форма создания пользователя"""
    full_name = forms.CharField(max_length=255, required=False, label='Полное имя')
    phone = forms.CharField(max_length=20, required=False, label='Телефон')
    balance = forms.DecimalField(max_digits=10, decimal_places=2, required=False, initial=0, label='Баланс')
    avatar = forms.ModelChoiceField(
        queryset=Avatar.objects.all(),
        required=False,
        label='Аватар'
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Исправляем: нужно использовать поле avatar, а не src
        if 'avatar' in self.fields:
            # Получаем related field для поля avatar (это ForeignKey в Profile)
            from django.db.models.fields.related import ForeignKey
            avatar_field = Profile._meta.get_field('avatar')
            if isinstance(avatar_field, ForeignKey):
                self.fields['avatar'].widget = RelatedFieldWidgetWrapper(
                    self.fields['avatar'].widget,
                    avatar_field.remote_field,
                    admin_site=admin.site,
                    can_add_related=True,
                    can_change_related=True,
                    can_delete_related=True
                )

    def save(self, commit=True):
        user = super().save(commit=False)

        if commit:
            user.save()
            # Проверяем, есть ли уже профиль
            if not hasattr(user, 'profile') or user.profile is None:
                Profile.objects.create(
                    user=user,
                    full_name=self.cleaned_data.get('full_name', ''),
                    phone=self.cleaned_data.get('phone', ''),
                    balance=self.cleaned_data.get('balance', 0),
                    avatar=self.cleaned_data.get('avatar'),
                )
            else:
                # Обновляем существующий профиль
                profile = user.profile
                profile.full_name = self.cleaned_data.get('full_name', '')
                profile.phone = self.cleaned_data.get('phone', '')
                profile.balance = self.cleaned_data.get('balance', 0)
                if self.cleaned_data.get('avatar'):
                    profile.avatar = self.cleaned_data.get('avatar')
                profile.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """Форма изменения пользователя"""
    full_name = forms.CharField(max_length=255, required=False, label='Полное имя')
    phone = forms.CharField(max_length=20, required=False, label='Телефон')
    balance = forms.DecimalField(max_digits=10, decimal_places=2, required=False, label='Баланс')
    avatar = forms.ModelChoiceField(
        queryset=Avatar.objects.all(),
        required=False,
        label='Аватар'
    )

    class Meta(UserChangeForm.Meta):
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Исправляем: нужно использовать поле avatar, а не src
        if 'avatar' in self.fields:
            from django.db.models.fields.related import ForeignKey
            avatar_field = Profile._meta.get_field('avatar')
            if isinstance(avatar_field, ForeignKey):
                self.fields['avatar'].widget = RelatedFieldWidgetWrapper(
                    self.fields['avatar'].widget,
                    avatar_field.remote_field,
                    admin_site=admin.site,
                    can_add_related=True,
                    can_change_related=True,
                    can_delete_related=True
                )

        if self.instance and self.instance.pk:
            try:
                profile = self.instance.profile
                self.initial['full_name'] = profile.full_name
                self.initial['phone'] = profile.phone
                self.initial['balance'] = profile.balance
                self.initial['avatar'] = profile.avatar
            except Profile.DoesNotExist:
                pass

    def save(self, commit=True):
        user = super().save(commit=commit)

        if commit:
            # Обновляем или создаем профиль
            profile, created = Profile.objects.get_or_create(user=user)
            profile.full_name = self.cleaned_data.get('full_name', '')
            profile.phone = self.cleaned_data.get('phone', '')
            profile.balance = self.cleaned_data.get('balance', 0)

            avatar = self.cleaned_data.get('avatar')
            if avatar:
                profile.avatar = avatar

            profile.save()

        return user


class AvatarAdmin(admin.ModelAdmin):
    list_display = ('id', 'src', 'alt', 'get_image_preview')
    list_display_links = ('id', 'src')
    search_fields = ('alt',)
    fields = ('src', 'alt')

    def get_image_preview(self, obj):
        if obj.src:
            return mark_safe(
                f'<img src="{obj.src.url}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />'
            )
        return "Нет изображения"

    get_image_preview.short_description = "Превью"

    def save_model(self, request, obj, form, change):
        if not obj.alt and obj.src:
            obj.alt = f"Avatar {obj.src.name.split('/')[-1]}"
        super().save_model(request, obj, form, change)


class CustomUserAdmin(UserAdmin):
    """Главная админка пользователей"""
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ('id', 'username', 'email', 'get_full_name', 'get_phone', 'get_balance', 'get_avatar_preview', 'is_staff',
                    'is_active', "is_soft_deleted")
    list_filter = ('is_staff', 'is_active', IsActiveFilter)
    search_fields = ('username', 'email', 'profile__full_name', 'profile__phone')
    list_editable = ('is_active',)
    list_display_links = ('id', 'username',)

    fieldsets = (
        ('Авторизация', {'fields': ('username', 'password')}),
        ('Контактные данные', {'fields': ('email',)}),
        ('Личная информация', {'fields': ('full_name', 'phone', 'avatar')}),
        ('Финансы', {'fields': ('balance',)}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'full_name', 'phone', 'balance', 'avatar'),
        }),
    )

    def get_full_name(self, obj):
        return obj.profile.full_name if hasattr(obj, 'profile') and obj.profile.full_name else '-'

    get_full_name.short_description = 'Полное имя'

    def get_phone(self, obj):
        return obj.profile.phone if hasattr(obj, 'profile') and obj.profile.phone else '-'

    get_phone.short_description = 'Телефон'

    def get_balance(self, obj):
        if hasattr(obj, 'profile'):
            return f"{obj.profile.balance} $"
        return "0 $"

    get_balance.short_description = 'Баланс'

    def get_avatar_preview(self, obj):
        if hasattr(obj, 'profile') and obj.profile and obj.profile.avatar and obj.profile.avatar.src:
            return mark_safe(
                f'<img src="{obj.profile.avatar.src.url}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />'
            )
        return "Нет аватара"

    get_avatar_preview.short_description = 'Аватар'



    actions = ['soft_delete_selected', 'restore_selected']
    has_delete_permission = lambda self, request, obj=None: False # убрала кнопку полного удаления пользователя

    def soft_delete_selected(self, request, queryset):
        """Мягкое удаление выбранных пользователей"""
        count = 0
        for user in queryset:
            if hasattr(user, 'profile'):
                user.profile.soft_delete()
                count += 1
        self.message_user(request, f'Пользователи ({count}) помечены как удаленные')

    soft_delete_selected.short_description = "Мягко удалить выбранных пользователей"

    def restore_selected(self, request, queryset):
        """Восстановление выбранных пользователей"""
        count = 0
        for user in queryset:
            if hasattr(user, 'profile'):
                user.profile.restore()
                count += 1
        self.message_user(request, f'Пользователи ({count}) восстановлены')

    restore_selected.short_description = "Восстановить выбранных пользователей"

    def is_soft_deleted(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            return not obj.profile.is_active
        return False

    is_soft_deleted.boolean = True
    is_soft_deleted.short_description = 'Мягко удален'

    def save_model(self, request, obj, form, change):
        """Сохраняем пользователя и профиль"""
        # Сохраняем сначала пользователя
        super().save_model(request, obj, form, change)

        # Обновляем профиль
        profile, created = Profile.objects.get_or_create(user=obj)
        profile.full_name = form.cleaned_data.get('full_name', '')
        profile.phone = form.cleaned_data.get('phone', '')
        profile.balance = form.cleaned_data.get('balance', 0)

        avatar = form.cleaned_data.get('avatar')
        if avatar:
            profile.avatar = avatar

        profile.save()

# Прокси-модель, для того чтобы Аватары были внутри одной группы с Groups Users
class AvatarAuthProxy(Avatar):
    class Meta:
        proxy = True
        app_label = 'auth'
        verbose_name = 'Аватар'
        verbose_name_plural = 'Аватары'


# Регистрация моделей
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
admin.site.register(AvatarAuthProxy, AvatarAdmin)