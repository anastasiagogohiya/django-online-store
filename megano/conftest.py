from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from app_users.models import Profile
from basket.models import Basket, BasketItem
from catalog.models import Category, Product, ProductImage, Tag


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_data():
    """Данные для регистрации"""
    return {"fullName": "Jennifer", "username": "jenn", "password": "jenn"}


@pytest.fixture
def create_user(db):
    """Фабрика для создания пользователей"""

    def _create_user(username, password, **kwargs):
        return User.objects.create_user(username=username, password=password, **kwargs)

    return _create_user


# ---------- Авторизованные клиенты ----------
class AuthClient:
    """Обёртка над APIClient, хранящая пользователя"""

    def __init__(self, client, user):
        self.client = client
        self.user = user

    def __getattr__(self, name):
        return getattr(self.client, name)


@pytest.fixture
def auth_jennifer(api_client, db):
    """Клиент, авторизованный как jenn"""
    user = User.objects.create_user(username="jenn", password="jenn")
    api_client.force_login(user)
    return AuthClient(api_client, user)


@pytest.fixture
def staff_client(db):
    """Клиент, авторизованный как staff-пользователь"""
    user = User.objects.create_user(username="admin", password="admin", is_staff=True)
    client = APIClient()
    client.force_login(user)
    return client


@pytest.fixture
def user(db):
    """Обычный пользователь testuser/testpass"""
    return User.objects.create_user(username="testuser", password="testpass")


@pytest.fixture
def profile(user):
    """Профиль для обычного пользователя"""
    profile, _ = Profile.objects.get_or_create(user=user, defaults={"full_name": "Test User", "phone": "123456789"})
    return profile


@pytest.fixture
def user_client(api_client, user):
    """Клиент, авторизованный как testuser"""
    api_client.force_login(user)
    return api_client


# Для совместимости с тестами, которые используют auth_client
@pytest.fixture
def auth_client(user_client):
    """Алиас для user_client"""
    return user_client


# ---------- Категории ----------
@pytest.fixture
def category(db):
    """Базовая категория (без родителя)"""
    return Category.objects.create(title="Тестовая категория", slug="test-cat")


@pytest.fixture
def parent_category(db):
    """Родительская категория (Электроника)"""
    return Category.objects.create(title="Электроника", slug="electronics", ordering_index=1, is_active=True)


@pytest.fixture
def child_category(parent_category):
    """Дочерняя категория (Смартфоны)"""
    return Category.objects.create(
        title="Смартфоны", slug="smartphones", parent=parent_category, ordering_index=2, is_active=True
    )


# ---------- Простые товары (без изображений, тегов) ----------
@pytest.fixture
def product(category):
    """Базовый активный товар"""
    return Product.objects.create(
        title="Тестовый товар",
        slug="test-product",
        category=category,
        price=Decimal("100.00"),
        count=10,
        is_active=True,
        description="Описание",
        full_description="Детали",
    )


@pytest.fixture
def base_product_expensive(category):
    """Товар с высокой ценой (1000) — используется в некоторых старых тестах"""
    return Product.objects.create(
        title="Тестовый товар дорогой",
        slug="test-product-expensive",
        category=category,
        price=Decimal("1000.00"),
        count=10,
        is_active=True,
        description="Описание",
        full_description="Полное описание",
    )


@pytest.fixture
def base_product(child_category):
    """Товар для иерархических тестов (без изображений)"""
    return Product.objects.create(
        title="Samsung Galaxy",
        slug="samsung-galaxy",
        category=child_category,
        price=Decimal("899.99"),
        count=5,
        free_delivery=False,
        description="Android смартфон",
        full_description="Подробное описание...",
    )


@pytest.fixture
def inactive_product(category):
    """Неактивный товар"""
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


# ---------- Товары с дополнительными данными (изображения, теги) ----------
@pytest.fixture
def active_product(category):
    """Активный товар с тегом и изображением"""
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
def product_with_image(base_product):
    """Товар с одним изображением"""
    image = ProductImage.objects.create(
        image=SimpleUploadedFile("test.jpg", b"content", content_type="image/jpeg"), alt="Samsung photo"
    )
    base_product.images.add(image)
    return base_product


@pytest.fixture
def product_without_image(child_category):
    """Товар без изображений, но с free_delivery=True и высокой ценой"""
    return Product.objects.create(
        title="iPhone 15",
        slug="iphone-15",
        category=child_category,
        price=Decimal("999.99"),
        count=10,
        free_delivery=True,
        description="Смартфон Apple",
        full_description="Детали...",
    )


@pytest.fixture
def product_with_tags(child_category):
    """Товар с двумя тегами (новинка, хит)"""
    tag1 = Tag.objects.create(name="новинка")
    tag2 = Tag.objects.create(name="хит")
    product = Product.objects.create(
        title="Xiaomi Mi 11",
        slug="xiaomi-mi11",
        category=child_category,
        price=Decimal("599.99"),
        count=20,
        free_delivery=True,
        description="Смартфон Xiaomi с отличной камерой",
        rating=Decimal("4.7"),
        reviews_count=42,
    )
    product.tags.set([tag1, tag2])
    return product


# ---------- Наборы товаров для тестов каталога ----------
@pytest.fixture
def catalog_products(db):
    """Три предопределённых товара (бельё, гантели, планшет)"""
    clothes_category = Category.objects.create(title="Одежда", slug="clothes")
    sports_category = Category.objects.create(title="Спорт", slug="sports")
    electronics_category = Category.objects.create(title="Электроника", slug="electronics")

    romantic_tag = Tag.objects.create(name="романтика")
    weight_tag = Tag.objects.create(name="утяжеление")
    tablet_tag = Tag.objects.create(name="планшет")

    product1 = Product.objects.create(
        title="Нижнее белье Романтика",
        slug="nizhnee-bele-romantika",
        category=clothes_category,
        price=1500.00,
        count=25,
        free_delivery=True,
        rating=4.7,
        reviews_count=15,
        purchase_count=120,
        ordering_index=10,
        description="Красивое нижнее белье из хлопка",
        full_description="Набор состоит из бюстгальтера и трусиков. Размеры: S, M, L.",
    )
    product1.tags.set([romantic_tag])

    product2 = Product.objects.create(
        title="Гантели 5 кг",
        slug="ganteli-5-kg",
        category=sports_category,
        price=2000.00,
        count=8,
        free_delivery=False,
        rating=4.9,
        reviews_count=42,
        purchase_count=300,
        ordering_index=5,
        description="Разборные гантели по 5 кг каждая",
        full_description="В комплекте две гантели. Материал: сталь с хромированным покрытием.",
    )
    product2.tags.set([weight_tag])

    product3 = Product.objects.create(
        title="Планшет Samsung",
        slug="planshet-samsung",
        category=electronics_category,
        price=25000.00,
        count=3,
        free_delivery=True,
        rating=4.5,
        reviews_count=89,
        purchase_count=210,
        ordering_index=15,
        description="Планшет Samsung Galaxy Tab",
        full_description="10.5 дюймов, 4 ГБ ОЗУ, 64 ГБ памяти.",
    )
    product3.tags.set([tablet_tag])

    return [product1, product2, product3]


@pytest.fixture
def limited_products(db):
    """5 товаров с is_limited=True"""
    cat = Category.objects.create(title="Техника", slug="tech")
    products = []
    for i in range(5):
        p = Product.objects.create(
            title=f"Limited Product {i}",
            slug=f"limited-{i}",
            category=cat,
            price=Decimal("1000") + Decimal(i * 100),
            count=10,
            free_delivery=True,
            is_limited=True,
            is_active=True,
            ordering_index=i,
            purchase_count=(5 - i) * 10,
            description=f"Описание Limited Product {i}",
        )
        products.append(p)
    return products


@pytest.fixture
def non_limited_products(db):
    """Один товар с is_limited=False"""
    cat = Category.objects.create(title="Обычные", slug="usual")
    p = Product.objects.create(
        title="Regular product",
        slug="regular",
        category=cat,
        price=500,
        count=5,
        is_limited=False,
        is_active=True,
        description="Обычный товар",
    )
    return [p]


@pytest.fixture
def inactive_limited_products(db):
    """Один товар is_limited=True, но is_active=False"""
    cat = Category.objects.create(title="Неактивные", slug="inactive")
    p = Product.objects.create(
        title="Inactive limited",
        slug="inactive-limited",
        category=cat,
        price=200,
        count=0,
        is_limited=True,
        is_active=False,
        description="Неактивный товар",
    )
    return [p]


@pytest.fixture
def popular_products(db):
    """10 товаров с разными ordering_index и purchase_count"""
    cat = Category.objects.create(title="Электроника", slug="electronics")
    products = []
    for i in range(10):
        p = Product.objects.create(
            title=f"Popular Product {i}",
            slug=f"popular-{i}",
            category=cat,
            price=Decimal("100") * (i + 1),
            count=10,
            free_delivery=True,
            is_active=True,
            ordering_index=9 - i,
            purchase_count=100 - i * 10,
            description=f"Описание популярного товара {i}",
        )
        products.append(p)
    return products


@pytest.fixture
def mixed_products(db):
    """Три товара с одинаковым ordering_index (5) и разным purchase_count"""
    cat = Category.objects.create(title="Одинаковые", slug="same")
    p1 = Product.objects.create(
        title="Product A",
        slug="prod-a",
        category=cat,
        price=100,
        count=5,
        is_active=True,
        ordering_index=5,
        purchase_count=30,
        description="A",
    )
    p2 = Product.objects.create(
        title="Product B",
        slug="prod-b",
        category=cat,
        price=200,
        count=3,
        is_active=True,
        ordering_index=5,
        purchase_count=50,
        description="B",
    )
    p3 = Product.objects.create(
        title="Product C",
        slug="prod-c",
        category=cat,
        price=150,
        count=7,
        is_active=True,
        ordering_index=5,
        purchase_count=20,
        description="C",
    )
    return [p1, p2, p3]


# ---------- Корзина ----------
@pytest.fixture
def basket(profile):
    """Пустая корзина для профиля"""
    return Basket.objects.create(profile=profile)


@pytest.fixture
def basket_with_items(basket, product):
    """Корзина с одним товаром (2 шт)"""
    BasketItem.objects.create(basket=basket, product=product, count=2)
    return basket
