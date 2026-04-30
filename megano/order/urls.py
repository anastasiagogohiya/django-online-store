from django.urls import path
from order.views import OrderView, OrderDetailView



urlpatterns = [
    # order
    path('orders/', OrderView.as_view(), name='orders'),
    path('order/<int:id>/', OrderDetailView.as_view(), name='order_detail'),
    path('order/<int:id>', OrderDetailView.as_view(), name='order_detail'),
]
