# megano/megano/urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("frontend.urls")),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path("api/", include("api.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# django_extensions (все urls для информации, они внутри frontend.urls, см выше)
# python manage.py show_urls
# ==============================================
# ФРОНТЕНД ПУТИ
# ==============================================
# '' - Главная страница (работает)
# 'about/' - О нас (работает)
# 'sign-in/' - Вход в аккаунт (работает)
# 'sign-up/' - Регистрация (работает)
# 'profile/' - Профиль пользователя (работает)

# 'catalog/' - Каталог
# 'catalog/<int:id>/' - Карточка товара в каталоге

# 'cart/' - Корзина
# 'history-order/' - История заказов
# 'order-detail/<int:id>/' - Детали заказа
# 'orders/<int:id>/' - Заказы
# 'payment/<int:id>/' - Страница оплаты
# 'payment-someone/' - Оплата для другого человека
# 'product/<int:id>/' - Карточка товара
# 'progress-payment/' - Прогресс оплаты
# 'sale/' - Распродажа



# ==============================================
# API ПУТИ (JSON данные)
# ==============================================
# 'api/sign-in/' - Вход (API) (swagger работает)
# 'api/sign-up/' - Регистрация (API)
# 'api/sign-out/' - Выход (API) (works, swagger работает)
# 'api/profile/' - Получение/обновление данных профиля (работает, get swagger работает, post swagger работает
# 'api/profile/password/' - Смена пароля (работает, только ПОСТ запрос, swagger работает)
# 'api/profile/avatar/' - Загрузка аватарки
# 'api/categories/' - Категории товаров