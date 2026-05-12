from decimal import Decimal

import pytest
from django.urls import reverse

from catalog.models import Category, Product, Tag


@pytest.fixture
def categories(db):
    return {
        "electronics": Category.objects.create(title="Электроника", slug="electronics"),
        "books": Category.objects.create(title="Книги", slug="books"),
    }


@pytest.fixture
def tags(db):
    return {
        "popular": Tag.objects.create(name="popular"),
        "new": Tag.objects.create(name="new"),
        "sale": Tag.objects.create(name="sale"),
        "limited": Tag.objects.create(name="limited"),
    }


@pytest.fixture
def products_with_tags(categories, tags):
    # Активные товары
    smartphone = Product.objects.create(
        title="Смартфон",
        slug="smartphone",
        category=categories["electronics"],
        price=Decimal("500.00"),
        count=10,
        is_active=True,
        description="Описание",
    )
    smartphone.tags.set([tags["popular"], tags["new"]])

    laptop = Product.objects.create(
        title="Ноутбук",
        slug="laptop",
        category=categories["electronics"],
        price=Decimal("1000.00"),
        count=5,
        is_active=True,
        description="Описание",
    )
    laptop.tags.set([tags["sale"], tags["limited"]])

    book = Product.objects.create(
        title="Python Book",
        slug="python-book",
        category=categories["books"],
        price=Decimal("50.00"),
        count=3,
        is_active=True,
        description="Описание",
    )
    book.tags.set([tags["popular"], tags["sale"]])

    # Неактивный товар (его тег не должен учитываться)
    inactive = Product.objects.create(
        title="Старый товар",
        slug="old",
        category=categories["electronics"],
        price=Decimal("10.00"),
        count=0,
        is_active=False,
        description="Неактивный",
    )
    inactive.tags.set([tags["limited"]])


@pytest.mark.django_db
class TestTagsView:
    url = reverse("tags")  # замените на реальное имя URL

    def _get_tag_names(self, response):
        return [item["name"] for item in response.data]

    @pytest.mark.parametrize(
        "category_key, expected_tags",
        [
            (None, {"popular", "new", "sale", "limited"}),  # все теги
            ("electronics", {"popular", "new", "sale", "limited"}),  # все четыре через активные товары
            ("books", {"popular", "sale"}),  # только два
        ],
    )
    def test_get_tags(self, api_client, categories, tags, products_with_tags, category_key, expected_tags):
        params = {"category": categories[category_key].id} if category_key else {}
        response = api_client.get(self.url, params)
        assert response.status_code == 200
        assert set(self._get_tag_names(response)) == expected_tags

    def test_get_tags_by_nonexistent_category_returns_empty_list(self, api_client):
        response = api_client.get(self.url, {"category": 99999})
        assert response.status_code == 200
        assert response.data == []

    def test_invalid_category_id_type_returns_500(self, api_client):
        # Текущее поведение: при передаче строки вместо числа возникает ValueError,
        # который перехватывается общим декоратором и возвращает 500
        response = api_client.get(self.url, {"category": "abc"})
        assert response.status_code == 500

    def test_tags_serializer_fields(self, api_client, tags):
        response = api_client.get(self.url)
        item = response.data[0]
        assert "id" in item
        assert "name" in item
        assert len(item) == 2
