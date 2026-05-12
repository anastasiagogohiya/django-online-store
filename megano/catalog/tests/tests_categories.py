import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from catalog.models import Category


class TestCategoryView:
    url = reverse("categories")

    @pytest.fixture
    def category_tree(self, db):
        root = Category.objects.create(title="Электроника", slug="electronics", ordering_index=1)
        sub = Category.objects.create(title="Смартфоны", slug="smartphones", parent=root, ordering_index=2)
        alone = Category.objects.create(title="Книги", slug="books", ordering_index=3)
        return {"root": root, "sub": sub, "alone": alone}

    def test_category_view_returns_only_root_categories(self, api_client, category_tree):
        response = api_client.get(self.url)
        assert response.status_code == 200
        data = response.data
        assert len(data) == 2
        titles = [item["title"] for item in data]
        assert "Электроника" in titles
        assert "Книги" in titles
        assert "Смартфоны" not in titles  # подкатегория не должна быть корнем

    def test_category_view_includes_subcategories(self, api_client, category_tree):
        response = api_client.get(self.url)
        data = response.data
        electronics = next(item for item in data if item["title"] == "Электроника")
        assert "subcategories" in electronics
        assert len(electronics["subcategories"]) == 1
        assert electronics["subcategories"][0]["title"] == "Смартфоны"
        # У подкатегории не должно быть поля subcategories
        assert "subcategories" not in electronics["subcategories"][0]

    def test_category_view_empty_subcategories_omitted(self, api_client, category_tree):
        response = api_client.get(self.url)
        data = response.data
        books = next(item for item in data if item["title"] == "Книги")
        assert "subcategories" not in books

    def test_category_view_returns_image_object(self, api_client, category_tree):
        response = api_client.get(self.url)
        data = response.data
        for category in data:
            assert "image" in category
            assert "src" in category["image"]
            assert "alt" in category["image"]


class TestCategoryModel:
    def test_create_root_category_ok(self, db):
        """Корневая категория (без parent) создаётся без ошибок"""
        root = Category(title="Корень", slug="root")
        root.full_clean()  # вызов clean() внутри
        # не должно быть исключения
        root.save()
        assert Category.objects.filter(title="Корень").exists()

    def test_create_subcategory_ok(self, db):
        """Подкатегория (parent – корневая) может быть"""
        root = Category.objects.create(title="Родитель", slug="parent")
        sub = Category(title="Подкатегория", slug="sub", parent=root)
        # валидация проходит
        sub.full_clean()
        sub.save()
        assert Category.objects.filter(title="Подкатегория").exists()

    def test_create_subsubcategory_forbidden(self, db):
        """Создание подкатегории у подкатегории должно вызывать ValidationError"""
        root = Category.objects.create(title="Родитель", slug="parent")
        sub = Category.objects.create(title="Подкатегория", slug="sub", parent=root)
        subsub = Category(title="Под-подкатегория", slug="subsub", parent=sub)
        with pytest.raises(ValidationError) as exc:
            subsub.full_clean()
        # Проверяем сообщение об ошибке
        error_messages = exc.value.message_dict.get("__all__", [])
        assert any("Максимальная глубина вложенности" in msg for msg in error_messages)

    def test_save_calls_clean(self, db):
        """Проверяем, что метод save вызывает валидацию"""
        root = Category.objects.create(title="Родитель", slug="parent")
        sub = Category.objects.create(title="Подкатегория", slug="sub", parent=root)
        subsub = Category(title="Под-подкатегория", slug="subsub", parent=sub)
        with pytest.raises(ValidationError):
            subsub.save()  # save() вызывает full_clean(), который вызовет clean()
