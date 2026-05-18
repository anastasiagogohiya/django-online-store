import logging
import re
import time

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class ResponseTimeMiddleware(MiddlewareMixin):
    """Измерение времени ответа для мониторинга производительности"""

    def process_request(self, request):
        request.start_time = time.time()
        return None

    def process_response(self, request, response):
        if hasattr(request, "start_time"):
            elapsed = time.time() - request.start_time
            if elapsed > 0.3:  # поставкила 0. сек
                logger.warning(f"Медленный запрос: {request.method} {request.path} - {elapsed:.2f} сек")
        return response


class SecurityLoggingMiddleware:
    """Логирование подозрительных попыток"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # 1. Логируем 403 (доступ запрещён)
        if response.status_code == 403:
            logger.warning(
                f"Forbidden access: {request.method} {request.path} | "
                f"User: {request.user} | IP: {self.get_client_ip(request)}"
            )

        # 2. Логируем попытки доступа к админке без прав
        if request.path.startswith("/admin/") and not request.user.is_staff:
            logger.warning(f"Non-staff access to admin: {request.user} | IP: {self.get_client_ip(request)}")

        # 3. подозрительно длинный URL (> 200 символов)
        if len(request.get_full_path()) > 200:
            logger.warning(f"Suspicious long URL: {request.get_full_path()} | IP: {self.get_client_ip(request)}")

        # 4. Подозрительные символы (простые SQL-инъекции, XSS)
        suspicious_patterns = [r"union.*select", r"(%27)|(')|(--)", r"<script", r"javascript:"]
        for pattern in suspicious_patterns:
            if re.search(pattern, request.get_full_path(), re.IGNORECASE):
                logger.error(
                    f"Potential attack pattern '{pattern}' "
                    f"in URL: {request.get_full_path()} | "
                    f"IP: {self.get_client_ip(request)}"
                )
                break

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
