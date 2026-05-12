import json

import pytest
from django.urls import reverse
from rest_framework.request import Request as DRFRequest
from rest_framework.test import APIRequestFactory

from catalog.models import Product
from catalog.utils import (
    apply_price_filter,
    apply_search_filter,
    extract_filters,
    get_pagination_params,
    to_bool,
)


class TestCatalogView:
    url = reverse("catalog")

    def test_only_active_products_appear(self, api_client, catalog_products):
        """Проверяем, что неактивные товары не выводятся"""
        inactive = catalog_products[0]  # Нижнее бельё
        inactive.is_active = False
        inactive.save()

        response = api_client.get(self.url)
        assert response.status_code == 200
        items = response.data["items"]
        ids = [item["id"] for item in items]
        assert inactive.id not in ids
        assert len(items) == 2  # остаются гантели и планшет

    def test_search_by_name(self, api_client, catalog_products):
        """Поиск по названию"""
        response = api_client.get(self.url, {"filter": '{"name": "Гантели"}'})
        assert response.status_code == 200
        items = response.data["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Гантели 5 кг"

        response = api_client.get(self.url, {"filter": '{"name": "Планшет"}'})
        items = response.data["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Планшет Samsung"

    def test_price_filter(self, api_client, catalog_products):
        """Фильтр по диапазону цен"""
        # Гантели (2000) и планшет (25000) не входят в диапазон 100-600
        response = api_client.get(self.url, {"filter": '{"minPrice": 100, "maxPrice": 600}'})
        items = response.data["items"]
        assert len(items) == 0

        # Цена от 1500 до 3000 – подходят бельё (1500) и гантели (2000)
        response = api_client.get(self.url, {"filter": '{"minPrice": 1500, "maxPrice": 3000}'})
        titles = {item["name"] for item in response.data["items"]}
        assert titles == {"Нижнее белье Романтика", "Гантели 5 кг"}

        # Цена от 20000 – только планшет
        response = api_client.get(self.url, {"filter": '{"minPrice": 20000}'})
        items = response.data["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Планшет Samsung"

    def test_free_delivery_filter(self, api_client, catalog_products):
        """Фильтр по бесплатной доставке"""
        response = api_client.get(self.url, {"filter": '{"freeDelivery": true}'})
        titles = [item["name"] for item in response.data["items"]]
        # Бесплатная доставка у белья (True) и планшета (True), у гантелей False
        assert "Нижнее белье Романтика" in titles
        assert "Планшет Samsung" in titles
        assert "Гантели 5 кг" not in titles

    def test_available_filter(self, api_client, catalog_products):
        """Фильтр 'только в наличии'"""
        response = api_client.get(self.url, {"filter": '{"available": true}'})
        titles = [item["name"] for item in response.data["items"]]
        # У всех трёх товаров count > 0 (25, 8, 3), так что все три должны быть
        assert len(titles) == 3
        assert "Гантели 5 кг" in titles

        # Сделаем один товар недоступным
        out_of_stock = catalog_products[1]  # Гантели
        out_of_stock.count = 0
        out_of_stock.save()

        response = api_client.get(self.url, {"filter": '{"available": true}'})
        titles = [item["name"] for item in response.data["items"]]
        assert "Гантели 5 кг" not in titles
        assert len(titles) == 2

    def test_category_filter(self, api_client, catalog_products):
        """Фильтр по категории"""
        # Категория "Спорт" (гантели)
        sports_category = catalog_products[1].category  # Гантели имеют категорию "Спорт"
        response = api_client.get(self.url, {"category": sports_category.id})
        titles = [item["name"] for item in response.data["items"]]
        assert titles == ["Гантели 5 кг"]

        # Категория "Одежда" (бельё)
        clothes_category = catalog_products[0].category
        response = api_client.get(self.url, {"category": clothes_category.id})
        titles = [item["name"] for item in response.data["items"]]
        assert titles == ["Нижнее белье Романтика"]

    def test_tags_filter(self, api_client, catalog_products):
        """Фильтр по тегам"""
        romantic_tag = catalog_products[0].tags.first()
        response = api_client.get(self.url, {"tags[]": romantic_tag.id})
        titles = [item["name"] for item in response.data["items"]]
        assert titles == ["Нижнее белье Романтика"]

        tablet_tag = catalog_products[2].tags.first()
        response = api_client.get(self.url, {"tags[]": tablet_tag.id})
        titles = [item["name"] for item in response.data["items"]]
        assert titles == ["Планшет Samsung"]

        # Несколько тегов: романтика или утяжеление – оба товара имеют хотя бы один
        weight_tag = catalog_products[1].tags.first()
        response = api_client.get(self.url, {"tags[]": [romantic_tag.id, weight_tag.id]})
        titles = [item["name"] for item in response.data["items"]]
        # Ожидаем оба товара (бельё и гантели), порядок может быть разным
        assert set(titles) == {"Нижнее белье Романтика", "Гантели 5 кг"}


@pytest.mark.django_db
class TestCatalogUtils:
    """Тесты для вспомогательных функций каталога"""

    def test_extract_filters_from_json(self):
        factory = APIRequestFactory()
        django_request = factory.get("/", {"filter": json.dumps({"name": "тест", "minPrice": 100})})
        drf_request = DRFRequest(django_request)
        filters = extract_filters(drf_request)
        assert filters == {"name": "тест", "minPrice": 100}

    def test_extract_filters_from_nested_keys(self):
        factory = APIRequestFactory()
        django_request = factory.get(
            "/", {"filter[name]": "тест", "filter[minPrice]": "100", "filter[maxPrice]": "500"}
        )
        drf_request = DRFRequest(django_request)
        filters = extract_filters(drf_request)
        assert filters == {"name": "тест", "minPrice": "100", "maxPrice": "500"}

    def test_extract_filters_both_sources(self):
        factory = APIRequestFactory()
        django_request = factory.get(
            "/",
            {
                "filter": json.dumps({"name": "из_json"}),
                "filter[minPrice]": "50",
                "filter[available]": "true",
            },
        )
        drf_request = DRFRequest(django_request)
        filters = extract_filters(drf_request)
        assert filters == {"name": "из_json", "minPrice": "50", "available": "true"}

    def test_extract_filters_invalid_json_ignored(self):
        factory = APIRequestFactory()
        django_request = factory.get("/", {"filter": "{invalid}"})
        drf_request = DRFRequest(django_request)
        filters = extract_filters(drf_request)
        assert filters == {}

    def test_apply_search_filter(self, catalog_products):
        queryset = Product.objects.all()
        result = apply_search_filter(queryset, "Гантели")
        assert result.count() == 1
        assert result.first().title == "Гантели 5 кг"

        result = apply_search_filter(queryset, "Гантел")
        assert result.count() == 1
        assert result.first().title == "Гантели 5 кг"

        result = apply_search_filter(queryset, "антели")
        assert result.count() == 1
        assert result.first().title == "Гантели 5 кг"

        result = apply_search_filter(queryset, "Нижнее белье")
        assert result.count() == 1
        assert result.first().title == "Нижнее белье Романтика"

        result = apply_search_filter(queryset, "хромированным")
        assert result.count() == 1
        assert result.first().title == "Гантели 5 кг"

        result = apply_search_filter(queryset, "")
        assert result.count() == 3

    def test_apply_price_filter(self, catalog_products):
        queryset = Product.objects.all()
        result = apply_price_filter(queryset, min_price=2000, max_price=None)
        assert set(result.values_list("title", flat=True)) == {"Гантели 5 кг", "Планшет Samsung"}

        result = apply_price_filter(queryset, min_price=None, max_price=2000)
        assert set(result.values_list("title", flat=True)) == {"Нижнее белье Романтика", "Гантели 5 кг"}

        result = apply_price_filter(queryset, min_price=1500, max_price=2500)
        assert set(result.values_list("title", flat=True)) == {"Нижнее белье Романтика", "Гантели 5 кг"}

    @pytest.mark.parametrize(
        "input_value, expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("false", False),
            ("False", False),
            (True, True),
            (False, False),
            (1, True),
            (0, False),
            (None, False),
            ("", False),
            ("abc", False),
        ],
    )
    def test_to_bool(self, input_value, expected):
        assert to_bool(input_value) == expected

    def test_get_pagination_params_defaults(self):
        factory = APIRequestFactory()
        django_request = factory.get("/")
        drf_request = DRFRequest(django_request)
        limit, page = get_pagination_params(drf_request)
        assert limit == 20
        assert page == 1

    def test_get_pagination_params_custom(self):
        factory = APIRequestFactory()
        django_request = factory.get("/", {"limit": "50", "currentPage": "3"})
        drf_request = DRFRequest(django_request)
        limit, page = get_pagination_params(drf_request)
        assert limit == 50
        assert page == 3

    def test_get_pagination_params_limits(self):
        factory = APIRequestFactory()
        django_request = factory.get("/", {"limit": "200", "currentPage": "0"})
        drf_request = DRFRequest(django_request)
        limit, page = get_pagination_params(drf_request)
        assert limit == 100
        assert page == 1

    def test_get_pagination_params_invalid_values(self):
        factory = APIRequestFactory()
        django_request = factory.get("/", {"limit": "abc", "currentPage": "xyz"})
        drf_request = DRFRequest(django_request)
        limit, page = get_pagination_params(drf_request)
        assert limit == 20
        assert page == 1
