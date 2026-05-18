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
	mypy app_users catalog basket order payment megano

test:
	pytest

coverage:
	pytest --cov --cov-report=term-missing

all: lint type-check test coverage
	@echo "✅ All checks passed!"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -delete 2>/dev/null || true