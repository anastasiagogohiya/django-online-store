import datetime
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.urls import reverse

from catalog.models import Category, Product, Sale


@pytest.fixture
def category(db):
    return Category.objects.create(title="Тестовая категория", slug="test-cat")


@pytest.fixture
def all_sale_products(category):
    """Возвращает словарь с продуктами: active, expired, future, no_sale"""
    today = datetime.date.today()
    products = {}

    # Активная скидка
    p = Product.objects.create(
        title="Товар со скидкой",
        slug="sale-product",
        category=category,
        price=Decimal("1000.00"),
        count=10,
        is_active=True,
        description="Описание",
        free_delivery=True,
    )
    Sale.objects.create(
        product=p,
        sale_price=Decimal("800.00"),
        date_from=today - datetime.timedelta(days=1),
        date_to=today + datetime.timedelta(days=5),
    )
    products["active"] = p

    # Просроченная скидка
    p = Product.objects.create(
        title="Просроченная скидка",
        slug="expired-sale",
        category=category,
        price=Decimal("500.00"),
        count=5,
        is_active=True,
        description="Описание",
    )
    Sale.objects.create(
        product=p,
        sale_price=Decimal("400.00"),
        date_from=today - datetime.timedelta(days=5),
        date_to=today - datetime.timedelta(days=2),
    )
    products["expired"] = p

    # Будущая скидка
    p = Product.objects.create(
        title="Будущая скидка",
        slug="future-sale",
        category=category,
        price=Decimal("2000.00"),
        count=3,
        is_active=True,
        description="Описание",
    )
    Sale.objects.create(
        product=p,
        sale_price=Decimal("1500.00"),
        date_from=today + datetime.timedelta(days=1),
        date_to=today + datetime.timedelta(days=8),
    )
    products["future"] = p

    # Без скидки
    p = Product.objects.create(
        title="Обычный товар",
        slug="no-sale",
        category=category,
        price=Decimal("300.00"),
        count=20,
        is_active=True,
        description="Обычный товар",
    )
    products["no_sale"] = p

    return products


@pytest.fixture
def many_sale_products(category):
    """10 продуктов с активными скидками для тестов пагинации"""
    today = datetime.date.today()
    products = []
    for i in range(10):
        p = Product.objects.create(
            title=f"Sale Product {i}",
            slug=f"sale-{i}",
            category=category,
            price=Decimal("1000.00") + Decimal(i * 100),
            count=10,
            is_active=True,
            description=f"Описание {i}",
        )
        Sale.objects.create(
            product=p,
            sale_price=Decimal("800.00") + Decimal(i * 80),
            date_from=today - datetime.timedelta(days=1),
            date_to=today + datetime.timedelta(days=5),
        )
        products.append(p)
    return products


@pytest.mark.django_db
class TestSalesView:
    url = reverse("sales")  # замените на реальное имя URL

    def setup_method(self):
        cache.clear()

    def test_only_active_sales_returned(self, api_client, all_sale_products):
        response = api_client.get(self.url)
        assert response.status_code == 200
        titles = [item["title"] for item in response.data["items"]]
        assert all_sale_products["active"].title in titles
        assert all_sale_products["expired"].title not in titles
        assert all_sale_products["future"].title not in titles
        assert all_sale_products["no_sale"].title not in titles

    def test_pagination_page_size_8(self, api_client, many_sale_products):
        response = api_client.get(self.url)
        assert response.status_code == 200
        data = response.data
        assert len(data["items"]) == 8
        assert data["lastPage"] == 2

    @pytest.mark.parametrize(
        "page, expected_len, expected_page, expected_last",
        [
            (2, 2, 2, 2),  # вторая страница
            ("abc", 8, 1, 2),  # невалидный -> первая страница
        ],
    )
    def test_pagination_pages(self, api_client, many_sale_products, page, expected_len, expected_page, expected_last):
        response = api_client.get(self.url, {"currentPage": page})
        assert response.status_code == 200
        data = response.data
        assert len(data["items"]) == expected_len
        assert data["currentPage"] == expected_page
        assert data["lastPage"] == expected_last

    def test_sale_fields_serialized(self, api_client, all_sale_products):
        response = api_client.get(self.url)
        item = response.data["items"][0]
        # Проверяем наличие ключевых полей (в зависимости от сериализатора)
        expected_fields = {"salePrice", "price", "title"}
        assert expected_fields.issubset(item.keys())

    def test_cache_key_depends_on_page(self, api_client, many_sale_products):
        api_client.get(self.url, {"currentPage": 1})
        api_client.get(self.url, {"currentPage": 2})
        assert cache.get("sales_products_page_1") is not None
        assert cache.get("sales_products_page_2") is not None

    def test_response_structure(self, api_client, all_sale_products):
        response = api_client.get(self.url)
        data = response.data
        assert "items" in data
        assert "currentPage" in data
        assert "lastPage" in data
        assert isinstance(data["items"], list)
        if data["items"]:
            expected_fields = {"id", "title", "price", "salePrice", "dateFrom", "dateTo", "images"}
            assert expected_fields.issubset(data["items"][0].keys())
