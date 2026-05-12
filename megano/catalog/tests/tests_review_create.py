import pytest
from django.core.cache import cache
from django.http import HttpRequest
from django.urls import reverse
from rest_framework.request import Request

from catalog.models import Review
from catalog.serializers.review_serializers import ReviewCreateSerializer, ReviewGetSerializer, ReviewSerializer


@pytest.fixture
def existing_review(user_client, profile, product):
    """Фикстура, создающая отзыв и возвращающая его"""
    url = reverse("product_reviews_create", args=[product.id])
    payload = {"text": "Отличный товар", "rate": 5}
    user_client.post(url, payload)
    return Review.objects.get(product=product, author=profile)


# ---------------------- Тесты для ReviewCreateView ----------------------
class TestReviewCreateView:
    url_name_reviews = "product_reviews_create"

    def setup_method(self):
        cache.clear()

    @classmethod
    def get_url(cls, product_id):
        return reverse(cls.url_name_reviews, args=[product_id])

    def test_get_reviews_after_create(self, existing_review, user_client, product):
        response = user_client.get(self.get_url(product.id))
        assert response.status_code == 200
        assert len(response.data) == 1
        review_data = response.data[0]
        assert review_data["text"] == "Отличный товар"
        assert review_data["rate"] == 5
        assert "author" in review_data

    def test_create_review_success(self, user_client, profile, product):
        url = self.get_url(product.id)
        payload = {"text": "Отличный товар!", "rate": 5}
        response = user_client.post(url, payload)
        assert response.status_code == 200
        data = response.data
        assert data["text"] == "Отличный товар!"
        assert data["rate"] == 5
        review = Review.objects.get(product=product, author=profile)
        assert review.text == "Отличный товар!"
        assert review.rate == 5

    def test_create_review_unauthenticated(self, api_client, product):
        response = api_client.post(self.get_url(product.id), {"text": "Хороший товар", "rate": 4})
        assert response.status_code == 401  # пользователь неавторизован

    def test_create_review_invalid_rate(self, user_client, product):
        response = user_client.post(self.get_url(product.id), {"text": "Плохой товар", "rate": 6})
        assert response.status_code == 400
        assert "error" in response.data

    def test_create_review_missing_text(self, user_client, product):
        response = user_client.post(self.get_url(product.id), {"rate": 5})
        assert response.status_code == 400
        assert "details" in response.data
        assert "text" in response.data["details"]

    def test_create_review_nonexistent_product(self, user_client):
        response = user_client.post(self.get_url(99999), {"text": "Нет товара", "rate": 3})
        assert response.status_code == 404


# ---------------------- Тесты для сериализаторов ----------------------
class TestReviewSerializers:
    @pytest.fixture
    def mock_request(self, user):
        return Request(HttpRequest())
        # Устанавливаем user для request
        self_req = Request(HttpRequest())
        self_req.user = user
        return self_req

    def test_review_create_serializer_missing_text(self, product, mock_request):
        serializer = ReviewCreateSerializer(data={"rate": 5}, context={"request": mock_request, "product": product})
        assert not serializer.is_valid()
        assert "text" in serializer.errors

    def test_review_get_serializer_fields(self, existing_review):
        serializer = ReviewGetSerializer(existing_review)
        data = serializer.data
        assert "author" in data
        assert "email" in data
        assert "text" in data
        assert "rate" in data
        assert "date" in data
        assert data["author"] == existing_review.author.user.username
        assert isinstance(data["email"], str)

    def test_review_serializer(self, product, profile):
        review = Review.objects.create(product=product, author=profile, text="Прямое создание", rate=3)
        serializer = ReviewSerializer(review)
        data = serializer.data
        assert data["text"] == "Прямое создание"
        assert data["rate"] == 3
        assert "date" in data
