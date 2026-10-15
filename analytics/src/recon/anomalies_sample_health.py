import os
import re
from typing import Optional
import pandas as pd
from sqlalchemy.engine import Engine


# ============================================================
# 8. АНОМАЛИИ
# Дубли имён, таблицы без FK.
# ============================================================

def find_name_anomalies(df: pd.DataFrame) -> list:
    """
    Таблицы, чьи имена совпадают после удаления подчёркиваний.
    Пример: catalog_product_images ↔ catalog_productimage.
    """
    names = df["table_name"].tolist()
    anomalies = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a.replace("_", "") == b.replace("_", ""):
                anomalies.append((a, b))
    return anomalies


def print_anomalies(df: pd.DataFrame, fks: pd.DataFrame) -> None:
    print("=== АНОМАЛИИ ===\n")

    # 1. Похожие имена
    dupes = find_name_anomalies(df)
    if dupes:
        print("Похожие имена (возможный legacy/дубль):")
        for a, b in dupes:
            print(f"  {a}  ↔  {b}")
        print()

    # 2. Таблицы без FK (в обе стороны)
    # Если таблица большая и без FK — возможно, связь через content_type
    # или через JSON-поле. Это важно понять до написания JOIN'ов.
    no_fk = df[(df["n_fk_in"] == 0) & (df["n_fk_out"] == 0)]
    # исключаем фреймворк — там FK часто не нужны
    no_fk = no_fk[~no_fk["is_framework"]]
    if not no_fk.empty:
        print("Бизнес-таблицы без FK (связь вне схемы):")
        print(no_fk[["table_name", "total_size", "live_rows"]]
              .to_string(index=False))
        print()


# ============================================================
# 9. SAMPLE ДАННЫХ
# SELECT * LIMIT 5 из ключевых таблиц.
# Без этого не понять семантику колонок.
# ============================================================

def sample_tables(
    engine: Engine,
    df: pd.DataFrame,
    n: int = 5,
    top: int = 10,
) -> dict:
    """
    Возвращает словарь {table_name: DataFrame} для top-N самых крупных
    бизнес-таблиц. Фреймворк исключаем — там смотреть нечего.
    """
    business = df[~df["is_framework"]].nlargest(top, "total_bytes")
    samples = {}
    for table in business["table_name"]:
        try:
            samples[table] = pd.read_sql(
                f'SELECT * FROM "{table}" LIMIT {n}', engine
            )
        except Exception as e:
            samples[table] = f"Ошибка: {e}"
    return samples


def print_samples(samples: dict) -> None:
    print("=== SAMPLE ДАННЫХ (LIMIT 5) ===\n")
    for table, data in samples.items():
        print(f"--- {table} ---")
        if isinstance(data, pd.DataFrame):
            if data.empty:
                print("  (пусто)\n")
            else:
                print(data.to_string(index=False))
                print()
        else:
            print(f"  {data}\n")


# ============================================================
# 10. HEALTH
# Флаги P1-P6. Это ФИНАЛ разведки, а не её начало.
# ============================================================

def analyze_health(df: pd.DataFrame) -> pd.DataFrame:
    """
    Разметка таблиц флагами.

    ВАЖНО: live_rows = 0 — это НЕ «таблица пустая».
    Это «ANALYZE не было, оценка неизвестна».
    Поэтому флаг P3 (never_analyzed) мягкий: только для больших таблиц.
    """
    df = df.copy()

    # P1: bloat — реально много мёртвых строк
    df["flag_dead_bloat"] = (
        (df["dead_pct"].fillna(0) > 20)
        & (df["dead_rows"].fillna(0) >= 100)
    )

    # P6: never used — таблица никогда не читалась и не писалась
    # (инфраструктура, которую Django создал, но не использует)
    df["flag_never_used"] = (
        (df["live_rows"].fillna(0) == 0)
        & (df["dead_rows"].fillna(0) == 0)
        & (df["seq_scan"].fillna(0) + df["idx_scan"].fillna(0) == 0)
    )

    # P2: stale stats — planner думает, что данные есть, а их нет
    # Обязательное условие: ANALYZE вообще был. Иначе ловим свежие таблицы.
    df["flag_stale_stats"] = (
        df["est_rows"].notna() & (df["est_rows"] > 0)
        & (df["live_rows"].fillna(0) == 0)
        & (df["last_analyze"].notna() | df["last_autoanalyze"].notna())
    )

    # P3: never analyzed — есть данные, но статистики нет.
    # Смягчаем: только для таблиц, где есть смысл анализировать.
    # Порог est_rows >= 100 — иначе это мелкие справочники.
    df["flag_never_analyzed"] = (
        df["last_analyze"].isna()
        & df["last_autoanalyze"].isna()
        & ~df["flag_never_used"]
        & (df["est_rows"].fillna(0) >= 100)
    )

    # P4: empty — к таблице обращались, но она пуста.
    # Исключаем never_used, чтобы флаги не пересекались.
    df["flag_empty"] = (
        (df["live_rows"].fillna(0) == 0)
        & ~df["flag_never_used"]
    )

    # P5: seq_heavy — только на больших таблицах.
    # Порог 1000: ниже seq scan дешевле index scan.
    df["flag_seq_heavy"] = (
        (df["idx_hit_pct"].fillna(100) < 50)
        & (df["live_rows"].fillna(0) > 1000)
    )

    def priority(r):
        # Порядок ВАЖЕН: от критичного к менее.
        # never_used стоит ПЕРЕД empty, иначе P4 забьётся инфраструктурой.
        if r["flag_dead_bloat"]:      return "P1_bloat"
        if r["flag_stale_stats"]:     return "P2_stale_stats"
        if r["flag_never_analyzed"]:  return "P3_never_analyzed"
        if r["flag_never_used"]:      return "P6_unused"
        if r["flag_empty"]:           return "P4_empty"
        if r["flag_seq_heavy"]:       return "P5_seq_heavy"
        return "OK"

    df["priority"] = df.apply(priority, axis=1)
    df["needs_attention"] = df["priority"] != "OK"
    return df


def print_health(df: pd.DataFrame) -> None:
    print("=== HEALTH ===\n")
    print("Легенда:")
    print("  P1_bloat           — dead_pct>20% И dead_rows>=100")
    print("  P2_stale_stats     — est_rows>0, live_rows=0, ANALYZE был")
    print("  P3_never_analyzed  — нет ANALYZE, est_rows>=100")
    print("  P4_empty           — live_rows=0, но обращались")
    print("  P5_seq_heavy       — idx_hit<50% И live_rows>1000")
    print("  P6_unused          — live=0, dead=0, 0 сканов")
    print()

    cols_main = [
        "table_name", "total_size", "live_rows", "dead_pct",
        "idx_hit_pct", "n_columns", "n_indexes", "n_unused_idx",
        "n_triggers", "n_fk_out", "n_fk_in",
    ]
    cols_p2 = [
        "table_name", "total_size", "est_rows", "live_rows",
        "dead_pct", "idx_hit_pct",
    ]
    cols_p3 = [
        "table_name", "total_size", "est_rows", "live_rows",
        "last_analyze", "last_autoanalyze",
    ]
    cols_p6 = ["table_name", "total_size", "live_rows", "n_indexes"]

    for p in ["P1_bloat", "P2_stale_stats", "P3_never_analyzed",
              "P4_empty", "P5_seq_heavy", "P6_unused"]:
        chunk = df[df["priority"] == p]
        if chunk.empty:
            continue
        print(f"--- {p} ({len(chunk)}) ---")
        if p == "P2_stale_stats":
            print(chunk[cols_p2].to_string(index=False))
        elif p == "P3_never_analyzed":
            print(chunk[cols_p3].to_string(index=False))
        elif p == "P6_unused":
            print(chunk[cols_p6].to_string(index=False))
        else:
            print(chunk[cols_main].to_string(index=False))
        print()

    ok = df[df["priority"] == "OK"]
    print(f"--- OK ({len(ok)}) ---")
    if not ok.empty:
        print(ok[cols_main].to_string(index=False))
    print()


# ============================================================
# ТОЧНЫЙ COUNT
# Для мелких БД (до ~50 таблиц, каждая < 1M строк) — можно
# посчитать точное число строк одним запросом. Это НЕ замена
# n_live_tup, а дополнение: точные цифры там, где они важны.
# ============================================================

def get_exact_counts(engine: Engine, schema: str = "public") -> pd.DataFrame:
    """
    Точный count(*) по всем BASE TABLE в схеме.
    ОПАСНО на больших БД — генерирует UNION ALL по всем таблицам.
    Использовать только когда таблиц немного и они мелкие.
    """
    tables = pd.read_sql(f"""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = '{schema}'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """, engine)["table_name"].tolist()

    if not tables:
        return pd.DataFrame(columns=["table_name", "exact_rows"])

    parts = [
        f"SELECT '{t}'::text AS table_name, count(*)::bigint AS exact_rows "
        f'FROM {schema}."{t}"'
        for t in tables
    ]
    return pd.read_sql(" UNION ALL ".join(parts), engine)