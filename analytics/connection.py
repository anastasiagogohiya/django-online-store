# Создаем engine и проверяем соединение
import os
import pandas as pd
from sqlalchemy import create_engine, URL
from sqlalchemy.engine import Engine

# Создаем отдельного пользователя аналитика для БД read-only

# ============================================================
# 1. ПОДКЛЮЧЕНИЕ
# Знает ТОЛЬКО про то, как открыть дверь.
# Не знает ни про разведку, ни про бизнес.
# ============================================================

def get_engine(
    user: str = None,
    password: str = None,
    host: str = None,
    port: int = None,
    database: str = None,
) -> Engine:
    """
    Создаёт engine. Параметры берутся из env-переменных,
    если не переданы явно. Это позволяет не хардкодить креды.
    """
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=user or os.getenv("PG_USER", "analytics"),
        password=password or os.getenv("PG_PASS", "analytics_pass"),
        host=host or os.getenv("PG_HOST", "localhost"),
        port=int(port or os.getenv("PG_PORT", 5433)),
        database=database or os.getenv("PG_DB", "megano_prod"),
    )
    return create_engine(url)


def check_connection(engine: Engine) -> str:
    """Возвращает имя текущей БД. Заодно проверяет, что соединение живое."""
    with engine.connect() as conn:
        return pd.read_sql("SELECT current_database()", conn).iloc[0, 0]
