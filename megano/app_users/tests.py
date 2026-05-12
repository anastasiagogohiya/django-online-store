import base64
import logging
import os
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.authtoken.models import Token

from app_users.models import Avatar, Profile
from app_users.profile_serializers import AvatarUploadSerializer, ProfileSerializer
from app_users.utils import get_profile, parse_request_data

# 1x1 прозрачный PNG
VALID_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfF4SJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
VALID_PNG_CONTENT = base64.b64decode(VALID_PNG_BASE64)


# ---------------------- Тесты регистрации ----------------------
@pytest.mark.django_db
def test_sign_up_success(api_client, user_data):
    response = api_client.post(reverse("sign-up"), user_data, format="json")
    assert response.status_code == 200
    assert User.objects.filter(username=user_data["username"]).exists()
    assert Profile.objects.filter(full_name=user_data["fullName"]).exists()


@pytest.mark.django_db
def test_sign_up_failed_user_exists(api_client, user_data, create_user):
    create_user(username=user_data["username"], password=user_data["password"])
    response = api_client.post(reverse("sign-up"), user_data, format="json")
    assert response.status_code == 400


@pytest.mark.parametrize(
    "case_data, expected_status",
    [
        ({"username": "jenn", "password": "jenn", "fullName": ""}, 400),
        ({"username": "", "password": "jenn", "fullName": "Jennifer"}, 400),
        ({"username": "jenn", "password": "", "fullName": "Jennifer"}, 400),
    ],
)
@pytest.mark.django_db
def test_sign_up_failed(api_client, case_data, expected_status):
    response = api_client.post(reverse("sign-up"), case_data, format="json")
    assert response.status_code == expected_status


# ---------------------- Тесты входа/выхода ----------------------
@pytest.mark.django_db
def test_sign_in_success(api_client, user_data, create_user):
    create_user(username=user_data["username"], password=user_data["password"])
    payload = {"username": user_data["username"], "password": user_data["password"]}
    response = api_client.post(reverse("sign-in"), payload, format="json")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "case_data, expected_status",
    [
        ({"username": "jenno", "password": "jenn"}, 401),
        ({"username": "jenn", "password": "lala"}, 401),
    ],
)
@pytest.mark.django_db
def test_sign_in_failed(api_client, user_data, create_user, case_data, expected_status):
    create_user(username=user_data["username"], password=user_data["password"])
    response = api_client.post(reverse("sign-in"), case_data, format="json")
    assert response.status_code == expected_status


@pytest.mark.django_db
def test_sign_out_success(api_client, user_data, create_user):
    user = create_user(username=user_data["username"], password=user_data["password"])
    token = Token.objects.create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    response = api_client.post(reverse("sign-out"), format="json")
    assert response.status_code == 200
    assert not Token.objects.filter(user=user).exists()


# ---------------------- Тесты профиля ----------------------
@pytest.mark.django_db
def test_get_profile_success(auth_jennifer):
    response = auth_jennifer.get(reverse("profile"))
    assert response.status_code == 200
    profile = Profile.objects.get(user=auth_jennifer.user)
    assert response.json() == ProfileSerializer(profile).data


@pytest.mark.django_db
def test_post_profile_success(auth_jennifer):
    data = {"email": "jenn@gmail.com", "phone": "79999999999"}
    response = auth_jennifer.post(reverse("profile"), data=data)
    assert response.status_code == 200
    assert response.json()["email"] == "jenn@gmail.com"
    assert response.json()["phone"] == "79999999999"
    profile = Profile.objects.get(user=auth_jennifer.user)
    assert profile.phone == 79999999999
    assert profile.user.email == "jenn@gmail.com"


def test_post_profile_bad_request(auth_jennifer):
    data = {"email": "not_an_email", "phone": "abc"}
    response = auth_jennifer.post(reverse("profile"), data=data)
    assert response.status_code == 400
    assert response.json()["message"] == "Введите корректные данные."


@pytest.mark.django_db
def test_post_profile_phone_unique(auth_jennifer, create_user):
    other_user = create_user(username="other", password="pass")
    Profile.objects.filter(user=other_user).update(phone=1234567890)
    data = {"phone": "1234567890"}
    response = auth_jennifer.post(reverse("profile"), data=data)
    assert response.status_code == 400
    assert "phone" in response.json().get("errors", {})


@pytest.mark.django_db
def test_post_profile_update_own_phone_email(auth_jennifer):
    profile = Profile.objects.get(user=auth_jennifer.user)
    profile.phone = 1111111111
    profile.save()
    auth_jennifer.user.email = "same@example.com"
    auth_jennifer.user.save()
    data = {"phone": "1111111111", "email": "same@example.com"}
    response = auth_jennifer.post(reverse("profile"), data=data)
    assert response.status_code == 200


# ---------------------- Тесты смены пароля ----------------------
@pytest.mark.django_db
def test_change_password_success(auth_jennifer):
    data = {"currentPassword": "jenn", "newPassword": "newpass123"}
    response = auth_jennifer.post(reverse("change-password"), data=data)
    assert response.status_code == 200
    assert response.json()["message"] == "Вы успешно поменяли пароль"
    auth_jennifer.user.refresh_from_db()
    assert auth_jennifer.user.check_password("newpass123")


@pytest.mark.django_db
def test_change_password_wrong_current(auth_jennifer):
    data = {"currentPassword": "wrongpassword", "newPassword": "newpass123"}
    response = auth_jennifer.post(reverse("change-password"), data=data)
    assert response.status_code == 400
    assert response.json()["message"] == "Вы ввели неправильный текущий пароль"


@pytest.mark.parametrize("missing_field", ["currentPassword", "newPassword"])
@pytest.mark.django_db
def test_change_password_missing_field(auth_jennifer, missing_field):
    data = {"currentPassword": "jenn", "newPassword": "newpass123"}
    del data[missing_field]
    response = auth_jennifer.post(reverse("change-password"), data=data)
    assert response.status_code == 400
    assert response.json()["message"] == "Текущий и новый пароль обязательны"


# ---------------------- Тесты аватара ----------------------
@pytest.mark.django_db
def test_upload_avatar_no_file(auth_jennifer):
    response = auth_jennifer.post(reverse("change-avatar"), data={"alt": "just alt"}, format="multipart")
    assert response.status_code == 400
    assert "avatar" in response.json()


# Параметризация для невалидных файлов аватара
@pytest.mark.parametrize(
    "file_name, content, content_type, expected_error_field",
    [
        ("file.txt", b"not an image", "text/plain", "avatar"),
        ("test.jpg", b"fake", "text/plain", "avatar"),
        ("avatar.bmp", VALID_PNG_CONTENT, "image/bmp", "avatar"),
    ],
)
@pytest.mark.django_db
def test_upload_avatar_invalid_file(auth_jennifer, file_name, content, content_type, expected_error_field):
    invalid_file = SimpleUploadedFile(file_name, content, content_type=content_type)
    response = auth_jennifer.post(reverse("change-avatar"), data={"avatar": invalid_file}, format="multipart")
    assert response.status_code == 400
    errors = response.json()
    assert expected_error_field in errors


@pytest.mark.django_db
def test_avatar_delete_removes_file(settings, tmpdir):
    """При вызове delete() у аватара удаляется связанный файл с диска."""
    settings.MEDIA_ROOT = tmpdir.strpath
    avatar_file = SimpleUploadedFile("test_avatar.png", VALID_PNG_CONTENT, content_type="image/png")
    avatar = Avatar.objects.create(src=avatar_file, alt="Test")
    avatar_path = avatar.src.path
    assert os.path.exists(avatar_path)

    avatar.delete()
    # Объект удалён из БД
    assert not Avatar.objects.filter(id=avatar.id).exists()
    # Файл удалён с диска
    assert not os.path.exists(avatar_path)


@pytest.mark.django_db
def test_avatar_delete_handles_missing_file():
    """Если файл уже отсутствует, delete() не вызывает ошибку (только удаляет объект)."""
    avatar = Avatar.objects.create(alt="No file")
    # Симулируем, что файл не сохранялся: src.name есть, но файла нет
    avatar.delete()
    assert not Avatar.objects.filter(id=avatar.id).exists()


# Валидный PNG 1x1 (минимальный)
VALID_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfF4SJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

# Валидный JPEG 1x1 (минимальный)
VALID_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwAUUUUAFFFFABRRRQAUUUUAf/2Q=="
)

# Валидный GIF 1x1 (минимальный)
VALID_GIF = base64.b64decode("R0lGODlhAQABAIAAAP///wAAACH5BAAAAAAALAAAAAABAAEAAAICRAEAOw==")


@pytest.mark.django_db
class TestAvatarUploadSerializer:
    def test_valid_jpeg(self):
        serializer = AvatarUploadSerializer(
            data={"avatar": SimpleUploadedFile("avatar.jpg", VALID_JPEG, content_type="image/jpeg")}
        )
        assert serializer.is_valid()

    def test_valid_gif(self):
        serializer = AvatarUploadSerializer(
            data={"avatar": SimpleUploadedFile("avatar.gif", VALID_GIF, content_type="image/gif")}
        )
        assert serializer.is_valid()

    # ----- Файл не является изображением (коррумпированный) -----
    def test_not_an_image(self):
        not_image = SimpleUploadedFile("avatar.jpg", b"this is not an image", content_type="image/jpeg")
        serializer = AvatarUploadSerializer(data={"avatar": not_image})
        assert not serializer.is_valid()
        # ImageField должен вернуть стандартную ошибку
        error_msg = str(serializer.errors["avatar"][0])
        assert "Upload a valid image" in error_msg or "corrupted image" in error_msg


# тестирование utils.py


@pytest.fixture
def user_jennifer(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(username="jennifer", password="testpass123")
    # Убедимся, что профиль существует и full_name заполнен
    profile, _ = Profile.objects.update_or_create(user=user, defaults={"full_name": user.username})
    return user


@pytest.mark.django_db
class TestParseRequestData:
    """
    Тесты для parse_request_data.
    Создаём подставные объекты с нужными атрибутами, чтобы не зависеть от DRF-парсеров.
    """

    def test_parse_swagger_json(self):
        """Данные в формате application/json."""
        mock_request = SimpleNamespace(content_type="application/json", data={"id": 10, "count": 3})
        result = parse_request_data(mock_request)
        assert result == {"id": 10, "count": 3}

    def test_parse_frontend_form_data(self):
        """Фронтенд передаёт JSON-строку как единственный ключ form-data."""

        # Мок-объект, где data – это форма с одним ключом (JSON-строка)
        # Поскольку request.data.keys() возвращает список ключей, делаем его методами
        class MockData:
            def keys(self):
                return ['{"name": "test", "active": true}']

        mock_request = SimpleNamespace(content_type="multipart/form-data", data=MockData())
        result = parse_request_data(mock_request)
        assert result == {"name": "test", "active": True}


@pytest.mark.django_db
class TestGetProfile:
    def test_get_profile_existing(self, user_jennifer):
        profile = get_profile(user_jennifer)
        assert profile.user == user_jennifer
        assert profile.full_name == user_jennifer.username

    def test_get_profile_creates_new(self, user_jennifer, caplog):
        Profile.objects.filter(user=user_jennifer).delete()

        with caplog.at_level(logging.INFO):
            profile = get_profile(user_jennifer)

        assert profile.user == user_jennifer
        assert profile.full_name == user_jennifer.username
