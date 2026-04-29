# megano/api/urls.py
from django.urls import path
from app_users.profile_views import ProfileView, ProfilePasswordView, ProfileAvatarUploadView
from app_users.auth_views import SignInView, SignUpView, SignOutView
from catalog.views.categories_views import CategoriesView
from catalog.views.catalog_views import CatalogView
from catalog.views.popular_views import ProductsPopularView
from catalog.views.limited_views import ProductsLimitedView
from catalog.views.sales_views import SalesView
from catalog.views.tags_views import TagsView
from catalog.views.banners_views import BannersView
from catalog.views.product_views import ProductView
from catalog.views.review_create_views import ReviewCreateView
from basket.views import BasketView
from order.views import OrderView, OrderDetailView
from payment.views import PaymentView

# Нужно ли выносить эти пути по папкам проекта?

urlpatterns = [
    # auth
    path('sign-in/', SignInView.as_view(), name='sign-in'),
    path('sign-up/', SignUpView.as_view(), name='sign-up'),
    path('sign-out/', SignOutView.as_view(), name='sign-out'),

    # profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/password/', ProfilePasswordView.as_view(), name='change-password'),
    path('profile/avatar/', ProfileAvatarUploadView.as_view(), name='change-avatar'),

    # catalog
    path('categories/', CategoriesView.as_view(), name='categories'),
    path('catalog/', CatalogView.as_view(), name='catalog-swagger'), # в фронтэде без слэша на конце когда нужна например фильтрация по тэгам
    path('products/popular/', ProductsPopularView.as_view(), name='products-popular'),
    path('products/limited/', ProductsLimitedView.as_view(), name='products-limited'),
    path('sales/', SalesView.as_view(), name='sales'),
    path('banners/', BannersView.as_view(), name='banners'),

    # tags
    path('tags/', TagsView.as_view(), name='tags'),

    # product
    path('product/<int:id>/', ProductView.as_view(), name='product_id'),
    path('product/<int:id>/reviews', ReviewCreateView.as_view(), name='product_reviews_create'),

    # basket
    path('basket/', BasketView.as_view(), name='basket'),

    # order
    path('orders/', OrderView.as_view(), name='orders'),
    path('order/<int:id>/', OrderDetailView.as_view(), name='order_detail'),
    path('order/<int:id>', OrderDetailView.as_view(), name='order_detail'),

    path('payment/<int:id>/', PaymentView.as_view(), name='payment'),
]
