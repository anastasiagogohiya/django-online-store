import os
import re
from typing import Optional
import pandas as pd
from sqlalchemy.engine import Engine


# ============================================================
# 5. ДОМЕНЫ
# Группировка таблиц по префиксам. Отделяем бизнес от фреймворка.
# Это ПЕРВОЕ, что должен увидеть сеньор в чужой БД.
# ============================================================

# Префиксы, которые точно инфраструктура, а не бизнес
FRAMEWORK_PREFIXES = {"auth", "django", "authtoken", "kafka", "pg"}


def add_domain(df: pd.DataFrame) -> pd.DataFrame:
    """
    Добавляет колонки domain и is_framework.
    domain = префикс до первого подчёркивания.
    """
    df = df.copy()
    df["domain"] = df["table_name"].str.extract(r"^([a-z]+)_")[0].fillna("other")
    df["is_framework"] = df["domain"].isin(FRAMEWORK_PREFIXES)
    return df


def print_domains(df: pd.DataFrame) -> None:
    """Сводка по доменам: сколько таблиц, сколько данных."""
    print("=== ДОМЕНЫ ===\n")
    grouped = (
        df.groupby(["is_framework", "domain"])
        .agg(
            n_tables=("table_name", "count"),
            total_bytes=("total_bytes", "sum"),
            live_rows=("live_rows", "sum"),
        )
        .reset_index()
    )
    grouped["total_size"] = grouped["total_bytes"].apply(
        lambda b: f"{b / 1024:.1f} kB" if b < 1024**2 else f"{b / 1024**2:.1f} MB"
    )
    grouped = grouped.sort_values("total_bytes", ascending=False)

    for is_fw in [False, True]:
        label = "ИНФРАСТРУКТУРА" if is_fw else "БИЗНЕС-ДОМЕНЫ"
        chunk = grouped[grouped["is_framework"] == is_fw]
        if chunk.empty:
            continue
        print(f"--- {label} ---")
        print(chunk[["domain", "n_tables", "total_size", "live_rows"]]
              .to_string(index=False))
        print()


# ============================================================
# 6. ЯДРО
# Хабы (много FK in) и транзакционные таблицы.
# Показывает, вокруг чего вертится система.
# ============================================================

def print_hubs(df: pd.DataFrame, top: int = 10) -> None:
    """Таблицы, на которые смотрит больше всего FK."""
    print("=== ХАБЫ (на кого смотрят FK) ===\n")
    hubs = df[df["n_fk_in"] > 0].nlargest(top, "n_fk_in")
    if hubs.empty:
        print("  (нет FK)\n")
        return
    print(hubs[["table_name", "n_fk_in", "n_fk_out", "live_rows", "total_size"]]
          .to_string(index=False))
    print()


def print_transactional(df: pd.DataFrame) -> None:
    """
    Транзакционные таблицы — те, что пишутся в рантайме.
    Эвристика: имя содержит order/payment/basket/cart/transaction.
    """
    pattern = r"(order|payment|basket|cart|transaction|invoice)"
    chunk = df[df["table_name"].str.contains(pattern, case=False, regex=True)]
    if chunk.empty:
        return
    print("=== ТРАНЗАКЦИОННЫЕ ===\n")
    print(chunk[["table_name", "total_size", "live_rows", "n_fk_out", "n_fk_in"]]
          .to_string(index=False))
    print()


# ============================================================
# 7. ВРЕМЯ И ДЕНЬГИ
# Вход для 90% будущих бизнес-запросов.
# ============================================================

QUERY_TIME_COLUMNS = """
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND column_name ~* '(created|updated|deleted|_at$|_date$|timestamp)'
ORDER BY table_name, column_name;
"""

QUERY_MONEY_COLUMNS = """
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND data_type IN ('numeric', 'integer', 'bigint', 'decimal', 'real',
                    'double precision', 'smallint')
  AND column_name ~* '(price|amount|total|sum|cost|qty|quantity|count|balance)'
ORDER BY table_name, column_name;
"""


def recon_time_columns(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(QUERY_TIME_COLUMNS, engine)


def recon_money_columns(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(QUERY_MONEY_COLUMNS, engine)


def print_time_and_money(time_cols: pd.DataFrame, money_cols: pd.DataFrame) -> None:
    print("=== ВРЕМЕННЫЕ КОЛОНКИ ===")
    if time_cols.empty:
        print("  (нет)\n")
    else:
        # группируем по таблице — так компактнее
        for table, chunk in time_cols.groupby("table_name"):
            cols = ", ".join(chunk["column_name"])
            print(f"  {table}: {cols}")
        print()

    print("=== ДЕНЕЖНЫЕ КОЛОНКИ ===")
    if money_cols.empty:
        print("  (нет)\n")
    else:
        for table, chunk in money_cols.groupby("table_name"):
            cols = ", ".join(
                f"{r.column_name}({r.data_type})"
                for r in chunk.itertuples()
            )
            print(f"  {table}: {cols}")
        print()
