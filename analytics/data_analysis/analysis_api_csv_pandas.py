"""
Анализ данных из БД, CSV, API. А также их объединение.
Результат: reports/combined_report.xlsx
cd analytics
python -m data_analysis.analysis_api_csv_pandas
"""
import json
from pathlib import Path
from io import StringIO
import pandas as pd
import numpy as np
from sqlalchemy import text
from connection import get_engine, check_connection


# ============================================================
# ИСТОЧНИК БД PostgreSQL: запрос SQL + Python + Pandas
# ============================================================
def source_a_postgres(engine) -> pd.DataFrame:
    """Топ-3 клиента по каждому городу — из БД."""

    query = text("""
        WITH ranked AS (
            SELECT oo.city, oo.profile_id, aup.full_name,
                SUM(oo.total_cost::numeric) AS total_sum,
                DENSE_RANK() OVER (
                    PARTITION BY oo.city
                    ORDER BY SUM(oo.total_cost::numeric) DESC
                ) AS rnk
            FROM order_order oo
            JOIN app_users_profile aup ON aup.id = oo.profile_id
            WHERE oo.status = 'delivered' AND oo.created_at >= NOW() - INTERVAL '1 year'
            GROUP BY oo.city, oo.profile_id, aup.full_name)
        SELECT city, full_name, total_sum, rnk,
            CASE rnk
                WHEN 1 THEN 30
                WHEN 2 THEN 20
                WHEN 3 THEN 10
                ELSE 0
            END AS discount_pct
        FROM ranked
        WHERE rnk <= 3
        ORDER BY city, rnk;
    """)
    df = pd.read_sql(query, engine)
    print(f"Получено строк: {len(df)}")
    print(df.head().to_string(index=False))
    return df


# ============================================================
# ИСТОЧНИК CSV: применяем только pandas
# ============================================================
def ensure_csv_exists(path: str = "orders.csv") -> str:
    """Создаёт псевдо файл, если его нет."""
    if not Path(path).exists():
        rng = np.random.default_rng(42)
        cities = ["Москва", "Санкт-Петербург", "Казань", "Новосибирск"]
        names = [f"Клиент_{i}" for i in range(1, 21)]
        rows = []
        for _ in range(200):
            rows.append({
                "city": rng.choice(cities),
                "profile_id": rng.integers(1, 21),
                "full_name": rng.choice(names),
                "total_cost": float(rng.integers(1000, 50000)),
                "status": rng.choice(["delivered", "cancelled"], p=[0.8, 0.2]),
                "created_at": pd.Timestamp("2024-01-01")
                              + pd.Timedelta(days=int(rng.integers(0, 400))),
            })
        pd.DataFrame(rows).to_csv(path, index=False)
        print(f"Создан демо-файл: {path}")
    return path


def source_b_csv(path: str = "orders.csv") -> pd.DataFrame:
    """Топ-3 клиента по каждому городу — из CSV через pandas."""

    df = pd.read_csv(path, parse_dates=["created_at"])

    # 1. Фильтр: доставлено + год от текущей даты
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=365)
    df = df[(df["status"] == "delivered") & (df["created_at"] >= cutoff)]

    # 2. Агрегация: сумма по city + profile_id + full_name
    grouped = (
        df.groupby(["city", "profile_id", "full_name"], as_index=False)
          .agg(total_sum=("total_cost", "sum"))
    )

    # 3. Ранг по городам
    grouped["rnk"] = (
        grouped.groupby("city")["total_sum"]
               .rank(method="dense", ascending=False)
               .astype(int)
    )

    # 4. Фильтр топ-3 + скидка через map
    top3 = grouped[grouped["rnk"] <= 3].copy()
    top3["discount_pct"] = top3["rnk"].map({1: 30, 2: 20, 3: 10}).fillna(0).astype(int)

    top3 = top3.sort_values(["city", "rnk"]).reset_index(drop=True)
    print(f"Получено строк: {len(top3)}")
    print(top3.head().to_string(index=False))
    return top3


# ============================================================
# ИСТОЧНИК API: requests + pandas
# ============================================================
def fetch_api_orders() -> pd.DataFrame:
    """
    Имитация API-ответа. В реальности — requests.get(...).
    Например:
        import requests
        r = requests.get("https://api.example.com/orders",
                         headers={"Authorization": "Bearer ..."})
        return pd.DataFrame(r.json()["items"])
    """
    api_payload = {
        "items": [
            {"city": "Москва", "profile_id": 1, "full_name": "Иванов Иван",
             "total_cost": 45000, "status": "delivered", "created_at": "2025-03-15"},
            {"city": "Москва", "profile_id": 2, "full_name": "Петров Пётр",
             "total_cost": 38000, "status": "delivered", "created_at": "2025-04-02"},
            {"city": "Казань", "profile_id": 3, "full_name": "Сидоров Сидор",
             "total_cost": 52000, "status": "delivered", "created_at": "2025-05-20"},
            {"city": "Казань", "profile_id": 4, "full_name": "Кузнецов Кузьма",
             "total_cost": 41000, "status": "delivered", "created_at": "2025-06-10"},
            {"city": "Москва", "profile_id": 1, "full_name": "Иванов Иван",
             "total_cost": 25000, "status": "delivered", "created_at": "2025-07-01"},]
    }
    return pd.DataFrame(api_payload["items"])


def source_c_api() -> pd.DataFrame:
    """Топ-3 клиента по каждому городу — из API."""
    df = fetch_api_orders()
    df["created_at"] = pd.to_datetime(df["created_at"])

    cutoff = pd.Timestamp.now() - pd.Timedelta(days=365)
    df = df[(df["status"] == "delivered") & (df["created_at"] >= cutoff)]

    grouped = (
        df.groupby(["city", "profile_id", "full_name"], as_index=False)
          .agg(total_sum=("total_cost", "sum"))
    )
    grouped["rnk"] = (
        grouped.groupby("city")["total_sum"]
               .rank(method="dense", ascending=False)
               .astype(int)
    )
    top3 = grouped[grouped["rnk"] <= 3].copy()
    top3["discount_pct"] = top3["rnk"].map({1: 30, 2: 20, 3: 10}).fillna(0).astype(int)

    print(f"Получено строк: {len(top3)}")
    print(top3.to_string(index=False))
    return top3


# ============================================================
# Объединяем данные БД, CSV, API
# ============================================================
def combine_sources(
    a: pd.DataFrame, b: pd.DataFrame, c: pd.DataFrame
) -> pd.DataFrame:
    """Сводим три источника в один отчёт."""
    a = a.assign(source="postgres")
    b = b.assign(source="csv")
    c = c.assign(source="api")
    # concat — просто "склеить" таблицы
    all_df = pd.concat([a, b, c], ignore_index=True)

    # агрегируем по всем источникам
    combined = (
        all_df.groupby(["city", "full_name"], as_index=False)
              .agg(
                  total_sum=("total_sum", "sum"),
                  sources=("source", lambda s: ", ".join(sorted(set(s)))),
              )
    )
    combined["rnk"] = (
        combined.groupby("city")["total_sum"]
                .rank(method="dense", ascending=False)
                .astype(int)
    )
    combined["discount_pct"] = (
        combined["rnk"].map({1: 30, 2: 20, 3: 10}).fillna(0).astype(int)
    )
    combined = combined[combined["rnk"] <= 3].sort_values(["city", "rnk"])

    print(f"Итог после объединения: {len(combined)} строк")
    print(combined.to_string(index=False))
    return combined


def main():
    engine = get_engine()
    print(f"Подключено к БД: {check_connection(engine)}")

    # только SQL
    top3_pg = source_a_postgres(engine)
    # только pandas (CSV)
    csv_path = ensure_csv_exists()
    top3_csv = source_b_csv(csv_path)
    # только pandas (API)
    top3_api = source_c_api()

    # объединение все вышеук. источников (pandas)
    final = combine_sources(top3_pg, top3_csv, top3_api)

    # Сохраняем итог
    out_dir = Path(__file__).resolve().parent.parent/'reports'
    out_dir.mkdir(exist_ok=True)
    final.to_excel(out_dir/"combined_report.xlsx", index=False)
    print("\nИтог сохранён: combined_report.xlsx")




if __name__ == "__main__":
    main()