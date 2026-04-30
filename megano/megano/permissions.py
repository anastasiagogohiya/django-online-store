"""Разрешения"""
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser, BasePermission

class IsAuth(IsAuthenticated):
    """Авторизованные пользователи"""
    pass

class IsAdmin(IsAdminUser):
    """Только администраторы"""
    pass

class AllowAll(AllowAny):
    """Публичный доступ"""
    pass

class IsProfileOwner(BasePermission):
    """Разрешение: пользователь владелец профиля
    ЭТО НЕ НУЖНО!"""
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class IsStaffOrReadOnly(BasePermission):
    """Сотрудники могут всё, остальные только чтение"""
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user and request.user.is_staff