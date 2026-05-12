"""Разрешения"""
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser, BasePermission

class IsAuth(IsAuthenticated):
    """Авторизованные пользователи
    - OrderView (заказы)
    - OrderDetailView (детали заказа)
    - OrderCancelView (отмена)
    - PaymentView (оплата)
    - ReviewCreateView (создание отзывов)
    - ProfileView (профиль)
    - ProfilePasswordView (смена пароля)
    - ProfileAvatarUploadView (аватар)
    """
    pass



class AllowAll(AllowAny):
    """Публичный доступ
        - CatalogView (каталог)
        - CategoriesView
        - TagsView (теги)
        - SalesView (распродажи)
        - ProductsLimitedView (ограниченный тираж)
        - ProductView (детали товара)
        - ProductReviewsView (просмотр отзывов)
        - BasketView (корзина)
        - BannersView (просмотр баннеров)"""
    pass

class IsProfileOwner(BasePermission):
    """Разрешение: пользователь владелец профиля
    ЭТО НЕ НУЖНО!"""
    pass

class IsAdmin(IsAdminUser):
    """Только администраторы"""
    pass

class IsStaffOrReadOnly(BasePermission):
    """Сотрудники могут всё, остальные только чтение"""
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return request.user and request.user.is_staff