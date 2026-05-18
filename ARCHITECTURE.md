# 🏗️ Архитектура проекта: Мегано

## 🌳 Структура проекта (3 уровня)
```plaintext
python_django_diploma
├── README.md, ARCHITECTURE.md
├── .gitignore, .dockerignore
├── Makefile                     # Команды для докера, запуска проекта
├── docker/                      # env ссылочный файл, Dockerfile, docker-compose.yml, entrypoint.sh и др.
├── diploma-frontend/            # Пакет для фронтенда
└── megano/                      # Корень Django-проекта
    ├── manage.py                     
    ├── conftest.py              # Настройки pytest
    ├── pyproject.toml           # Конфигурация
    ├── Makefile                 # Автоматизация задач (пайтесты, линтеры, покрытие)
    ├── db.sqlite3               # SQLite база данных (разработка DEBUG=true)
    ├── .coverage                    
    ├── .env   
    ├── .env.example     
    ├── poetry.lock                                 
    │
    ├── megano/                       # Внутренний пакет проекта
    │   ├── settings.py               
    │   ├── urls.py / wsgi.py / asgi.py            
    │   ├── celery.py                 # Конфигурация Celery
    │   ├── middleware.py             # Собственные middleware
    │   ├── permissions.py            # Права доступа
    │   ├── error_handlers.py         # Обработчики ошибок
    │   ├── decorators.py             # Декораторы отлова ошибок
    │   └── tests/                    # Тесты общих модулей
    │
    ├── api/                          # Приложение API
    │
    ├── app_users/                    # Управление пользователями и профилями
    │   ├── auth_views.py / profile_views.py
    │   ├── models.py, profile_serializers.py
    │   ├── utils.py / urls.py / admin.py
    │   └── tests.py / migrations      # Внутри миграции 0002 создание ролей и прав
    │
    ├── catalog/                      # Каталог товаров
    │   ├── models.py / admin.py
    │   ├── views/                    
    │   ├── serializers/              # Сериализаторы
    │   ├── management/               # Внутри комманда с загрузкой демо данных
    │   ├── mixins.py / utils.py
    │   └── tests/
    │
    ├── basket/                       # Корзина покупок
    │   ├── models.py / views.py
    │   ├── serializers.py
    │   ├── mixins.py / admin.py
    │   └── signals.py                # Сигналы для обновления корзины
    │
    ├── order/                        # Заказы
    │   ├── models.py / views.py
    │   ├── serializers.py / admin.py
    │   ├── services.py / utils.py    # Бизнес-логика заказов
    │   ├── utils.py / mixins.py
    │   ├── templates/                # Для админской панели
    │   └── tests/
    │
    ├── payment/                      # Платежи
    │   ├── models.py / views.py
    │   ├── serializers.py
    │   ├── queue.py                  # Очередь платежей (Celery tasks)
    │   └── tests.py / admin.py
    │
    └── media/                        # Пользовательские загружаемые файлы (в реальном продакшене нужен сервер для хранения)
       ├── app_users/
       └── catalog/
          
```

| Слой                     | Реализация в проекте                                                                                                             |
|--------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| **Model (Модель)**       | Модели в `catalog`, `order`, `basket`, `payment`, `app_users`; миграции; база данных PostgreSQL (продакшн) / SQLite (разработка) |
| **View (Представление)** | `views.py`, `services.py`, `utils.py`, `api/` (REST API), middleware, сигналы, Celery (асинхронная логика)                       |
| **Template (Шаблон)**    | `diploma-frontend` (HTML, CSS, статика); для API – сериализаторы + JSON                                                          |