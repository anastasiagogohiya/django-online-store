import json
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from basket.models import Basket, BasketItem
from catalog.models import Product
from order.models import DeliveryType, Order, OrderItem, OrderStatus, PaymentType
from order.serializers import CreateOrderSerializer, OrderIdSerializer, OrderSerializer
from order.utils import check_basket_not_empty, check_profile, get_user_basket

# ---------------------- вью ----------------------


@pytest.mark.django_db
class TestOrderView:
    def test_get_orders_list(self, auth_client, product, basket_with_items):
        # создаём заказ
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
        auth_client.post(reverse("orders"), data=json.dumps(products_data), content_type="application/json")
        # запрашиваем список
        response = auth_client.get(reverse("orders"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["status"] == OrderStatus.CREATED

    def test_create_order_success(self, auth_client, product, basket_with_items):
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
        assert response.status_code == status.HTTP_201_CREATED
        order_id = response.data["orderId"]
        order = Order.objects.get(id=order_id)
        assert order.total_cost == product.price * 2
        assert not BasketItem.objects.filter(basket=basket_with_items).exists()
        product.refresh_from_db()
        assert product.count == 8

    def test_create_order_empty_basket(self, auth_client, product, basket_with_items):
        basket_with_items.items.all().delete()  # очищаем корзину
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
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Корзина пуста" in str(response.data)

    def test_create_order_wrong_product_id(self, auth_client, basket_with_items):
        products_data = [
            {
                "id": 9999,
                "category": 1,
                "price": "100.00",
                "count": 1,
                "date": "2023-01-01T00:00:00Z",
                "title": "Ghost",
                "description": "Описание",
                "freeDelivery": True,
                "images": [],
                "tags": [],
                "reviews": 0,
                "rating": "0",
            }
        ]
        response = auth_client.post(reverse("orders"), data=json.dumps(products_data), content_type="application/json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data
        assert "отсутствуют в корзине" in response.data["error"]


@pytest.mark.django_db
class TestOrderDetailView:
    @pytest.fixture
    def created_order(self, auth_client, product, basket_with_items):
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

    def test_get_order_detail(self, auth_client, created_order):
        url = reverse("order_detail", args=[created_order.id])
        response = auth_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == created_order.id
        assert response.data["status"] == OrderStatus.CREATED

    def test_post_update_order_details(self, auth_client, created_order):
        url = reverse("order_detail", args=[created_order.id])
        payload = {
            "city": "Moscow",
            "address": "Tverskaya 1",
            "deliveryType": DeliveryType.EXPRESS,
            "paymentType": PaymentType.SOMEONE,
        }
        response = auth_client.post(url, data=payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        created_order.refresh_from_db()
        assert created_order.city == "Moscow"
        assert created_order.address_delivery == "Tverskaya 1"
        assert created_order.delivery_type == DeliveryType.EXPRESS
        assert created_order.payment_type == PaymentType.SOMEONE
        assert created_order.status == OrderStatus.ACCEPTED


# ---------------------- Тесты сериализаторов ----------------------
@pytest.mark.django_db
class TestSerializers:
    @pytest.fixture
    def order_with_items(self, profile, product):
        order = Order.objects.create(
            profile=profile,
            city="Moscow",
            address_delivery="Lenina 5",
            delivery_type="free",
            payment_type="online",
            total_cost=Decimal("199.98"),
            status=OrderStatus.ACCEPTED,
        )
        OrderItem.objects.create(order=order, product=product, quantity=2, price_at_time=Decimal("99.99"))
        return order

    def test_order_serializer(self, order_with_items, profile):
        serializer = OrderSerializer(instance=order_with_items)
        data = serializer.data
        assert data["id"] == order_with_items.id
        assert data["city"] == "Moscow"
        assert data["address"] == "Lenina 5"
        assert data["deliveryType"] == "free"
        assert data["paymentType"] == "online"
        assert data["totalCost"] == "199.98"
        assert data["status"] == "accepted"
        assert data["fullName"] == profile.full_name
        assert data["phone"] == profile.phone
        assert len(data["products"]) == 1
        assert data["products"][0]["count"] == 2

    def test_create_order_serializer_validation(self):
        valid_data = [
            {
                "id": 1,
                "category": 5,
                "price": "100.00",
                "count": 3,
                "date": "2023-01-01T00:00:00Z",
                "title": "Item",
                "description": "desc",
                "freeDelivery": True,
                "images": [],
                "tags": [],
                "reviews": 5,
                "rating": "4.5",
            }
        ]
        serializer = CreateOrderSerializer(data=valid_data, many=True)
        assert serializer.is_valid()

    def test_order_id_serializer(self, order_with_items):
        serializer = OrderIdSerializer(instance=order_with_items)
        assert serializer.data["orderId"] == order_with_items.id


# ---------------------- Тесты утилит ----------------------
@pytest.mark.django_db
class TestUtils:
    def test_check_profile_success(self, auth_client, user):
        request = auth_client.get("/").wsgi_request
        request.user = user
        profile, error = check_profile(request)
        assert profile is not None
        assert error is None

    def test_get_user_basket_found(self, profile):
        basket = Basket.objects.create(profile=profile)
        result, error = get_user_basket(profile, session_key=None)
        assert result == basket
        assert error is None

    def test_get_user_basket_returns_basket_for_profile(self, profile):
        result, error = get_user_basket(profile, session_key=None)
        assert result is not None
        assert isinstance(result, Basket)
        assert result.profile == profile
        assert error is None

    def test_check_basket_not_empty(self, profile, category):
        basket = Basket.objects.create(profile=profile)
        product = Product.objects.create(
            title="TempProd", description="d", price=10, count=1, is_active=True, category=category
        )
        BasketItem.objects.create(basket=basket, product=product, count=1)
        is_empty, error = check_basket_not_empty(basket)
        assert not is_empty
        assert error is None

    def test_check_basket_empty(self, profile):
        basket = Basket.objects.create(profile=profile)
        is_empty, error = check_basket_not_empty(basket)
        assert is_empty
        assert error.status_code == status.HTTP_400_BAD_REQUEST
