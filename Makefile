# Инициализация окружения: создание .env из шаблона (если файл не существует)
# плюс автогенерация секретного ключа
.PHONY: init-env
init-env:
	@if [ ! -f megano/.env ]; then \
		cd megano && cp .env.example .env; \
		KEY=$$(python -c "import secrets; print(secrets.token_urlsafe(32))"); \
		sed -i "s/secret_key_here/$$KEY/" .env; \
		echo "Файл .env создан, секретный ключ сгенерирован."; \
	else \
		echo "Файл .env уже существует, пропускаем."; \
	fi


# Запуск всего стека (продакшн-режим, DEBUG=false)
.PHONY: up
up: init-env
	cd docker && docker compose up -d

# Просмотр логов всех сервисов
logs:
	cd docker && docker compose logs -f app db redis celery

logs-kafka-wh:
	cd docker && docker compose logs -f warehouse_consumer

logs-mon:
	cd docker && docker compose logs -f prometheus grafana postgres-exporter redis-exporter nginx-exporter celery-exporter


# Запуск только мониторинга (Prometheus + Grafana)
.PHONY: metrics
metrics:
	cd docker && docker compose up -d prometheus grafana

# Остановка всех контейнеров
.PHONY: down
down:
	cd docker && docker compose down

# Перезапуск (down + up)
.PHONY: restart
restart:
	cd docker && docker compose down && docker compose up -d

# Пересборка без кэша
.PHONY: rebuild
rebuild:
	cd docker && docker compose down && docker compose build --no-cache && docker compose up -d


# Тотальная очистка и пересборка, особождем порт кафки
.PHONY: total clean
total clean:
	cd docker && docker-compose down --volumes --remove-orphans
	-docker stop kafka_new 2>/dev/null || true
	-docker rm kafka_new 2>/dev/null || true
	docker system prune -f