import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from catalog.serializers.catalog_serializers import CatalogSerializer, CategorySerializer
from catalog.serializers.tag_serializers import TagSerializer


# ---------------------- Тесты CategorySerializer ----------------------
class TestCategorySerializer:
    def test_category_without_image(self, parent_category):
        serializer = CategorySerializer(parent_category)
        data = serializer.data
        assert data["id"] == parent_category.id
        assert data["title"] == "Электроника"
        assert data["image"] == {"src": "", "alt": "Электроника"}
        assert "subcategories" not in data

    def test_category_with_image(self, parent_category):
        parent_category.image = SimpleUploadedFile("cat.jpg", b"content", content_type="image/jpeg")
        parent_category.save()
        serializer = CategorySerializer(parent_category)
        data = serializer.data
        assert data["image"]["src"].startswith("/media/")
        assert data["image"]["alt"] == "Электроника"

    def test_category_with_subcategories(self, parent_category, child_category):
        serializer = CategorySerializer(parent_category)
        data = serializer.data
        assert "subcategories" in data
        assert len(data["subcategories"]) == 1
        sub = data["subcategories"][0]
        assert sub["id"] == child_category.id
        assert sub["title"] == "Смартфоны"
        assert sub["image"] == {"src": "", "alt": "Смартфоны"}
        assert "subcategories" not in sub

    def test_category_does_not_show_subcategories_if_empty(self, parent_category):
        serializer = CategorySerializer(parent_category)
        assert "subcategories" not in serializer.data


# ---------------------- Тесты CatalogSerializer с параметризацией ----------------------
class TestCatalogSerializer:
    # Параметризация: (фикстура, ожидаемое имя, free_delivery, ожидаемое кол-во изображений,
    # ожидаемое кол-во тегов, rating, reviews)
    @pytest.mark.parametrize(
        "product_fixture, expected_name, free_delivery, images_count, tags_count, rating, reviews",
        [
            ("product_without_image", "iPhone 15", True, 1, 0, "0.00", 0),
            ("product_with_image", "Samsung Galaxy", False, 1, 0, "0.00", 0),
            ("product_with_tags", "Xiaomi Mi 11", True, 0, 2, "4.70", 42),
        ],
    )
    def test_catalog_serializer_fields(
        self, request, product_fixture, expected_name, free_delivery, images_count, tags_count, rating, reviews
    ):
        product = request.getfixturevalue(product_fixture)
        serializer = CatalogSerializer(product)
        data = serializer.data

        assert data["id"] == product.id
        assert data["name"] == expected_name
        assert data["freeDelivery"] == free_delivery
        assert data["rating"] == rating
        assert data["reviews"] == reviews
        assert len(data["tags"]) == tags_count

        # Проверка псевдоизображения для продуктов без реального изображения
        if images_count == 1 and product_fixture == "product_without_image":
            assert data["images"][0]["src"] == "https://noimage/"
            assert data["images"][0]["alt"] == expected_name

    def test_all_fields_present(self, product_without_image):
        serializer = CatalogSerializer(product_without_image)
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
        assert set(serializer.data.keys()) == expected_fields

    def test_product_with_tags_serialization(self, product_with_tags):
        """Дополнительная проверка точного совпадения тегов (через TagSerializer)"""
        serializer = CatalogSerializer(product_with_tags)
        data = serializer.data
        expected_tags = TagSerializer(product_with_tags.tags.all(), many=True).data
        assert data["tags"] == expected_tags
