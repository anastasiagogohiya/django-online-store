from django.urls import path
from app_users.profile_views import ProfileView, ProfilePasswordView, ProfileAvatarUploadView
from app_users.auth_views import SignInView, SignUpView, SignOutView
from catalog.catalog_views import CategoriesView


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

    #path('banners/', views.banners),
    #path('catalog/', views.catalog),
    #path('products/popular/', views.productsPopular),
    #path('products/limited/', views.productsLimited),
    #path('sales/', views.sales),
    #path('basket/', views.basket),
    #path('orders/', views.orders),
    #path('product/<int:id>/', views.product),
    #path('product/<int:id>/reviews/', views.productReviews),
    #path('tags/', views.tags),
    #path('order/<int:id>/', views.order),
    #path('payment/<int:id>/', views.payment),
]
