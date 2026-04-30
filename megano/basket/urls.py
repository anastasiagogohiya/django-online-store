from django.urls import path
from basket.views import BasketView



urlpatterns = [
    # basket
    path('basket/', BasketView.as_view(), name='basket'),
]