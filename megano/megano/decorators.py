# megano/decorators.py
import logging
from functools import wraps

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.http import Http404
from rest_framework.exceptions import ValidationError as DRFValidationError

from .error_handlers import (
    handle_bad_request,
    handle_exception,
    handle_not_found_error,
    handle_permission_error,
    handle_validation_error,
)

logger = logging.getLogger(__name__)


def catch_all_errors(func):
    """
    Универсальный декоратор для отлова всех типов ошибок.
    Возвращает ответ с полями: status, error_type, error
    """

    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        try:
            return func(self, request, *args, **kwargs)

        except (ValidationError, DRFValidationError) as e:
            logger.error(f"ValidationError or DRFValidationError (400) in {func.__name__}: {e}")
            return handle_validation_error(e)

        except PermissionDenied as permission_error:
            logger.warning(f"PermissionDenied (403) in {func.__name__}: {permission_error}")
            return handle_permission_error()

        except Http404:
            logger.warning(f"404 Error in {func.__name__}")
            raise

        except ObjectDoesNotExist as not_found_error:
            logger.warning(f"ObjectDoesNotExist (404) in {func.__name__}: {not_found_error}")
            return handle_not_found_error(message=str(not_found_error))

        except KeyError as key_error:
            logger.warning(f"KeyError (400) in {func.__name__}: {key_error}")
            return handle_bad_request(message=f"Отсутствует обязательное поле: {key_error}")

        except Exception as unexpected_error:
            error_type = type(unexpected_error).__name__
            logger.error(f"{error_type} (500) in {func.__name__}: {unexpected_error}", exc_info=True)
            return handle_exception(unexpected_error)

    return wrapper
