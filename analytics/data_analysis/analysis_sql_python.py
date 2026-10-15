import pandas as pd
import numpy as np
from pathlib import Path
from connection import get_engine, check_connection
from sqlalchemy import text

# Запрос через SQL напрямую в таблицу
def get_active_users_by_letter(engine, letter: str) -> pd.DataFrame:
    """Активные пользователи, чья фамилия начинается с указанной буквы
    Args:
        engine: подключение SQLAlchemy
        letter: первая буква фамилии

    Returns:
        DataFrame с колонками: last_name, first_name, email, phone
    """
    query = text("""
        select au.last_name, au.first_name, au.email, aup.phone
        from auth_user au
        left join app_users_profile aup on au.id = aup.user_id
        where au.last_name like :letter and au.is_active = True;
        """)
    df = pd.read_sql(query, engine, params={"letter": f"{letter}%"})
    print(f"\nНайдено записей: {len(df)}")
    print(df.to_string(index=False))
    return df


def main():
    engine = get_engine()
    print(f"Подключено к БД: {check_connection(engine)}")
    letter = 'А'
    df = get_active_users_by_letter(engine, letter)

    if df.empty:
        print(f"По букве '{letter}' никого не найдено — файл не сохранён.")
        return df

    reports_dir = Path(__file__).resolve().parent.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    out_path = reports_dir / f"users_{letter}.xlsx"
    df.to_excel(out_path, index=False)

    print(f"\nФайл сохранён: {out_path}")
    return df


if __name__ == "__main__":
    main()







