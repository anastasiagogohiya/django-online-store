from django.urls import path
from .views import SignInView, SignUpView, SignOutView

urlpatterns = [
    path('sign-in/', SignInView.as_view(), name='sign-in'),
    path('sign-up/', SignUpView.as_view(), name='sign-up'),
    path('sign-out/', SignOutView.as_view(), name='sign-out'),
    #path('banners/', views.banners),
    #path('categories/', views.categories),
    #path('catalog/', views.catalog),
    #path('products/popular/', views.productsPopular),
    #path('products/limited/', views.productsLimited),
    #path('sales/', views.sales),
    #path('basket/', views.basket),
    #path('orders/', views.orders),
    #path('product/<int:id>/', views.product),
    #path('product/<int:id>/reviews/', views.productReviews),
    #path('tags/', views.tags),
    #path('profile/', views.profile),
    #path('profile/password/', views.profilePassword),
    #path('profile/avatar/', views.avatar),
    #path('order/<int:id>/', views.order),
    #path('payment/<int:id>/', views.payment),
]
