from django.urls import path
from app_users.profile_views import ProfileView, ProfilePasswordView, ProfileAvatarUploadView
from app_users.auth_views import SignInView, SignUpView, SignOutView


urlpatterns = [
    # auth
    path('sign-in/', SignInView.as_view(), name='sign-in'),
    path('sign-up/', SignUpView.as_view(), name='sign-up'),
    path('sign-out/', SignOutView.as_view(), name='sign-out'),

    # profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/password/', ProfilePasswordView.as_view(), name='change-password'),
    path('profile/avatar/', ProfileAvatarUploadView.as_view(), name='change-avatar'),
]
