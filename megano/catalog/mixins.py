# catalog/mixins.py
import os
from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.utils.text import slugify

"""Валидация на уровне моделей БД с помощью миксинов ниже."""

class ImageValidatorMixin:
    """Миксин для валидации изображений"""

    ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
    MAX_SIZE_MB = 5
    MIN_WIDTH = 100
    MIN_HEIGHT = 100

    def validate_image(self, image_field, field_name='image', max_size_mb=None, min_width=None, min_height=None):
        """Универсальная валидация изображения"""
        if not image_field:
            return

        max_size_mb = max_size_mb or self.MAX_SIZE_MB
        min_width = min_width or self.MIN_WIDTH
        min_height = min_height or self.MIN_HEIGHT

        # Проверка расширения
        ext = os.path.splitext(image_field.name)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValidationError({
                field_name: f'Неподдерживаемый формат. Разрешенные: {", ".join(self.ALLOWED_EXTENSIONS)}'
            })

        # Проверка размера файла
        if image_field.size > max_size_mb * 1024 * 1024:
            raise ValidationError({
                field_name: f'Размер изображения не должен превышать {max_size_mb}MB'
            })

        # Проверка размеров изображения
        try:
            width, height = get_image_dimensions(image_field)
            if width and height:
                if width < min_width or height < min_height:
                    raise ValidationError({
                        field_name: f'Минимальный размер изображения {min_width}x{min_height} пикселей'
                    })
        except Exception:
            raise ValidationError({
                field_name: 'Не удалось прочитать изображение. Файл поврежден.'
            })


class SlugMixin:
    """Миксин для авто создания slug (красивый url)
       применяется в Category и Product.
    """
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            if self.__class__.objects.filter(slug=self.slug).exists():
                import uuid
                self.slug = f"{self.slug}-{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)
