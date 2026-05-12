# megano/api/urls.py
from django.urls import include, path

# Все api urls, пути фронтэнда и бэкэнда в megano/urls.py
urlpatterns = [
    path("", include("app_users.urls")),
    path("", include("catalog.urls")),
    path("", include("basket.urls")),
    path("", include("order.urls")),
    path("", include("payment.urls")),
]
