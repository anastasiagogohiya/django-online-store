from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from catalog.models import Category, Product, ProductImage, Sale, Tag


@pytest.fixture
def staff_client(db):
    user = User.objects.create_user(username="admin", password="admin", is_staff=True)
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def category(db):
    return Category.objects.create(title="Тестовая категория", slug="test-cat")


@pytest.fixture
def base_product(category):
    """активный товар"""
    return Product.objects.create(
        title="Тестовый товар",
        slug="test-product",
        category=category,
        price=Decimal("1000.00"),
        count=10,
        is_active=True,
        description="Описание",
        full_description="Полное описание",
    )


@pytest.fixture
def active_product(category):
    """Активный товар с тегом и изображением для API-тестов"""
    product = Product.objects.create(
        title="Активный товар",
        slug="active-product",
        category=category,
        price=Decimal("999.99"),
        count=10,
        free_delivery=True,
        is_active=True,
        description="Активный товар для тестов",
        full_description="Полное описание активного товара",
    )
    tag = Tag.objects.create(name="популярный")
    product.tags.set([tag])
    image = ProductImage.objects.create(
        image=SimpleUploadedFile("test.jpg", b"fake_image_content", content_type="image/jpeg"),
        alt="тестовое изображение",
    )
    product.images.set([image])
    return product


@pytest.fixture
def inactive_product(category):
    return Product.objects.create(
        title="Неактивный товар",
        slug="inactive-product",
        category=category,
        price=Decimal("500.00"),
        count=0,
        free_delivery=False,
        is_active=False,
        description="Неактивный товар",
        full_description="",
    )


# ---------------------- Тесты API ----------------------
@pytest.mark.django_db
class TestProductView:
    url_name = "product_id"

    def setup_method(self):
        cache.clear()

    def test_get_active_product_success(self, api_client, active_product):
        url = reverse(self.url_name, args=[active_product.id])
        response = api_client.get(url)
        assert response.status_code == 200
        data = response.data
        assert data["id"] == active_product.id
        assert data["title"] == active_product.title
        assert "images" in data
        assert "tags" in data

    def test_get_inactive_product_returns_404_for_anon(self, api_client, inactive_product):
        url = reverse(self.url_name, args=[inactive_product.id])
        response = api_client.get(url)
        assert response.status_code == 404

    def test_get_nonexistent_product_404(self, api_client):
        url = reverse(self.url_name, args=[99999])
        response = api_client.get(url)
        assert response.status_code == 404

    def test_cache_is_used(self, api_client, active_product):
        url = reverse(self.url_name, args=[active_product.id])
        response1 = api_client.get(url)
        response2 = api_client.get(url)
        assert response1.status_code == 200
        assert response1.data == response2.data

    def test_cache_key_depends_on_id(self, api_client, active_product, inactive_product):
        cache_key_active = f"product_detail_{active_product.id}"
        cache_key_inactive = f"product_detail_{inactive_product.id}"
        api_client.get(reverse(self.url_name, args=[active_product.id]))
        api_client.get(reverse(self.url_name, args=[inactive_product.id]))
        assert cache.get(cache_key_active) is not None
        assert cache.get(cache_key_inactive) is None


# ---------------------- Тесты свойств товара (цена, скидка, доступность, валидация) ----------------------
@pytest.mark.django_db
class TestProductProperties:
    # ---------- current_price ----------
    def test_current_price_without_sale(self, base_product):
        assert base_product.current_price == Decimal("1000.00")

    def test_current_price_with_inactive_sale(self, base_product):
        yesterday = timezone.now().date() - timedelta(days=1)
        two_days_ago = yesterday - timedelta(days=1)
        Sale.objects.create(
            product=base_product,
            sale_price=Decimal("800.00"),
            date_from=two_days_ago,
            date_to=yesterday,
        )
        assert base_product.current_price == Decimal("1000.00")

    def test_current_price_with_future_sale(self, base_product):
        tomorrow = timezone.now().date() + timedelta(days=1)
        next_week = tomorrow + timedelta(days=7)
        Sale.objects.create(
            product=base_product,
            sale_price=Decimal("750.00"),
            date_from=tomorrow,
            date_to=next_week,
        )
        assert base_product.current_price == Decimal("1000.00")

    def test_current_price_with_active_sale(self, base_product):
        today = timezone.now().date()
        Sale.objects.create(
            product=base_product,
            sale_price=Decimal("700.00"),
            date_from=today - timedelta(days=1),
            date_to=today + timedelta(days=5),
        )
        assert base_product.current_price == Decimal("700.00")

    def test_current_price_with_sale_equal_to_original(self, base_product):
        today = timezone.now().date()
        Sale.objects.create(
            product=base_product,
            sale_price=Decimal("1000.00"),
            date_from=today - timedelta(days=1),
            date_to=today + timedelta(days=5),
        )
        assert base_product.current_price == Decimal("1000.00")

    # ---------- has_active_sale ----------
    def test_has_active_sale_false_when_no_sale(self, base_product):
        assert base_product.has_active_sale is False

    def test_has_active_sale_false_when_sale_inactive(self, base_product):
        yesterday = timezone.now().date() - timedelta(days=1)
        two_days_ago = yesterday - timedelta(days=1)
        Sale.objects.create(
            product=base_product,
            sale_price=Decimal("800.00"),
            date_from=two_days_ago,
            date_to=yesterday,
        )
        assert base_product.has_active_sale is False

    def test_has_active_sale_true_when_sale_active(self, base_product):
        today = timezone.now().date()
        Sale.objects.create(
            product=base_product,
            sale_price=Decimal("700.00"),
            date_from=today - timedelta(days=1),
            date_to=today + timedelta(days=5),
        )
        assert base_product.has_active_sale is True

    # ---------- available ----------
    def test_available_true_when_count_positive(self, base_product):
        base_product.count = 5
        assert base_product.available is True

    def test_available_false_when_count_zero(self, base_product):
        base_product.count = 0
        assert base_product.available is False

    def test_available_false_when_count_negative(self, base_product):
        base_product.count = -1
        assert base_product.available is False

    # ---------- clean validation ----------
    def test_clean_raises_for_negative_price(self, base_product):
        base_product.price = Decimal("-10.00")
        with pytest.raises(ValidationError) as exc:
            base_product.clean()
        assert "price" in exc.value.message_dict

    def test_clean_raises_for_negative_count(self, base_product):
        base_product.count = -5
        with pytest.raises(ValidationError) as exc:
            base_product.clean()
        assert "count" in exc.value.message_dict

    def test_clean_passes_for_valid_data(self, base_product):
        base_product.price = Decimal("100.00")
        base_product.count = 10
        base_product.clean()  # не должно быть исключения


# ---------------------- Тесты мягкого и жёсткого удаления ----------------------
@pytest.mark.django_db
class TestProductDeleteRestore:
    @pytest.fixture
    def product_for_delete(self, category):
        return Product.objects.create(
            title="Тестовый товар",
            slug="test-delete",
            category=category,
            price=Decimal("100.00"),
            count=10,
            is_active=True,
            description="Описание",
        )

    def test_soft_delete_sets_is_active_false(self, product_for_delete):
        assert product_for_delete.is_active is True
        product_for_delete.soft_delete()
        product_for_delete.refresh_from_db()
        assert product_for_delete.is_active is False
        assert Product.objects.filter(id=product_for_delete.id).exists()

    def test_restore_sets_is_active_true(self, product_for_delete):
        product_for_delete.is_active = False
        product_for_delete.save()
        product_for_delete.restore()
        product_for_delete.refresh_from_db()
        assert product_for_delete.is_active is True

    def test_hard_delete_removes_object(self, product_for_delete):
        pk = product_for_delete.id
        product_for_delete.hard_delete()
        assert not Product.objects.filter(id=pk).exists()
