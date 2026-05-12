# payment/tests_order_model_mixin.py
import json
import time

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from order.models import Order, OrderStatus
from payment.models import Payment

User = get_user_model()


@pytest.fixture
def created_order(auth_client, product, basket_with_items):
    products_data = [
        {
            "id": product.id,
            "category": product.category.id,
            "price": str(product.price),
            "count": 2,
            "date": "2023-01-01T00:00:00Z",
            "title": product.title,
            "description": product.description,
            "freeDelivery": True,
            "images": [],
            "tags": [],
            "reviews": 0,
            "rating": "0",
        }
    ]
    response = auth_client.post(reverse("orders"), data=json.dumps(products_data), content_type="application/json")
    order_id = response.data["orderId"]
    return Order.objects.get(id=order_id)


# ---------------------- Тесты ----------------------
@pytest.mark.django_db
class TestPaymentView:
    def test_payment_success(self, auth_client, created_order):
        url = reverse("payment", args=[created_order.id])
        payment_data = {
            "number": "66666666",
            "name": "Annoying Orange",
            "month": 12,
            "year": 2025,
            "code": "123",
        }
        response = auth_client.post(url, data=payment_data, format="json")
        assert response.status_code == 200
        assert response.data["status"] == "pending"
        payment_id = response.data["payment_id"]

        # Ждём выполнения задачи (в реальном тесте лучше использовать polling с таймаутом)
        for _ in range(10):
            payment = Payment.objects.get(id=payment_id)
            if payment.status != "pending":
                break
            time.sleep(0.2)

        assert payment.status == "success"
        assert payment.card_last4 == "6666"  # номер 66666666 → последние 4 = 6666

        created_order.refresh_from_db()
        assert created_order.status == OrderStatus.PAID

    def test_payment_already_paid(self, auth_client, created_order):
        url = reverse("payment", args=[created_order.id])
        payment_data = {
            "number": "66666666",
            "name": "Annoying Orange",
            "month": 12,
            "year": 2025,
            "code": "123",
        }
        auth_client.post(url, data=payment_data, format="json")
        response = auth_client.post(url, data=payment_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Заказ уже оплачен" in str(response.data)

    def test_payment_nonexistent_order(self, auth_client):
        url = reverse("payment", args=[9999])
        payment_data = {
            "number": "66666666",
            "name": "Annoying Orange",
            "month": 12,
            "year": 2025,
            "code": "123",
        }
        response = auth_client.post(url, data=payment_data, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_payment_invalid_card_data(self, auth_client, created_order):
        url = reverse("payment", args=[created_order.id])
        invalid_data = {
            "number": "123",
            "name": "Annoying Orange",
            "month": 13,
            "year": 2023,
            "code": "abc",
        }
        response = auth_client.post(url, data=invalid_data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        created_order.refresh_from_db()
        assert created_order.status == OrderStatus.CREATED

    def test_payment_other_user_order(self, created_order):
        other_user = User.objects.create_user(username="other", password="other")
        other_client = APIClient()
        other_client.force_login(other_user)
        url = reverse("payment", args=[created_order.id])
        payment_data = {
            "number": "66666666",
            "name": "Other User",
            "month": 12,
            "year": 2025,
            "code": "123",
        }
        response = other_client.post(url, data=payment_data, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
