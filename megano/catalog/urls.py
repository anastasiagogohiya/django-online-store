# megano/api/urls.py
from django.urls import path
from catalog.views.categories_views import CategoriesView
from catalog.views.catalog_views import CatalogView
from catalog.views.popular_views import ProductsPopularView
from catalog.views.limited_views import ProductsLimitedView
from catalog.views.sales_views import SalesView
from catalog.views.tags_views import TagsView
from catalog.views.banners_views import BannersView
from catalog.views.product_views import ProductView
from catalog.views.review_create_views import ReviewCreateView



urlpatterns = [
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

]
