"""
Новогодний отчёт: топ-3 клиента по каждому городу + скидки.
- Pivot по месяцам
- Excel с форматированием
- Отправка на email
"""
import os
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text
from connection import get_engine, check_connection

load_dotenv() # для отправки по почте


def fetch_orders(engine) -> pd.DataFrame:
    """Доставленные заказы за год с городом, клиентом и месяцем."""
    query = text("""
        SELECT
            oo.city,
            oo.profile_id,
            aup.full_name,
            DATE_TRUNC('month', oo.created_at) AS month,
            SUM(oo.total_cost::numeric)        AS month_sum
        FROM order_order oo
        JOIN app_users_profile aup ON aup.id = oo.profile_id
        WHERE oo.status = 'delivered'
          AND oo.created_at >= NOW() - INTERVAL '1 year'
        GROUP BY oo.city, oo.profile_id, aup.full_name,
                 DATE_TRUNC('month', oo.created_at)
    """)
    df = pd.read_sql(query, engine)
    if not df.empty:
        df['month'] = pd.to_datetime(df['month']).dt.strftime('%Y-%m')
    return df


# 2. PIVOT ГОРОДА × МЕСЯЦЫ
def build_monthly_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """Сводная: города × месяцы → сумма заказов."""
    if df.empty:
        return pd.DataFrame()
    pivot = df.pivot_table(
        index='city',
        columns='month',
        values='month_sum',
        aggfunc='sum',
        fill_value=0,
    )
    pivot['ИТОГО'] = pivot.sum(axis=1)
    pivot = pivot.sort_values('ИТОГО', ascending=False)
    return pivot


def build_top3_with_discount(engine) -> pd.DataFrame:
    """Топ-3 клиента по каждому городу + размер новогодней скидки."""
    query = text("""
        WITH ranked AS (
            SELECT
                oo.city,
                oo.profile_id,
                aup.full_name,
                SUM(oo.total_cost::numeric) AS total_sum,
                DENSE_RANK() OVER (
                    PARTITION BY oo.city
                    ORDER BY SUM(oo.total_cost::numeric) DESC
                ) AS rnk
            FROM order_order oo
            JOIN app_users_profile aup ON aup.id = oo.profile_id
            WHERE oo.status = 'delivered'
              AND oo.created_at >= NOW() - INTERVAL '1 year'
            GROUP BY oo.city, oo.profile_id, aup.full_name
        )
        SELECT
            city,
            full_name,
            total_sum,
            rnk,
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
    return pd.read_sql(query, engine)



def save_excel(
    pivot: pd.DataFrame,
    top3: pd.DataFrame,
    path: str | Path = "reports/new_year_report.xlsx",
) -> str:
    """Сохраняет Excel с двумя листами и форматированием."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)   # создаём reports/, если нет

    with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
        # --- лист 1: pivot по месяцам ---
        if not pivot.empty:
            pivot.to_excel(writer, sheet_name='Продажи по месяцам')

            wb = writer.book
            ws = writer.sheets['Продажи по месяцам']
            money_fmt = wb.add_format({'num_format': '#,##0 ₽'})
            header_fmt = wb.add_format({
                'bold': True, 'bg_color': '#D9E1F2', 'border': 1
            })

            for col_num, col_name in enumerate(pivot.columns, start=1):
                ws.write(0, col_num, col_name, header_fmt)
            ws.set_column(0, 0, 25)
            ws.set_column(1, len(pivot.columns), 14, money_fmt)

        # --- лист 2: топ-3 со скидками ---
        if not top3.empty:
            top3.to_excel(writer, sheet_name='Топ-3 + скидки', index=False)

            wb = writer.book
            ws = writer.sheets['Топ-3 + скидки']
            money_fmt = wb.add_format({'num_format': '#,##0 ₽'})
            pct_fmt = wb.add_format({'num_format': '0"%"'})
            header_fmt = wb.add_format({
                'bold': True, 'bg_color': '#FFE699', 'border': 1
            })

            for col_num, col_name in enumerate(top3.columns):
                ws.write(0, col_num, col_name, header_fmt)

            ws.set_column(0, 0, 20)   # city
            ws.set_column(1, 1, 30)   # full_name
            ws.set_column(2, 2, 16, money_fmt)  # total_sum
            ws.set_column(3, 3, 8)    # rnk
            ws.set_column(4, 4, 12, pct_fmt)    # discount

    return str(path)



def build_html_body(pivot: pd.DataFrame, top3: pd.DataFrame) -> str:
    """Красивая HTML-таблица для вставки в тело письма."""
    style = """
    <style>
        body { font-family: Arial, sans-serif; color: #333; }
        h2 { color: #c0392b; }
        table { border-collapse: collapse; margin: 12px 0; }
        th, td { border: 1px solid #ddd; padding: 6px 10px; }
        th { background: #f2f2f2; }
        .money { text-align: right; }
        .top1 { background: #ffe699; font-weight: bold; }
    </style>
    """
    html = [style, "<h2>🎄 Новогодний отчёт</h2>"]

    if not top3.empty:
        html.append("<h3>Топ-3 клиента по городам со скидками</h3>")
        rows = []
        for _, r in top3.iterrows():
            cls = ' class="top1"' if r['rnk'] == 1 else ''
            rows.append(
                f"<tr{cls}><td>{r['city']}</td><td>{r['full_name']}</td>"
                f"<td class='money'>{r['total_sum']:,.0f} ₽</td>"
                f"<td>{int(r['rnk'])}</td>"
                f"<td>{int(r['discount_pct'])}%</td></tr>"
            )
        html.append(
            "<table><tr><th>Город</th><th>Клиент</th><th>Сумма</th>"
            "<th>Место</th><th>Скидка</th></tr>"
            + "".join(rows) + "</table>"
        )

    if not pivot.empty:
        html.append("<h3>Продажи по месяцам (топ-5 городов)</h3>")
        html.append(
            pivot.head(5).to_html(
                classes='money', border=0,
                formatters={c: lambda x: f"{x:,.0f} ₽" for c in pivot.columns}
            )
        )

    html.append("<p>С уважением,<br>Отдел аналитики</p>")
    return "\n".join(html)


def send_email(
    html_body: str,
    attachment_path: str,
    subject: str = "🎄 Новогодний отчёт: топ-3 клиента по городам",
) -> None:
    """Отправляет письмо с HTML-телом и вложением Excel."""
    host = os.getenv('SMTP_HOST')
    port = int(os.getenv('SMTP_PORT', 465))
    user = os.getenv('SMTP_USER')
    password = os.getenv('SMTP_PASSWORD')
    sender = os.getenv('EMAIL_FROM', user)
    recipients = [e.strip() for e in os.getenv('EMAIL_TO', '').split(',') if e.strip()]

    if not all([host, user, password, recipients]):
        raise RuntimeError(
            "Не заданы SMTP_HOST / SMTP_USER / SMTP_PASSWORD / EMAIL_TO в .env"
        )

    msg = EmailMessage()
    msg['From'] = sender
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = make_msgid()

    # текстовая версия (fallback)
    msg.set_content("Новогодний отчёт. Откройте в HTML-совместимом клиенте.")
    # HTML версия
    msg.add_alternative(html_body, subtype='html')

    # вложение
    with open(attachment_path, 'rb') as f:
        msg.add_attachment(
            f.read(),
            maintype='application',
            subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=Path(attachment_path).name,
        )

    with smtplib.SMTP_SSL(host, port) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)

    print(f"Письмо отправлено: {', '.join(recipients)}")


def main():
    engine = get_engine()
    print(f"Подключено к БД: {check_connection(engine)}")

    # 1.
    orders = fetch_orders(engine)
    print(f"\nЗаказов в сырье: {len(orders)}")

    # 2. Pivot
    pivot = build_monthly_pivot(orders)
    if not pivot.empty:
        print("\n[Pivot: города × месяцы]")
        print(pivot.head(10).to_string())

    # 3. Топ-3 со скидками
    top3 = build_top3_with_discount(engine)
    print(f"\n[Топ-3 призёров: {len(top3)}]")
    if not top3.empty:
        print(top3.to_string(index=False))

    # 4. Excel
    xlsx_path = save_excel(pivot, top3)
    print(f"\nExcel сохранён: {xlsx_path}")

    # 5. HTML + email
    html = build_html_body(pivot, top3)
    with open('reports/email_preview.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("HTML-превью: email_preview.html")

    try:
        send_email(html, xlsx_path)
    except Exception as e:
        print(f"\n⚠ Email не отправлен: {e}")
        print("Проверьте .env и попробуйте снова.")


if __name__ == "__main__":
    main()