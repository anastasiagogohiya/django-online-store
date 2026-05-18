#!/bin/sh
set -e

wait_for_postgres() {
    echo "Waiting for PostgreSQL at $POSTGRES_DB_HOST:$POSTGRES_DB_PORT..."
    while ! nc -z "$POSTGRES_DB_HOST" "$POSTGRES_DB_PORT"; do
        sleep 0.1
    done
    echo "PostgreSQL started"
}

wait_for_redis() {
    echo "Waiting for Redis at redis:6379..."
    while ! nc -z redis 6379; do
        sleep 0.1
    done
    echo "Redis started"
}

# ждём PostgreSQL
wait_for_postgres

# Определяем роль, поэтапно попорядку
ROLE=${CONTAINER_ROLE:-app}

if [ "$ROLE" = "app" ]; then
    echo "=== Running as app container ==="
    python manage.py migrate --noinput
    if [ "$LOAD_DEMO_DATA" = "true" ]; then
        echo "Loading demo data..."
        python manage.py load_demo_data
    fi
    python manage.py collectstatic --noinput
    echo "Starting Gunicorn..."
    exec gunicorn megano.wsgi:application --bind 0.0.0.0:8000 --timeout 300 --workers 4 --max-requests 1000 --max-requests-jitter 50

elif [ "$ROLE" = "celery" ]; then
    echo "=== Running as celery container ==="
    wait_for_redis
    echo "Starting Celery worker..."
    exec celery -A megano worker --loglevel=info

else
    echo "Unknown role: $ROLE"
    exit 1
fi