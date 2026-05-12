from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse

from catalog.models import Category, Product
from catalog.views.popular_views import ProductsPopularView


@pytest.mark.django_db
class TestProductsPopularView:
    url = reverse("products-popular")

    def setup_method(self):
        cache.clear()

    def test_only_active_products(self, api_client):
        """Неактивные товары не попадают в выдачу"""
        cat = Category.objects.create(title="Cat", slug="cat")
        Product.objects.create(
            title="Active",
            slug="active",
            category=cat,
            price=100,
            is_active=True,
            ordering_index=1,
            purchase_count=10,
            description="Active",
        )
        Product.objects.create(
            title="Inactive",
            slug="inactive",
            category=cat,
            price=200,
            is_active=False,
            ordering_index=2,
            purchase_count=20,
            description="Inactive",
        )
        response = api_client.get(self.url)
        titles = [item["name"] for item in response.data]
        assert "Active" in titles
        assert "Inactive" not in titles

    def test_limit_to_8_products(self, api_client, popular_products):
        """Возвращается не более 8 товаров, даже если их больше"""
        response = api_client.get(self.url)
        assert len(response.data) == 8
        expected_titles = [f"Popular Product {i}" for i in range(8)]
        returned_titles = [item["name"] for item in response.data]
        assert returned_titles == expected_titles

    def test_sorting_ordering_index_desc(self, api_client, popular_products):
        """Сортировка сначала по убыванию ordering_index"""
        response = api_client.get(self.url)
        expected_titles = [f"Popular Product {i}" for i in range(8)]
        returned_titles = [item["name"] for item in response.data]
        assert returned_titles == expected_titles

    def test_secondary_sort_by_purchase_count(self, api_client, mixed_products):
        """При одинаковом ordering_index сортируются по убыванию purchase_count"""
        response = api_client.get(self.url)
        titles = [item["name"] for item in response.data]
        assert titles == ["Product B", "Product A", "Product C"]

    def test_cache_used(self, api_client, popular_products):
        """Второй запрос не обращается к БД (кэш)"""
        cache.clear()
        with patch("catalog.views.popular_views.Product.objects.filter", wraps=Product.objects.filter) as mock_filter:
            response1 = api_client.get(self.url)
            assert response1.status_code == 200
            assert mock_filter.call_count == 1
            response2 = api_client.get(self.url)
            assert response2.status_code == 200
            assert mock_filter.call_count == 1
            assert response1.data == response2.data

    def test_cache_key_depends_on_limit(self, api_client):
        """Изменение LIMITED_COUNT приводит к новому кэшу"""
        cat = Category.objects.create(title="LimitTest", slug="limit")
        for i in range(12):
            Product.objects.create(
                title=f"Prod {i}",
                slug=f"prod-{i}",
                category=cat,
                price=100,
                is_active=True,
                ordering_index=0,
                purchase_count=0,
                description=f"Desc {i}",
            )
        cache.clear()
        response_default = api_client.get(self.url)
        assert len(response_default.data) == 8
        with patch.object(ProductsPopularView, "LIMITED_COUNT", 3):
            response_small = api_client.get(self.url)
            assert len(response_small.data) == 3
        response_default2 = api_client.get(self.url)
        assert len(response_default2.data) == 8

    def test_response_structure(self, api_client, popular_products):
        """Проверяем, что ответ содержит ожидаемые поля сериализатора"""
        response = api_client.get(self.url)
        item = response.data[0]
        expected_fields = {
            "id",
            "category",
            "price",
            "count",
            "date",
            "name",
            "description",
            "freeDelivery",
            "images",
            "tags",
            "reviews",
            "rating",
        }
        assert set(item.keys()) == expected_fields
