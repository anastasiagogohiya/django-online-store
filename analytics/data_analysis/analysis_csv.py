"""
Анализ заказов интернет-магазина. Это аналитика на CSV-файлах через pandas
Полный цикл: очистка → метрики → Excel → HTML с графиками.
Источник(папка data): orders.csv + order_items.csv
Результат: reports/Excel-отчёт (multi-sheet) + HTML-отчёт с Plotly-графиками.
"""
import re
import numpy as np
import pandas as pd
import plotly.express as px
from pathlib import Path


# Чтение данных
BASE_DIR = Path(__file__).resolve().parent.parent  # папка, где лежит analysis_csv.py
orders = pd.read_csv(BASE_DIR/'data'/'full_orders.csv', parse_dates=['created_at'], encoding='cp1251'
)
items = pd.read_csv(BASE_DIR/'data'/'order_items.csv', encoding='cp1251')
print(f"Загружено: orders={len(orders)}, items={len(items)}")


# ============================================================
# 1. ОЧИСТКА ДАННЫХ
# ============================================================
def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Чистим заказы: пропуски, типы, строки, дубликаты."""
    print("\n[Очистка orders]")
    print(f"  Пропусков до: {df.isna().sum().sum()}")
    print(f"  Дубликатов до: {df.duplicated(subset=['order_id']).sum()}")

    # Критичные пропуски — удаляем строки
    df = df.dropna(subset=['order_id', 'status', 'total_cost', 'city'])

    # Числовые типы
    df['total_cost'] = pd.to_numeric(df['total_cost'], errors='coerce')
    df = df.dropna(subset=['total_cost'])

    # Строки: пробелы, регистр
    df['city'] = df['city'].str.strip().str.title()
    df['status'] = df['status'].str.strip().str.lower()
    df['delivery_type'] = df['delivery_type'].str.strip().str.lower()
    df['payment_type'] = df['payment_type'].str.strip().str.lower()

    # Дубликаты по order_id — оставляем первый
    df = df.drop_duplicates(subset=['order_id'], keep='first')
    print(f"  Пропусков после: {df.isna().sum().sum()}")
    print(f"  Строк после очистки: {len(df)}")
    return df


def clean_items(df: pd.DataFrame) -> pd.DataFrame:
    """Чистим позиции: пропуски, типы, строки, вычисляемая колонка."""
    print("\n[Очистка items]")
    print(f"  Пропусков до: {df.isna().sum().sum()}")

    df = df.dropna(subset=['order_id', 'product', 'quantity'])
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
    df['price_at_time'] = pd.to_numeric(df['price_at_time'], errors='coerce').fillna(0)
    df['product'] = df['product'].str.strip().str.title()

    # Вычисляемая колонка — вместо lambda в agg
    df['line_revenue'] = df['price_at_time'] * df['quantity']

    print(f"  Строк после очистки: {len(df)}")
    return df


orders = clean_orders(orders)
items = clean_items(items)


# ============================================================
# 2. СОЕДИНЕНИЕ ТАБЛИЦ
# ============================================================
orders_items = orders.merge(
    items,
    on='order_id',
    how='left',
    validate='1:m',
    suffixes=('', '_item'),
)
print(f"\norders_items: {len(orders_items)} строк, {len(orders_items.columns)} столбцов")


# ============================================================
# 3. БАЗОВЫЕ МЕТРИКИ
# ============================================================
total_orders = len(orders)
total_items = len(items)
delivered_orders = orders[orders['status'] == 'delivered']
delivered_revenue = delivered_orders['total_cost'].sum()


# ============================================================
# 4. МЕТРИКИ С ПРОЦЕНТАМИ
# ============================================================
# --- 4.1 Заказы по статусам ---
status_df = orders['status'].value_counts().reset_index()
status_df.columns = ['Статус', 'Количество']
status_df['Доля, %'] = (status_df['Количество'] / total_orders * 100).round(1)

# --- 4.2 Воронка конверсии ---
funnel_order = ['created', 'accepted', 'paid', 'delivered']
funnel_labels = {
    'created': 'Создан', 'accepted': 'Принят',
    'paid': 'Оплачен', 'delivered': 'Доставлен',
}
funnel_df = pd.DataFrame({
    'Этап': [funnel_labels[s] for s in funnel_order],
    'Количество': [len(orders[orders['status'] == s]) for s in funnel_order],
})
funnel_df['Конверсия от всех, %'] = (
    funnel_df['Количество'] / total_orders * 100
).round(1)
funnel_df['Конверсия от предыдущего, %'] = (
    funnel_df['Количество'] / funnel_df['Количество'].shift(1) * 100
).round(1)
funnel_df.loc[0, 'Конверсия от предыдущего, %'] = 100.0

# --- 4.3 Средний чек по доставке ---
avg_df = (
    delivered_orders.groupby('delivery_type')
    .agg(**{
        'Заказов': ('order_id', 'count'),
        'Средний чек, $': ('total_cost', 'mean'),
        'Выручка, $': ('total_cost', 'sum'),
    })
    .round(2)
    .reset_index()
    .rename(columns={'delivery_type': 'Тип доставки'})
)
avg_df['Доля заказов, %'] = (
    avg_df['Заказов'] / avg_df['Заказов'].sum() * 100
).round(1)
avg_df['Доля выручки, %'] = (
    avg_df['Выручка, $'] / avg_df['Выручка, $'].sum() * 100
).round(1)

# --- 4.4 Топ товаров ---
top_df = (
    items.groupby('product')
    .agg(**{
        'Продано, шт': ('quantity', 'sum'),
        'Выручка, $': ('line_revenue', 'sum'),
    })
    .sort_values('Продано, шт', ascending=False)
    .round(2)
    .reset_index()
    .rename(columns={'product': 'Товар'})
)
top_df['Доля продаж, %'] = (
    top_df['Продано, шт'] / top_df['Продано, шт'].sum() * 100
).round(1)
top_df['Доля выручки, %'] = (
    top_df['Выручка, $'] / top_df['Выручка, $'].sum() * 100
).round(1)

# --- 4.5 Выручка по городам ---
city_df = (
    delivered_orders.groupby('city')
    .agg(**{
        'Заказов': ('order_id', 'count'),
        'Выручка, $': ('total_cost', 'sum'),
        'Средний чек, $': ('total_cost', 'mean'),
    })
    .sort_values('Выручка, $', ascending=False)
    .round(2)
    .reset_index()
    .rename(columns={'city': 'Город'})
)
city_df['Доля выручки, %'] = (
    city_df['Выручка, $'] / city_df['Выручка, $'].sum() * 100
).round(1)
city_df['Доля заказов, %'] = (
    city_df['Заказов'] / city_df['Заказов'].sum() * 100
).round(1)

# --- 4.6 Типы оплаты ---
pay_df = orders['payment_type'].value_counts().reset_index()
pay_df.columns = ['Тип оплаты', 'Количество']
pay_df['Доля, %'] = (pay_df['Количество'] / total_orders * 100).round(1)

# --- 4.7 Динамика по дням ---
daily = orders.copy()
daily['Дата'] = daily['created_at'].dt.date
daily_df = (
    daily.groupby('Дата')
    .agg(**{
        'Заказов': ('order_id', 'count'),
        'Выручка, $': ('total_cost', 'sum'),
    })
    .reset_index()
)
daily_df['Выручка, $'] = daily_df['Выручка, $'].round(2)

# --- 4.8 Pivot городов по месяцам ---
orders['month'] = orders['created_at'].dt.to_period('M').astype(str)
pivot_city_month = orders.pivot_table(
    index='city',
    columns='month',
    values='total_cost',
    aggfunc='sum',
    fill_value=0,
).round(2).reset_index().rename(columns={'city': 'Город'})
pivot_city_month['ИТОГО'] = pivot_city_month.select_dtypes('number').sum(axis=1)
pivot_city_month = pivot_city_month.sort_values('ИТОГО', ascending=False)

# --- 4.9 Сегментация заказов по чеку ---
orders['segment'] = pd.cut(
    orders['total_cost'],
    bins=[0, 1000, 5000, 20000, np.inf],
    labels=['Мелкий', 'Средний', 'Крупный', 'VIP'],
)
segment_df = (
    orders.groupby('segment', observed=True)
    .agg(**{
        'Заказов': ('order_id', 'count'),
        'Выручка, $': ('total_cost', 'sum'),
        'Средний чек, $': ('total_cost', 'mean'),
    })
    .round(2)
    .reset_index()
)
segment_df['Доля заказов, %'] = (
    segment_df['Заказов'] / segment_df['Заказов'].sum() * 100
).round(1)
segment_df['Доля выручки, %'] = (
    segment_df['Выручка, $'] / segment_df['Выручка, $'].sum() * 100
).round(1)

# --- 4.10 RFM-сегментация клиентов через qcut ---
if 'customer_id' in orders.columns:
    rfm_source = orders.groupby('customer_id').agg(
        last_order=('created_at', 'max'),
        frequency=('order_id', 'count'),
        monetary=('total_cost', 'sum'),
    ).reset_index()

    rfm_source['recency'] = (
        pd.Timestamp.now() - rfm_source['last_order']
    ).dt.days

    rfm_source['R'] = pd.qcut(
        rfm_source['recency'], 4, labels=[4, 3, 2, 1], duplicates='drop'
    )
    rfm_source['F'] = pd.qcut(
        rfm_source['frequency'].rank(method='first'), 4,
        labels=[1, 2, 3, 4], duplicates='drop'
    )
    rfm_source['M'] = pd.qcut(
        rfm_source['monetary'], 4, labels=[1, 2, 3, 4], duplicates='drop'
    )

    rfm_source['RFM_score'] = (
        rfm_source['R'].astype(str)
        + rfm_source['F'].astype(str)
        + rfm_source['M'].astype(str)
    )

    def segment_rfm(row):
        r, f, m = int(row['R']), int(row['F']), int(row['M'])
        if r >= 3 and f >= 3 and m >= 3:
            return 'VIP'
        if r >= 3 and f <= 2:
            return 'Новые перспективные'
        if r <= 2 and f >= 3:
            return 'Уходящие ценные'
        return 'Обычные'

    rfm_source['Сегмент'] = rfm_source.apply(segment_rfm, axis=1)
    rfm_df = (
        rfm_source.groupby('Сегмент')
        .agg(**{
            'Клиентов': ('customer_id', 'count'),
            'Средний чек, $': ('monetary', 'mean'),
        })
        .round(2)
        .reset_index()
    )
else:
    rfm_df = pd.DataFrame({'Сообщение': ['customer_id не найден в orders']})

# --- 4.11 Флаг "дорогой заказ" через np.where ---
orders['is_expensive'] = np.where(
    orders['total_cost'] > 10000, 'Да', 'Нет'
)

# --- 4.12 Мульти-статус через np.select ---
conditions = [
    orders['status'] == 'delivered',
    orders['status'] == 'cancelled',
    orders['status'].isin(['created', 'accepted', 'paid']),
]
choices = ['Успешно', 'Потерян', 'В процессе']
orders['outcome'] = np.select(conditions, choices, default='Прочее')

outcome_df = (
    orders.groupby('outcome')
    .agg(**{'Заказов': ('order_id', 'count')})
    .reset_index()
)
outcome_df['Доля, %'] = (
    outcome_df['Заказов'] / outcome_df['Заказов'].sum() * 100
).round(1)

# --- 4.13 concat — сводка по источникам ---
status_short = status_df[['Статус', 'Количество']].rename(
    columns={'Статус': 'Категория', 'Количество': 'Значение'}
)
status_short['Тип'] = 'Статус'

pay_short = pay_df[['Тип оплаты', 'Количество']].rename(
    columns={'Тип оплаты': 'Категория', 'Количество': 'Значение'}
)
pay_short['Тип'] = 'Оплата'

summary_categories = pd.concat(
    [status_short, pay_short], ignore_index=True
)

# --- Сводка KPI ---
kpi_df = pd.DataFrame({
    'Метрика': [
        'Всего заказов',
        'Доставлено',
        'Конверсия в доставку, %',
        'Отменено',
        'Доля отмен, %',
        'Общая выручка (delivered), $',
        'Средний чек (delivered), $',
        'Всего позиций в заказах',
        'Среднее позиций на заказ',
        'Уникальных товаров',
        'Уникальных городов',
        'Дорогих заказов (>10000), %',
    ],
    'Значение': [
        total_orders,
        len(delivered_orders),
        round(len(delivered_orders) / total_orders * 100, 1),
        len(orders[orders['status'] == 'cancelled']),
        round(len(orders[orders['status'] == 'cancelled']) / total_orders * 100, 1),
        round(delivered_revenue, 2),
        round(delivered_orders['total_cost'].mean(), 2),
        total_items,
        round(total_items / total_orders, 2),
        items['product'].nunique(),
        orders['city'].nunique(),
        round((orders['is_expensive'] == 'Да').mean() * 100, 1),
    ],
})

# --- Все метрики в словарь ---
metrics = {
    'KPI (сводка)': kpi_df,
    'Заказы по статусам': status_df,
    'Воронка конверсии': funnel_df,
    'Средний чек по доставке': avg_df,
    'Топ товаров': top_df,
    'Выручка по городам': city_df,
    'Типы оплаты': pay_df,
    'Динамика по дням': daily_df,
    'Pivot — города × месяцы': pivot_city_month,
    'Сегменты по чеку': segment_df,
    'RFM-сегменты клиентов': rfm_df,
    'Исходы заказов': outcome_df,
    'Категории (concat)': summary_categories,
}


# ============================================================
# 5. EXCEL
# ============================================================
def safe_sheet_name(name: str, max_len: int = 31) -> str:
    """Убирает запрещённые Excel символы (: \\ / ? * [ ]) и обрезает до 31 символа."""
    return re.sub(r'[:\\/?*\[\]]', '—', name)[:max_len]


out_dir = Path('reports')
out_dir.mkdir(exist_ok=True)
out_path = out_dir / 'report.xlsx'
with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
    for name, df in metrics.items():
        df.to_excel(writer, sheet_name=safe_sheet_name(name), index=False)
    orders.to_excel(writer, sheet_name='Все заказы', index=False)
    items.to_excel(writer, sheet_name='Все позиции', index=False)
    orders_items.head(1000).to_excel(
        writer, sheet_name='Заказы + позиции (1000)', index=False
    )
print("\n✅ Excel сохранён: report.xlsx")


# ============================================================
# 6. HTML — стилизация таблиц
# ============================================================
def styled(df, color):
    """Стилизует DataFrame для HTML-вывода."""
    return df.style.set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', color), ('color', 'white'),
            ('padding', '10px'), ('text-align', 'left'),
        ]},
        {'selector': 'td', 'props': [
            ('padding', '8px'), ('border-bottom', '1px solid #eee'),
        ]},
        {'selector': 'tr:hover', 'props': [('background-color', '#f5f5f5')]},
    ]).format(precision=2)


colors = [
    '#34495e', '#3498db', '#16a085', '#27ae60',
    '#e67e22', '#9b59b6', '#c0392b', '#7f8c8d',
]

cards = "".join(
    f'<div class="card"><h2>{name}</h2>'
    f'{styled(df, colors[i % len(colors)]).to_html()}</div>'
    for i, (name, df) in enumerate(metrics.items())
)


# ============================================================
# 7. ГРАФИКИ PLOTLY
# ============================================================
# 7.1 Выручка по городам
fig_city = px.bar(
    city_df, x='Город', y='Выручка, $',
    title='Выручка по городам',
    color='Выручка, $', color_continuous_scale='Blues',
    text='Доля выручки, %',
)
fig_city.update_traces(texttemplate='%{text}%', textposition='outside')

# 7.2 Статусы заказов
fig_status = px.pie(
    status_df, names='Статус', values='Количество',
    title='Распределение заказов по статусам',
    hole=0.4,
)

# 7.3 Воронка
fig_funnel = px.bar(
    funnel_df, x='Этап', y='Количество',
    title='Воронка конверсии заказов',
    color='Количество', color_continuous_scale='Greens',
    text='Конверсия от всех, %',
)
fig_funnel.update_traces(texttemplate='%{text}%', textposition='outside')

# 7.4 Сегменты по чеку
fig_segment = px.bar(
    segment_df, x='segment', y='Выручка, $',
    title='Выручка по сегментам чека',
    color='segment', text='Доля выручки, %',
)
fig_segment.update_traces(texttemplate='%{text}%', textposition='outside')

# 7.5 Динамика по дням
fig_daily = px.line(
    daily_df, x='Дата', y='Заказов',
    title='Динамика заказов по дням',
    markers=True,
)

charts = (
    fig_city.to_html(full_html=False, include_plotlyjs='cdn')
    + fig_status.to_html(full_html=False, include_plotlyjs=False)
    + fig_funnel.to_html(full_html=False, include_plotlyjs=False)
    + fig_segment.to_html(full_html=False, include_plotlyjs=False)
    + fig_daily.to_html(full_html=False, include_plotlyjs=False)
)


# ============================================================
# 8. СБОРКА HTML
# ============================================================
html = f"""<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8">
<title>Анализ заказов — megano</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 1200px;
         margin: 40px auto; padding: 0 20px; background: #fafafa; color: #333; }}
  h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
  h2 {{ color: #34495e; margin-top: 0; }}
  .card {{ background: white; border-radius: 8px; padding: 20px; margin: 20px 0;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  table {{ border-collapse: collapse; width: 100%; }}
  .kpi {{ display: inline-block; background: #3498db; color: white;
         padding: 10px 20px; border-radius: 6px; font-size: 16px; margin: 5px 5px 0 0; }}
</style></head><body>
  <h1>📊 Расширенный анализ заказов интернет-магазина</h1>
  <div>
    <span class="kpi">Всего заказов: {total_orders}</span>
    <span class="kpi">Конверсия в доставку: {round(len(delivered_orders)/total_orders*100,1)}%</span>
    <span class="kpi">Выручка (delivered): {round(delivered_revenue,2)} $</span>
    <span class="kpi">Средний чек: {round(delivered_orders['total_cost'].mean(),2)} $</span>
    <span class="kpi">Уникальных товаров: {items['product'].nunique()}</span>
    <span class="kpi">Городов: {orders['city'].nunique()}</span>
  </div>
  <div class="card">{charts}</div>
  {cards}
</body></html>"""

with open('reports/report.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ HTML сохранён: report.html")