from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse

from catalog.models import Category, Product
from catalog.views.limited_views import ProductsLimitedView


@pytest.mark.django_db
class TestProductsLimitedView:
    url = reverse("products-limited")

    def setup_method(self):
        cache.clear()

    def test_returns_only_limited_active_products(
        self, api_client, limited_products, non_limited_products, inactive_limited_products
    ):
        response = api_client.get(self.url)
        assert response.status_code == 200
        data = response.data
        returned_titles = [item["name"] for item in data]
        assert len(returned_titles) == len(limited_products)
        for prod in limited_products:
            assert prod.title in returned_titles
        for prod in non_limited_products:
            assert prod.title not in returned_titles
        for prod in inactive_limited_products:
            assert prod.title not in returned_titles

    def test_limits_to_16_products(self, api_client):
        cat = Category.objects.create(title="Много", slug="many")
        for i in range(20):
            Product.objects.create(
                title=f"Limited {i}",
                slug=f"lim-{i}",
                category=cat,
                price=100,
                count=1,
                is_limited=True,
                is_active=True,
                ordering_index=0,
                description=f"Описание {i}",
            )
        response = api_client.get(self.url)
        assert len(response.data) == 16
        ids = [item["id"] for item in response.data]
        assert len(set(ids)) == 16

    @pytest.mark.parametrize(
        "ordering_index, purchase_count, expected_order_titles",
        [
            # Исправлено: для [5,3,1] порядок по убыванию: 5 (i=0), 3 (i=1), 1 (i=2)
            ([5, 3, 1], [10, 20, 30], ["Limited 0", "Limited 1", "Limited 2"]),
            ([2, 2, 2], [5, 10, 15], ["Limited 2", "Limited 1", "Limited 0"]),
            ([10, 5, 0], [0, 0, 0], ["Limited 0", "Limited 1", "Limited 2"]),
        ],
    )
    def test_sorting_order(self, api_client, ordering_index, purchase_count, expected_order_titles):
        cat = Category.objects.create(title="Сорт", slug="sort")
        for i, (idx, cnt) in enumerate(zip(ordering_index, purchase_count)):
            Product.objects.create(
                title=f"Limited {i}",
                slug=f"lim-{i}",
                category=cat,
                price=100,
                count=1,
                description=f"Товар {i}",
                is_limited=True,
                is_active=True,
                ordering_index=idx,
                purchase_count=cnt,
            )
        response = api_client.get(self.url)
        titles = [item["name"] for item in response.data]
        assert titles == expected_order_titles

    def test_cache_is_used(self, api_client, limited_products):
        """Второй запрос идёт из кэша (Product.objects.filter не вызывается повторно)"""
        cache.clear()
        with patch("catalog.views.limited_views.Product.objects.filter", wraps=Product.objects.filter) as mock_filter:
            response1 = api_client.get(self.url)
            assert response1.status_code == 200
            assert mock_filter.call_count == 1
            response2 = api_client.get(self.url)
            assert response2.status_code == 200
            assert mock_filter.call_count == 1  # второй раз filter не вызывался
            assert response1.data == response2.data

    def test_cache_key_depends_on_limit(self, api_client):
        cat = Category.objects.create(title="KeyTest", slug="key")
        for i in range(10):
            Product.objects.create(
                title=f"Key {i}",
                slug=f"key-{i}",
                category=cat,
                price=100,
                count=1,
                is_limited=True,
                is_active=True,
                description=f"Key {i}",
            )
        cache.clear()
        with patch.object(ProductsLimitedView, "LIMITED_COUNT", 3):
            response_small = api_client.get(self.url)
            assert response_small.status_code == 200
            assert len(response_small.data) == 3
        cache.clear()
        response_full = api_client.get(self.url)
        assert len(response_full.data) == 10
