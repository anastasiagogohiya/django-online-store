<p align="center">
  <img src="assets_readme/megano_title.png" width="300" alt="Banner megano">
</p>

<p align="center">
  <span style="font-size: 20px;"><em>Megano интернет магазин</em></span><br/>
</p>

<p align="center">
  <img src="https://284baef4-3d14-4ca5-8247-4811f0d6b14b.selstorage.ru/32c29ffa-b8e5-4b30-a115-d81240d46b2e_5a734ac2-88d7-422f-8ac0-075e0095894b.png" width="600" alt="Бейджики технологий">
</p>

## ✨ Функционал

- Аутентификация пользователя, с личным кабинетом пользователя
- Просмотр товаров на сайте по разным параметрам: поиск, сортировки, фильтры, категории, теги, распродажи т.д.
- Просмотр детальной информации с изображениями товаров
- Добавление товара в корзину
- Изменение количества товара в корзине
- Оформление заказа
- Оплата заказа (Celery + Redis)
- Отправка через Kafka сообщений на склад по сбору заказа
- Просмотр отзывов, написание отзывов
- Внедрение ролей с определенными разрешениями: Админ, Клиент, Менеджер, Продавец
- Создание, редактирование, мягкое удаление сущностей через Административную панель
- Автоматическая загрузка демо данных для демонстрации


## 🖥 Интерфейс

<p align="center">
  <img src="assets_readme/megano_actions.gif" width="800" alt="Работа на сайте">
</p>

<br>

-------------------------------------------------------------------------------------------------------
-------------------------------------------------------------------------------------------------------
## 🚀 Требования к запуску приложения через **Docker**

### 📦 Требования
Проверьте версии инструментов:
```bash
docker --version
docker compose version
```

### Приложение тестировалось на версиях:
Docker 29.1.5
Docker Compose 5.0.2

### Запуск проекта (с созданием .env)
**Внимание! Команды make - из Makefile.**
1. Клонируем репозиторий
```bash
git clone https://gitlab.skillbox.ru/anastasiia_gogokhiia/python_django_diploma.git
cd python_django_diploma
```
2. Запускаем проект (вручную ничего делать не нужно!)
```bash
make up
```
Откройте браузер http://localhost или http://127.0.0.1 и проверьте работу сайта.

------------------
При выполнении команды make up автоматически:
- Создается .env файл в нужной директории, с автогенерацией ключа
- Создается образ
- Поднимается PostgreSQL
- Создаются таблицы БД
- Применяются миграции
- Запускается сервис Редис
- Запускается сервис Celery
- Запускается сервис Kafka
- Запускается сервис склада для приема сообщений от Kafka
- Запускается NGINX
- Запускается GRAFANA + PROMETHEUS
- Загружаются демонстрационные данные в БД

3. Чтобы остановить контейнер
```bash
make down
```

-----------------------------------------------------
### Проверка работы приложения и ❗ Возможные проблемы
Если приложение не запускается, проверьте логи сервисов в реальном времени 
(app db redis celery nginx):
```bash
make logs
```
Сообщения передающиеся Кафка можно посмотреть на http://localhost:8080

Предупреждение:
порты 8000 (Django), 3000 (Grafana), 9090 (Prometheus) должны быть свободны!


### Документация
Swagger — [http://127.0.0.1:8000/api/schema/swagger/](http://127.0.0.1:8000/api/schema/swagger/) *(доступно после запуска Docker контейнера)*  
ReDoc — [http://127.0.0.1:8000/api/schema/redoc/](http://127.0.0.1:8000/api/schema/redoc/) *(доступно после запуска Docker контейнера)*

### 📊 Мониторинг (Prometheus + Grafana)
После запуска проекта (`make up`) мониторинг доступен по адресам:
- **Grafana** — [http://localhost:3000](http://localhost:3000)  
  *Логин/пароль по умолчанию:* `admin` / `admin` (при первом входе система попросит сменить пароль)
- **Prometheus** — [http://localhost:9090](http://localhost:9090)

В проекте есть файл с готовыми дашбордами:
1) Зайдите в Grafana введите логин и пароль
2) В Connections (меню слева) -> Data sources -> Add data source
   выберете Prometheus, URL http://prometheus:9090 и кнопка внизу Save & test.
3) В Dashboards (меню слева) -> Кнопка New справа -> Import -> 
   Upload file -> выбираете путь python_django_diploma/docker/megano_dashboard.json

Дашборды Grafana предварительно настроены для отображения метрик:
- PostgreSQL (через экспортёр)
- Redis
- Nginx
- Celery
- Django (через django-prometheus)

**Примечание:** Для просмотра логов сервисов мониторинга используйте команду:
```bash
make logs-mon
```
-----------------------------------------------------------------------------------------------------------
-----------------------------------------------------------------------------------------------------------
## 💻 Локальная разработка (без Docker, режим DEBUG=true) и тестирование
Если вы хотите запустить проект **вручную, без Docker** (например, для отладки или быстрых тестов):

**Важно:** Если у вас уже запущены контейнеры (`make up`), сначала остановите их:
```bash
cd python_django_diploma
make down
```

### Запуск в режиме DEBUG
1. Зайдите в `.env` файл раскомментируйте/закомментируйте как там написано (всего 2 строчки). Всё!
2. Выполните:
```bash
cd megano
pipx install poetry
poetry install
poetry shell
cd megano && poetry run python manage.py migrate
cd megano && poetry run python manage.py load_demo_data
cd megano && poetry run python manage.py runserver
```

### 🧪 Тестирование, запуск тестов, покрытие
```bash
cd megano
make test
make coverage
```
Покрытие тестами: **90%**

---
### 🧹 Проверка качества кода
- ruff — проверка стиля, форматирование
- mypy — проверка типов
```bash
make lint
make type-check
```

## Переключение между БД
Переключение происходит в .env файле DEBUG=true или false
- **Разработка (`DEBUG=True`)** – автоматически используется SQLite (файл `db.sqlite3`).
- **Продакшн (`DEBUG=False`)** – подключается PostgreSQL, а также активируются Redis, Celery, Nginx, Prometheus, Grafana.

--------------------------------------------------------------------------------------------------------
--------------------------------------------------------------------------------------------------------

## Архитектура, слои проекта
Подробное описание архитектуры в файле [ARCHITECTURE.md](./ARCHITECTURE.md)
Краткая структура проекта:

```text
python_django_diploma
├── README.md, ARCHITECTURE.md, .gitignore, .dockerignore
├── Makefile                     # Команды для докера, запуска проекта
├── docker/                      # env ссылочный файл, Dockerfile, docker-compose.yml, entrypoint.sh и др.
├── diploma-frontend/            # Пакет для фронтенда
└── megano/                      # Корень Django-проекта: manage.py, .env, conftest, pyproject, poetry и др               
    ├── megano/                  # Внутренний пакет проекта: settings, celery, обработчики ошибок
    ├── api/                     # Приложение API
    ├── app_users/               # Управление пользователями и профилями
    ├── catalog/                 # Каталог товаров, загрузка демо данных
    ├── basket/                  # Корзина покупок
    ├── order/                   # Заказы
    ├── payment/                 # Платежи, очередь
    ├── kafka_integration/       # Kafka, передача событий на склад
    ├── media/                   # Изображения
    ├── manage.py                
    └── poetry.lock, .env, pyproject.toml                   
    
          
```


## 🛠 Технологии

**Backend**
- Python 3.12
- Django 5.0
- Django REST Framework
- Gunicorn

**Базы данных и кэширование**
- PostgreSQL (продакшн)
- SQLite (разработка)

**Брокеры сообщений и очереди**
- Celery + Redis
- Kafka (события для склада)

**Контейнеризация и оркестрация**
- Docker
- Docker Compose
- Nginx

**Мониторинг**
- Prometheus
- Grafana
- django-prometheus
- Экспортёры (PostgreSQL, Redis, Nginx, Celery)

**Тестирование и качество кода**
- pytest (покрытие 89%)
- ruff (линтер + форматтер)
- mypy (проверка типов)

**Документация API**
- drf-spectacular (Swagger/ReDoc)

**Управление зависимостями**
- Poetry

---