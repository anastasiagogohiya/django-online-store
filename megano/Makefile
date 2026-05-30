# Makefile для Django проекта с ruff, mypy, pytest, coverage

.PHONY: help lint format type-check test coverage clean all

help:
	@echo "Доступные команды:"
	@echo "  make lint        - запустить ruff (линтер)"
	@echo "  make format      - автоматически исправить форматирование ruff"
	@echo "  make type-check  - проверить типы mypy"
	@echo "  make test        - запустить pytest"
	@echo "  make coverage    - запустить pytest с coverage (отчёт с пропущенными строками)"
	@echo "  make all         - выполнить все проверки (lint, type-check, coverage)"
	@echo "  make clean       - удалить кэш Python и папки .pytest_cache, .mypy_cache, .ruff_cache, htmlcov"

lint:
	ruff check megano/

format:
	ruff check --fix megano/
	ruff format megano/

type-check:
	mypy app_users catalog basket order payment megano kafka_integration

test:
	pytest

coverage:
	pytest --cov --cov-report=term-missing

all: lint type-check test coverage
	@echo "✅ All checks passed!"


.PHONY: kafka
kafka:
	@echo "🚀 Запуск Kafka, Zookeeper..."
	cd docker && docker-compose -f docker-compose.kafka.yml up -d


# Celery worker (должен выполняться из корня megano с активированным poetry)
.PHONY: celery-worker
celery-worker:
	@echo "🧵 Запуск Celery worker..."
	cd megano && poetry run celery -A megano worker -l info

# Consumer склада (обработка сообщений из Kafka)
.PHONY: warehouse-consumer
warehouse-consumer:
	@echo "📦 Запуск consumer склада..."
	cd megano && poetry run python manage.py run_warehouse_consumer

# Запуск Django development сервера
.PHONY: runserver
runserver:
	cd megano && poetry run python manage.py runserver

# (Опционально) всё вместе для локальной разработки: инфраструктура + миграции + демо-данные
.PHONY: dev
dev:
	@echo "🔄 Применяем миграции и загружаем демо-данные..."
	cd megano && poetry run python manage.py migrate
	cd megano && poetry run python manage.py load_demo_data
	@echo "✅ Готово. Теперь в отдельных терминалах выполните:"
	@echo "   make celery-worker"
	@echo "   make warehouse-consumer"
	@echo "   make runserver"