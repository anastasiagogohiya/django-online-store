from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from app_users.models import Profile
from basket.models import Basket, BasketItem
from catalog.models import Product
from order.mixins import OrderCreationMixin, OrderStockCheckMixin, OrderStockDecreaseMixin
from order.models import DeliveryCosts, DeliveryType, Order, OrderItem, OrderStatus, PaymentType


@pytest.mark.django_db
class TestOrderModel:
    def test_calculate_total_cost(self, profile, product):
        order = Order.objects.create(
            profile=profile,
            city="Moscow",
            address_delivery="Red Square",
            delivery_type=DeliveryType.FREE,
            payment_type=PaymentType.ONLINE,
            total_cost=0,
        )
        OrderItem.objects.create(order=order, product=product, quantity=2, price_at_time=Decimal("100.00"))
        order.calculate_total_cost()
        order.refresh_from_db()
        assert order.total_cost == Decimal("200.00")

    def test_create_from_basket_class_method(self, profile, basket_with_items, product):
        delivery_data = {
            "city": "SPB",
            "address": "Nevsky",
            "deliveryType": "express",
            "paymentType": "someone",
        }
        order = Order.create_from_basket(
            basket=basket_with_items,
            profile=profile,
            products_data=[],
            delivery_data=delivery_data,
        )
        delivery_costs = DeliveryCosts.get_solo()
        expected_products_price = product.price * 2
        expected_delivery_price = delivery_costs.express_delivery_price
        expected_total = expected_products_price + expected_delivery_price

        assert order.profile == profile
        assert order.city == "SPB"
        assert order.address_delivery == "Nevsky"
        assert order.delivery_type == "express"
        assert order.payment_type == "someone"
        assert order.status == OrderStatus.CREATED

        assert order.total_cost == expected_total
        assert order.delivery_price == expected_delivery_price

        assert not BasketItem.objects.filter(basket=basket_with_items).exists()
        order_item = order.items.first()
        assert order_item.product == product
        assert order_item.quantity == 2
        assert order_item.price_at_time == product.price


@pytest.mark.django_db
class TestOrderItemModel:
    @pytest.fixture
    def order(self, profile):
        return Order.objects.create(profile=profile, city="Moscow", address_delivery="Street")

    @pytest.fixture
    def inactive_product(self, category):
        return Product.objects.create(
            title="Inactive",
            description="desc",
            price=Decimal("50.00"),
            count=5,
            is_active=False,
            category=category,
        )

    def test_save_sets_price_at_time(self, order, product):
        item = OrderItem(order=order, product=product, quantity=1)
        item.save()
        assert item.price_at_time == product.price

    def test_clean_raises_if_product_inactive(self, order, inactive_product):
        item = OrderItem(order=order, product=inactive_product, quantity=1)
        with pytest.raises(ValidationError):
            item.full_clean()

    def test_clean_raises_if_product_not_selected(self, order):
        item = OrderItem(order=order, product=None, quantity=1)
        with pytest.raises(ValidationError):
            item.full_clean()


@pytest.mark.django_db
class TestOrderStockCheckMixin:
    @pytest.fixture
    def setup_stock(self, category):
        product1 = Product.objects.create(
            title="P1", description="d", count=5, price=100, is_active=True, category=category
        )
        product2 = Product.objects.create(
            title="P2", description="d", count=0, price=200, is_active=True, category=category
        )
        user = User.objects.create_user(username="test", password="test")
        profile, _ = Profile.objects.get_or_create(user=user)
        basket = Basket.objects.create(profile=profile)
        BasketItem.objects.create(basket=basket, product=product1, count=3)
        BasketItem.objects.create(basket=basket, product=product2, count=1)
        return basket, product1, product2

    def test_check_products_stock_fails(self, setup_stock):
        basket, product1, product2 = setup_stock
        mixin = OrderStockCheckMixin()
        basket_items = basket.items.select_related("product").all()
        available, errors = mixin.check_products_stock(basket_items)
        assert not available
        assert len(errors) == 1
        assert errors[0]["product_id"] == product2.id

    def test_validate_basket_before_order_raises_on_empty_basket(self, basket):
        mixin = OrderStockCheckMixin()
        with pytest.raises(ValidationError) as exc:
            mixin.validate_basket_before_order(basket)
        assert "Корзина пуста" in str(exc.value)

    def test_validate_basket_before_order_raises_on_stock_errors(self, setup_stock):
        basket, _, _ = setup_stock
        mixin = OrderStockCheckMixin()
        with pytest.raises(ValidationError) as exc:
            mixin.validate_basket_before_order(basket)
        assert "stock_errors" in exc.value.error_dict


@pytest.mark.django_db
class TestOrderStockDecreaseMixin:
    @pytest.fixture
    def setup_decrease(self, category):
        product = Product.objects.create(
            title="P", description="d", count=10, purchase_count=0, price=100, is_active=True, category=category
        )
        user = User.objects.create_user(username="test", password="test")
        profile, _ = Profile.objects.get_or_create(user=user)
        order = Order.objects.create(profile=profile, city="City", address_delivery="Addr")
        order_item = OrderItem.objects.create(order=order, product=product, quantity=3, price_at_time=100)
        return product, order, order_item

    def test_decrease_products_stock(self, setup_decrease):
        product, order, order_item = setup_decrease
        mixin = OrderStockDecreaseMixin()
        changes = mixin.decrease_products_stock([order_item])
        product.refresh_from_db()
        assert product.count == 7
        assert product.purchase_count == 3
        assert changes[0]["ordered"] == 3

    def test_restore_products_stock(self, setup_decrease):
        product, order, _ = setup_decrease
        product.count = 7
        product.purchase_count = 3
        product.save()
        mixin = OrderStockDecreaseMixin()
        mixin.restore_products_stock(order)
        product.refresh_from_db()
        assert product.count == 10
        assert product.purchase_count == 0


@pytest.mark.django_db
class TestOrderCreationMixin:
    @pytest.fixture
    def setup_creation(self, category):
        product = Product.objects.create(
            title="P", description="d", count=5, price=Decimal("100.00"), is_active=True, category=category
        )
        user = User.objects.create_user(username="testuser", password="test")
        profile, _ = Profile.objects.get_or_create(user=user)
        basket = Basket.objects.create(profile=profile)
        BasketItem.objects.create(basket=basket, product=product, count=2)
        return product, profile, basket

    def test_create_order_from_basket_success(self, setup_creation):
        product, profile, basket = setup_creation
        delivery_data = {
            "city": "Moscow",
            "address": "Tverskaya",
            "deliveryType": "free",
            "paymentType": "online",
        }
        mixin = OrderCreationMixin()
        order = mixin.create_order_from_basket(basket, profile, [], delivery_data, session_key=None)
        assert order.total_cost == product.price * 2
        assert order.status == OrderStatus.CREATED
        assert order.items.count() == 1
        assert order.items.first().quantity == 2
        product.refresh_from_db()
        assert product.count == 3
        assert not BasketItem.objects.filter(basket=basket).exists()

    def test_create_order_from_basket_stock_error(self, setup_creation):
        product, profile, basket = setup_creation
        product.count = 1
        product.save()
        delivery_data = {"city": "M", "address": "A", "deliveryType": "free", "paymentType": "online"}
        mixin = OrderCreationMixin()
        with pytest.raises(ValidationError) as exc:
            mixin.create_order_from_basket(basket, profile, [], delivery_data, session_key=None)
        assert "stock_errors" in exc.value.error_dict
        assert Order.objects.count() == 0
