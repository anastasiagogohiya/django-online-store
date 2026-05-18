FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev netcat-openbsd postgresql-client curl \
    fonts-dejavu \
    fonts-liberation \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

WORKDIR /app

# Poetry
RUN pip install --no-cache-dir poetry==1.8.0

# Копируем зависимости
COPY megano/pyproject.toml megano/poetry.lock* /app/

# Настраиваем Poetry и устанавливаем зависимости (без виртуального окружения)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Копируем весь код бэкенда
COPY megano /app

# Копируем фронтенд
COPY diploma-frontend /app/diploma-frontend

# Устанавливаем фронтенд
RUN pip install /app/diploma-frontend/dist/diploma_frontend-0.6.tar.gz

RUN mkdir -p /tmp/prometheus-django && chmod 777 /tmp/prometheus-django

# Копируем entrypoint.sh из папки docker
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]