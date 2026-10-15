"""
Разведка чужой Postgres-БД.

Слои:
  1. Подключение           — get_engine, check_connection
  2. Карта таблиц          — размер, строки, активность, структура
  3. Колонки               — типы, PK/FK/UNIQUE, комментарии
  4. FK-граф               — кто на кого ссылается
  5. Домены                — группировка по бизнес-областям
  6. Ядро                  — хабы (много FK in) и транзакционные таблицы
  7. Время и деньги        — где даты и где суммы
  8. Аномалии              — дубли имён, таблицы без FK
  9. Sample данных         — SELECT * LIMIT 5 из ключевых таблиц
 10. Health                — bloat, stale stats, unused indexes (в конце!)

Запуск:
    cd analytics
    python -m src.recon.main
"""

import os
import re
from typing import Optional
import pandas as pd
from connection import get_engine, check_connection
from sqlalchemy.engine import Engine
from src.recon.tables_columns_fk import recon_tables, recon_columns, recon_foreign_keys
from src.recon.domains_time_money import (add_domain,
                                          recon_time_columns,
                                          print_domains,
                                          recon_money_columns,
                                          print_time_and_money, print_hubs, print_transactional)
from src.recon.anomalies_sample_health import (print_anomalies,
                                               sample_tables, print_samples, get_exact_counts,
                                               analyze_health,
                                               print_health)




# ============================================================
# MAIN
# Порядок вызовов отражает порядок разведки:
# сначала смысл, потом гигиена.
# ============================================================

def main():
    engine = get_engine()
    print(f"✅ Подключено к БД: {check_connection(engine)}\n")

    # --- Сырые данные ---
    tables = recon_tables(engine)
    columns = recon_columns(engine)
    fks = recon_foreign_keys(engine)
    time_cols = recon_time_columns(engine)
    money_cols = recon_money_columns(engine)

    print(f"📋 Таблиц/матвью: {len(tables)}")
    print(f"🧱 Колонок:      {len(columns)}")
    print(f"🔗 FK:           {len(fks)}")
    print()

    tables = add_domain(tables)
    print_domains(tables)
    print_hubs(tables)
    print_transactional(tables)
    print_time_and_money(time_cols, money_cols)
    print_anomalies(tables, fks)

    # --- Sample данных ---
    samples = sample_tables(engine, tables, n=5, top=8)
    print_samples(samples)

    tables = analyze_health(tables)
    print_health(tables)

    # --- Точные цифры (для мелких БД) ---
    if len(tables) <= 50:
        try:
            exact = get_exact_counts(engine)
            merged = tables.merge(exact, on="table_name", how="left")
            print("=== ТОЧНЫЕ COUNT(*) (там, где оценка врёт) ===\n")
            mismatch = merged[
                merged["exact_rows"].notna()
                & (merged["exact_rows"] != merged["live_rows"].fillna(0))
            ]
            if mismatch.empty:
                print("  (оценки совпадают с реальностью)\n")
            else:
                print(mismatch[["table_name", "live_rows", "exact_rows"]]
                      .to_string(index=False))
                print()
        except Exception as e:
            print(f"⚠️  Не удалось посчитать точные count: {e}\n")


if __name__ == "__main__":
    main()