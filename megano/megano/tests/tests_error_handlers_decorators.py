from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError

from megano.decorators import catch_all_errors
from megano.error_handlers import (
    handle_bad_request,
    handle_exception,
    handle_not_found_error,
    handle_validation_error,
)


class TestValidationErrorHandler:
    def test_handle_validation_error_with_message_dict(self):
        """Исключение имеет message_dict → возвращается словарь ошибок"""

        class FakeException(Exception):
            message_dict = {"field": ["This field is required"]}

        exc = FakeException()
        response = handle_validation_error(exc)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == 400
        assert response.data["error_type"] == "ValidationError"
        assert response.data["error"] == exc.message_dict

    def test_handle_validation_error_with_message(self):
        """Исключение имеет атрибут message → используется message"""

        class FakeException(Exception):
            message = "Invalid data"

        exc = FakeException()
        response = handle_validation_error(exc)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Invalid data"

    def test_handle_validation_error_with_str(self):
        """Обычное исключение без message_dict и message → str(exception)"""
        exc = ValueError("Something went wrong")
        response = handle_validation_error(exc)
        assert response.data["error"] == "Something went wrong"

    def test_handle_validation_error_custom_message(self):
        """custom_message переопределяет сообщение об ошибке"""
        exc = ValueError("Original")
        response = handle_validation_error(exc, custom_message="Custom error")
        assert response.data["error"] == "Custom error"

    def test_handle_validation_error_logging(self, caplog):
        """Проверка логирования ошибки"""
        caplog.set_level("ERROR")
        exc = ValueError("Test log")
        handle_validation_error(exc)
        assert "ValidationError (400): Test log" in caplog.text


class TestExceptionHandler:
    def test_handle_exception_general(self, caplog):
        """Общее исключение → 500, сообщение по умолчанию"""
        exc = RuntimeError("DB connection lost")
        response = handle_exception(exc)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["status"] == 500
        assert response.data["error_type"] == "RuntimeError"
        assert response.data["error"] == "Внутренняя ошибка сервера"

    def test_handle_exception_custom_user_message(self):
        """Пользовательское сообщение для клиента"""
        exc = KeyError("missing")
        response = handle_exception(exc, user_message="Что-то пошло не так")
        assert response.data["error"] == "Что-то пошло не так"

    def test_handle_exception_logging(self, caplog):
        """Логирование с exc_info=True"""
        caplog.set_level("ERROR")
        exc = ZeroDivisionError("division by zero")
        handle_exception(exc)
        assert "Exception (500) ZeroDivisionError: division by zero" in caplog.text
        # Проверяем, что traceback записан (exc_info=True) — достаточно наличия записи уровня ERROR


class TestNotFoundErrorHandler:
    def test_handle_not_found_error_default(self, caplog):
        """404 с сообщением по умолчанию"""
        response = handle_not_found_error()
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["status"] == 404
        assert response.data["error_type"] == "NotFoundError"
        assert response.data["error"] == "Объект не найден"

    def test_handle_not_found_error_custom_message(self):
        response = handle_not_found_error(message="Пользователь не существует")
        assert response.data["error"] == "Пользователь не существует"

    def test_handle_not_found_error_logging(self, caplog):
        caplog.set_level("WARNING")
        handle_not_found_error("404 test")
        assert "NotFound (404): 404 test" in caplog.text


class TestBadRequestHandler:
    def test_handle_bad_request_default(self, caplog):
        """400 без дополнительных деталей"""
        response = handle_bad_request()
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == 400
        assert response.data["error_type"] == "BadRequest"
        assert response.data["error"] == "Некорректный запрос"
        assert "details" not in response.data

    def test_handle_bad_request_with_details(self):
        """400 с деталями ошибки"""
        details = {"email": "invalid format"}
        response = handle_bad_request(message="Ошибка валидации", errors_details=details)
        assert response.data["error"] == "Ошибка валидации"
        assert response.data["details"] == details

    def test_handle_bad_request_logging(self, caplog):
        caplog.set_level("WARNING")
        handle_bad_request("Bad request test")
        assert "BadRequest (400): Bad request test" in caplog.text


class TestCatchAllErrorsDecorator:
    """Тесты для декоратора catch_all_errors"""

    def create_view_function(self, side_effect=None, return_value=None):
        """Создает тестовую view-функцию с возможностью поднять исключение или вернуть значение"""

        class MockView:
            @catch_all_errors
            def test_method(self, request, *args, **kwargs):
                if side_effect:
                    raise side_effect
                return return_value or {"result": "ok"}

        return MockView().test_method

    def test_successful_call(self):
        """Успешный вызов без ошибок"""
        view_func = self.create_view_function(return_value={"data": "test"})
        mock_request = Mock()
        response = view_func(mock_request)
        assert response == {"data": "test"}

    def test_validation_error_from_django(self):
        """ValidationError (django) → handle_validation_error"""
        view_func = self.create_view_function(side_effect=ValidationError("Invalid field"))
        mock_request = Mock()
        with patch("megano.decorators.handle_validation_error") as mock_handler:
            mock_handler.return_value = Mock(status=400)
            view_func(mock_request)
            mock_handler.assert_called_once()
            args, _ = mock_handler.call_args
            assert isinstance(args[0], ValidationError)

    def test_validation_error_from_drf(self):
        """DRFValidationError → handle_validation_error"""
        view_func = self.create_view_function(side_effect=DRFValidationError({"field": "error"}))
        mock_request = Mock()
        with patch("megano.decorators.handle_validation_error") as mock_handler:
            mock_handler.return_value = Mock(status=400)
            view_func(mock_request)
            mock_handler.assert_called_once()
            assert isinstance(mock_handler.call_args[0][0], DRFValidationError)

    def test_permission_denied(self):
        """PermissionDenied → handle_permission_error"""
        view_func = self.create_view_function(side_effect=PermissionDenied("No access"))
        mock_request = Mock()
        with patch("megano.decorators.handle_permission_error") as mock_handler:
            mock_handler.return_value = Mock(status=403)
            view_func(mock_request)
            mock_handler.assert_called_once_with()  # без аргументов

    def test_http404_raises_through(self):
        """Http404 не перехватывается, пробрасывается дальше"""
        view_func = self.create_view_function(side_effect=Http404("Not found"))
        mock_request = Mock()
        with pytest.raises(Http404):
            view_func(mock_request)

    def test_object_does_not_exist(self):
        """ObjectDoesNotExist → handle_not_found_error с сообщением"""
        view_func = self.create_view_function(side_effect=ObjectDoesNotExist("User not found"))
        mock_request = Mock()
        with patch("megano.decorators.handle_not_found_error") as mock_handler:
            mock_handler.return_value = Mock(status=404)
            view_func(mock_request)
            mock_handler.assert_called_once_with(message="User not found")

    def test_key_error(self):
        """KeyError → handle_bad_request с сообщением о поле"""
        view_func = self.create_view_function(side_effect=KeyError("email"))
        mock_request = Mock()
        with patch("megano.decorators.handle_bad_request") as mock_handler:
            mock_handler.return_value = Mock(status=400)
            view_func(mock_request)
            mock_handler.assert_called_once_with(message="Отсутствует обязательное поле: 'email'")

    def test_any_other_exception(self):
        """Любое другое исключение → handle_exception"""
        view_func = self.create_view_function(side_effect=RuntimeError("DB crash"))
        mock_request = Mock()
        with patch("megano.decorators.handle_exception") as mock_handler:
            mock_handler.return_value = Mock(status=500)
            view_func(mock_request)
            mock_handler.assert_called_once()
            assert isinstance(mock_handler.call_args[0][0], RuntimeError)

    def test_logging_on_permission_denied(self, caplog):
        caplog.set_level("WARNING")
        view_func = self.create_view_function(side_effect=PermissionDenied())
        mock_request = Mock()
        with patch("megano.decorators.handle_permission_error") as mock_handler:
            mock_handler.return_value = Mock()
            view_func(mock_request)
        assert "PermissionDenied (403) in test_method:" in caplog.text

    def test_logging_on_object_does_not_exist(self, caplog):
        caplog.set_level("WARNING")
        view_func = self.create_view_function(side_effect=ObjectDoesNotExist("Missing"))
        mock_request = Mock()
        with patch("megano.decorators.handle_not_found_error") as mock_handler:
            mock_handler.return_value = Mock()
            view_func(mock_request)
        assert "ObjectDoesNotExist (404) in test_method: Missing" in caplog.text

    def test_logging_on_key_error(self, caplog):
        caplog.set_level("WARNING")
        view_func = self.create_view_function(side_effect=KeyError("username"))
        mock_request = Mock()
        with patch("megano.decorators.handle_bad_request") as mock_handler:
            mock_handler.return_value = Mock()
            view_func(mock_request)
        assert "KeyError (400) in test_method: 'username'" in caplog.text
