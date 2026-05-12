import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status

from app_users.models import Profile, User
from basket.models import Basket, BasketItem
from catalog.models import Category, Product


@pytest.fixture
def user(db):
    user = User.objects.create_user(username="testuser", password="testpass")
    Profile.objects.get_or_create(user=user, defaults={"is_active": True})
    return user


@pytest.fixture
def another_user(db):
    user = User.objects.create_user(username="another", password="testpass")
    Profile.objects.get_or_create(user=user, defaults={"is_active": True})
    return user


@pytest.fixture
def category(db):
    return Category.objects.create(title="Test Category")


@pytest.fixture
def product(db, category):
    return Product.objects.create(
        id=1,
        title="Test Product",
        price=100.0,
        count=10,
        is_active=True,
        free_delivery=True,
        category=category,
        description="Test description",
    )


@pytest.fixture
def product_out_of_stock(db, category):
    return Product.objects.create(
        id=2, title="Out of Stock", price=50.0, count=0, is_active=True, category=category, description="Out of stock"
    )


@pytest.fixture
def basket_for_user(user):
    basket, _ = Basket.objects.get_or_create(profile=user.profile)
    return basket


@pytest.fixture
def basket_for_session(db):
    basket, _ = Basket.objects.get_or_create(session_key="test_session", defaults={"profile": None})
    return basket


@pytest.fixture
def basket_item(basket_for_user, product):
    return BasketItem.objects.create(basket=basket_for_user, product=product, count=3)


@pytest.fixture
def auth(request):
    return request.param


# ---------- Тесты для BasketView ----------
@pytest.mark.django_db
class TestBasketView:
    url = reverse("basket")

    def test_get_basket_authenticated(self, api_client, user, basket_for_user, basket_item):
        api_client.force_authenticate(user=user)
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == basket_item.id
        assert response.data[0]["count"] == 3

    def test_get_basket_anonymous(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    @pytest.mark.parametrize(
        "auth, payload, expected_status, expected_count, initial_count",
        [
            ("auth", {"id": 1, "count": 2}, status.HTTP_200_OK, 2, 0),
            ("auth", {"id": 1, "count": 3}, status.HTTP_200_OK, 6, 3),
            (None, {"id": 1, "count": 1}, status.HTTP_200_OK, 1, 0),
            ("auth", {"id": 1, "count": 0}, status.HTTP_400_BAD_REQUEST, None, 0),
            ("auth", {"id": 1, "count": -5}, status.HTTP_400_BAD_REQUEST, None, 0),
            ("auth", {"id": 999, "count": 1}, status.HTTP_400_BAD_REQUEST, None, 0),
            ("auth", {"id": 2, "count": 1}, status.HTTP_400_BAD_REQUEST, None, 0),
            ("auth", {"id": 1, "count": 20}, status.HTTP_400_BAD_REQUEST, None, 0),
        ],
        indirect=["auth"],
    )
    def test_post_add_item(
        self,
        api_client,
        user,
        auth,
        payload,
        expected_status,
        expected_count,
        initial_count,
        product,
        product_out_of_stock,
    ):
        if auth == "auth":
            api_client.force_authenticate(user=user)
            basket, _ = Basket.objects.get_or_create(profile=user.profile)
        else:
            api_client.logout()
            api_client.session.create()
            session_key = api_client.session.session_key
            basket, _ = Basket.objects.get_or_create(session_key=session_key, profile=None)

        if initial_count > 0:
            BasketItem.objects.create(basket=basket, product=product, count=initial_count)

        response = api_client.post(self.url, payload, format="json")
        assert response.status_code == expected_status

        if expected_status == status.HTTP_200_OK:
            items = BasketItem.objects.filter(basket=basket)
            assert len(response.data) == len(items)
            assert response.data[0]["count"] == expected_count
        else:
            if initial_count > 0:
                items = BasketItem.objects.filter(basket=basket)
                assert items[0].count == initial_count
            else:
                assert BasketItem.objects.filter(basket=basket).count() == 0

    @pytest.mark.parametrize(
        "auth, initial_count, payload, expected_status, final_count, item_exists",
        [
            ("auth", 5, {"id": 1, "count": 2}, status.HTTP_200_OK, 3, True),
            ("auth", 5, {"id": 1, "count": 5}, status.HTTP_200_OK, None, False),
            ("auth", 5, {"id": 1, "count": 0}, status.HTTP_400_BAD_REQUEST, 5, True),
            (None, 3, {"id": 1, "count": 1}, status.HTTP_200_OK, 2, True),
            ("auth", 3, {"id": 1, "count": -1}, status.HTTP_400_BAD_REQUEST, 3, True),
            ("auth", 3, {"id": 999, "count": 1}, status.HTTP_400_BAD_REQUEST, 3, True),
        ],
        indirect=["auth"],
    )
    def test_delete_item(
        self, api_client, user, auth, initial_count, payload, expected_status, final_count, item_exists, product
    ):
        if auth == "auth":
            basket = Basket.objects.create(profile=user.profile)
        else:
            api_client.logout()
            api_client.session.create()
            session_key = api_client.session.session_key
            basket = Basket.objects.create(session_key=session_key, profile=None)

        basket_item = BasketItem.objects.create(basket=basket, product=product, count=initial_count)

        if auth == "auth":
            api_client.force_authenticate(user=user)

        response = api_client.delete(self.url, payload, format="json")
        assert response.status_code == expected_status

        if expected_status == status.HTTP_200_OK:
            if item_exists:
                basket_item.refresh_from_db()
                assert basket_item.count == final_count
                assert len(response.data) == 1
                assert response.data[0]["count"] == final_count
            else:
                with pytest.raises(BasketItem.DoesNotExist):
                    basket_item.refresh_from_db()
                assert response.data == []
        else:
            basket_item.refresh_from_db()
            assert basket_item.count == initial_count


# ---------- Тесты для моделей ----------
@pytest.mark.django_db
class TestBasketModel:
    def test_attach_profile(self, user, basket_for_session):
        basket = basket_for_session
        assert basket.profile is None
        basket.attach_profile(user.profile)
        basket.refresh_from_db()
        assert basket.profile == user.profile

    def test_total_price(self, basket_for_user, product):
        BasketItem.objects.create(basket=basket_for_user, product=product, count=2)
        assert basket_for_user.get_total_price() == 200.0

    def test_total_items(self, basket_for_user, product):
        BasketItem.objects.create(basket=basket_for_user, product=product, count=3)
        assert basket_for_user.get_total_items() == 3

    def test_clean_inactive_profile(self, user):
        user.profile.is_active = False
        user.profile.save()
        basket = Basket(profile=user.profile)
        with pytest.raises(ValidationError):
            basket.clean()


@pytest.mark.django_db
class TestBasketItemModel:
    def test_clean_inactive_product(self, basket_for_user, product):
        product.is_active = False
        product.save()
        item = BasketItem(basket=basket_for_user, product=product, count=1)
        with pytest.raises(ValidationError):
            item.clean()

    def test_total_price_property(self, basket_for_user, product):
        item = BasketItem.objects.create(basket=basket_for_user, product=product, count=4)
        assert item.total_price == 400.0


# ---------- Дополнительные тесты для миксина ----------
@pytest.mark.django_db
class TestBasketMixin:
    def test_get_or_create_basket_updates_session_key(self, user, api_client):
        from django.test import RequestFactory

        from basket.mixins import BasketMixin

        basket = Basket.objects.create(profile=user.profile, session_key=None)

        factory = RequestFactory()
        request = factory.get("/")
        request.user = user
        request.session = api_client.session
        request.session.create()
        request.session.save()

        mixin = BasketMixin()
        retrieved_basket = mixin.get_or_create_basket(request)

        assert retrieved_basket.id == basket.id
        basket.refresh_from_db()
        assert basket.session_key == request.session.session_key


# ---------- Тест для удаления через product.id ----------
@pytest.mark.django_db
class TestBasketDeleteByProductId:
    def test_delete_by_product_id(self, api_client, user, product, basket_for_user):
        basket_item = BasketItem.objects.create(basket=basket_for_user, product=product, count=5)

        api_client.force_authenticate(user=user)
        url = reverse("basket")

        payload = {"id": product.id, "count": 2}
        response = api_client.delete(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        basket_item.refresh_from_db()
        assert basket_item.count == 3
        assert response.data[0]["count"] == 3

        payload = {"id": product.id, "count": 3}
        response = api_client.delete(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        with pytest.raises(BasketItem.DoesNotExist):
            basket_item.refresh_from_db()
        assert response.data == []


# ---------- Тест для недоступного товара при обновлении ----------
@pytest.mark.django_db
class TestBasketSerializerUnavailableProduct:
    def test_post_update_unavailable_product(self, api_client, user, product, basket_for_user):
        product.count = 0
        product.save()
        basket_item = BasketItem.objects.create(basket=basket_for_user, product=product, count=2)

        api_client.force_authenticate(user=user)
        url = reverse("basket")
        payload = {"id": basket_item.id, "count": 1}
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == 400
        assert response.data["error_type"] == "ValidationError"
        assert "недоступен" in response.data["error"]
        assert "'id'" in response.data["error"] or '"id"' in response.data["error"]
