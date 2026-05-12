"""Так как двойная авторизация то
Пропускаем CSRF проверку для запросов, даже если есть сессия - только для SWAGGER"""

from django.utils.deprecation import MiddlewareMixin


class CSRFExemptForTokenAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith("/api/"):
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if auth_header.startswith("Token "):
                setattr(request, "_dont_enforce_csrf_checks", True)
