# megano/error_handlers.py Общий обработчик ошибок для всех приложений
import logging

from rest_framework import status
from rest_framework.response import Response

error_logger = logging.getLogger(__name__)


def handle_validation_error(exception, custom_message=None):
    """
    Обрабатывает ValidationError → 400
    """
    if hasattr(exception, "message_dict"):
        error_message = exception.message_dict
    elif hasattr(exception, "message"):
        error_message = exception.message
    else:
        error_message = str(exception)

    if custom_message:
        error_message = custom_message

    error_logger.error(f"ValidationError (400): {error_message}")

    return Response(
        {"status": 400, "error_type": "ValidationError", "error": error_message}, status=status.HTTP_400_BAD_REQUEST
    )


def handle_exception(exception, user_message="Внутренняя ошибка сервера"):
    """
    Обрабатывает общие исключения → 500
    """
    error_type = type(exception).__name__

    error_logger.error(f"Exception (500) {error_type}: {str(exception)}", exc_info=True)

    return Response(
        {
            "status": 500,
            "error_type": error_type,
            "error": user_message,
            "detail": str(exception) if error_logger.level <= logging.DEBUG else None,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def handle_permission_error(message="Нет прав доступа"):
    """
    Обрабатывает PermissionDenied → 403
    """
    error_logger.warning(f"PermissionDenied (403): {message}")

    return Response(
        {"status": 403, "error_type": "PermissionDenied", "error": message}, status=status.HTTP_403_FORBIDDEN
    )


def handle_not_found_error(message="Объект не найден"):
    """
    Обрабатывает 404 ошибку
    """
    error_logger.warning(f"NotFound (404): {message}")

    return Response({"status": 404, "error_type": "NotFoundError", "error": message}, status=status.HTTP_404_NOT_FOUND)


def handle_bad_request(message="Некорректный запрос", errors_details=None):
    """
    Обрабатывает ошибку 400
    """
    error_logger.warning(f"BadRequest (400): {message}")

    response_data = {"status": 400, "error_type": "BadRequest", "error": message}
    if errors_details:
        response_data["details"] = errors_details

    return Response(response_data, status=status.HTTP_400_BAD_REQUEST)
