from django.urls import path
from payment.views import PaymentView


urlpatterns = [
    path('payment/<int:id>/', PaymentView.as_view(), name='payment'),
]
