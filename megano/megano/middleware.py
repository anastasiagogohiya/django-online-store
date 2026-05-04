import logging
import time
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class ResponseTimeMiddleware(MiddlewareMixin):
    """Измерение времени ответа для мониторинга производительности"""
    def process_request(self, request):
        request.start_time = time.time()
        return None

    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            elapsed = time.time() - request.start_time
            if elapsed > 0.3:  # поставкила 0. сек
                logger.warning(f"Медленный запрос: {request.method} {request.path} - {elapsed:.2f} сек")
        return response