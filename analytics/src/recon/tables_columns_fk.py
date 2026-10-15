import os
import re
from typing import Optional
import pandas as pd
from sqlalchemy.engine import Engine

# ============================================================
# 2. КАРТА ТАБЛИЦ
# Размер, строки, активность, структура, комментарий.
# Одна строка на таблицу.
# ============================================================

QUERY_TABLES_HEALTH = """
SELECT
    n.nspname                                              AS schema,
    c.relname                                              AS table_name,
    c.relkind                                              AS kind,

    -- размер: total = heap + toast + индексы
    pg_size_pretty(pg_total_relation_size(c.oid))          AS total_size,
    pg_size_pretty(pg_relation_size(c.oid))                AS heap_size,
    pg_size_pretty(pg_total_relation_size(c.oid)
                   - pg_relation_size(c.oid))              AS toast_idx_size,
    pg_total_relation_size(c.oid)                          AS total_bytes,

    -- строки: reltuples — оценка planner'а, n_live_tup — оценка stats.
    -- NULLIF(..., -1) превращает «никогда не анализировалась» в NULL.
    NULLIF(c.reltuples::bigint, -1)                        AS est_rows,
    s.n_live_tup                                           AS live_rows,
    s.n_dead_tup                                           AS dead_rows,
    ROUND(100.0 * s.n_dead_tup
          / NULLIF(s.n_live_tup + s.n_dead_tup, 0), 2)     AS dead_pct,

    -- активность: seq_scan + idx_scan — сколько раз таблицу читали
    s.seq_scan,
    s.idx_scan,
    ROUND(100.0 * s.idx_scan
          / NULLIF(s.seq_scan + s.idx_scan, 0), 2)         AS idx_hit_pct,

    -- свежесть статистики
    s.last_analyze,
    s.last_autoanalyze,
    s.last_vacuum,
    s.last_autovacuum,

    -- структура
    (SELECT count(*) FROM pg_attribute a
       WHERE a.attrelid = c.oid AND a.attnum > 0
         AND NOT a.attisdropped)                           AS n_columns,
    (SELECT count(*) FROM pg_index i
       WHERE i.indrelid = c.oid)                           AS n_indexes,
    -- n_unused_idx: индексы без сканов, ИСКЛЮЧАЯ PK и UNIQUE
    -- (PK и UNIQUE нужны для constraint, даже если их не читают)
    (SELECT count(*) FROM pg_stat_user_indexes si
       JOIN pg_index i ON i.indexrelid = si.indexrelid
       WHERE si.relid = c.oid
         AND si.idx_scan = 0
         AND NOT i.indisprimary
         AND NOT i.indisunique)                            AS n_unused_idx,
    (SELECT count(*) FROM pg_trigger t
       WHERE t.tgrelid = c.oid AND NOT t.tgisinternal)     AS n_triggers,
    (SELECT count(*) FROM pg_constraint k
       WHERE k.conrelid = c.oid AND k.contype = 'f')       AS n_fk_out,
    (SELECT count(*) FROM pg_constraint k
       WHERE k.confrelid = c.oid AND k.contype = 'f')      AS n_fk_in,

    obj_description(c.oid, 'pg_class')                     AS comment
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
  -- 'v' (views) исключены: у них нет файла и нет stats — только шум
  AND c.relkind IN ('r', 'p', 'm', 'f')
ORDER BY pg_total_relation_size(c.oid) DESC NULLS LAST;
"""


def recon_tables(engine: Engine) -> pd.DataFrame:
    """Слой 2: карточка всех таблиц."""
    return pd.read_sql(QUERY_TABLES_HEALTH, engine)





# ============================================================
# 3. КОЛОНКИ
# Типы, nullable, дефолты, PK/FK/UNIQUE, комментарии.
# Одна строка на колонку.
# ============================================================

QUERY_COLUMNS = """
SELECT
    n.nspname                             AS schema,
    c.relname                             AS table_name,
    a.attnum                              AS ordinal,
    a.attname                             AS column_name,
    format_type(a.atttypid, a.atttypmod)  AS data_type,
    NOT a.attnotnull                      AS is_nullable,
    pg_get_expr(d.adbin, d.adrelid)       AS default_value,
    CASE
        WHEN pk.conname IS NOT NULL THEN 'PK'
        WHEN uq.conname IS NOT NULL THEN 'UNIQUE'
        WHEN fk.conname IS NOT NULL
            THEN 'FK -> ' || fk.ref_table || '(' || fk.ref_col || ')'
        ELSE NULL
    END                                   AS key_role,
    col_description(c.oid, a.attnum)      AS comment
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid
LEFT JOIN pg_attrdef d
    ON d.adrelid = c.oid AND d.adnum = a.attnum
LEFT JOIN (
    SELECT conrelid, conname, unnest(conkey) AS attnum
    FROM pg_constraint WHERE contype = 'p'
) pk ON pk.conrelid = c.oid AND pk.attnum = a.attnum
LEFT JOIN (
    SELECT conrelid, conname, unnest(conkey) AS attnum
    FROM pg_constraint WHERE contype = 'u'
) uq ON uq.conrelid = c.oid AND uq.attnum = a.attnum
LEFT JOIN (
    -- только одно-колоночные FK: для составных нужен отдельный разбор
    SELECT
        k.conrelid, k.conname,
        k.conkey[1] AS attnum,
        rc.relname  AS ref_table,
        ra.attname  AS ref_col
    FROM pg_constraint k
    JOIN pg_class rc ON rc.oid = k.confrelid
    JOIN pg_attribute ra
        ON ra.attrelid = k.confrelid AND ra.attnum = k.confkey[1]
    WHERE k.contype = 'f' AND array_length(k.conkey, 1) = 1
) fk ON fk.conrelid = c.oid AND fk.attnum = a.attnum
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND c.relkind IN ('r', 'p', 'm')
  AND a.attnum > 0
  AND NOT a.attisdropped
ORDER BY n.nspname, c.relname, a.attnum;
"""


def recon_columns(engine: Engine) -> pd.DataFrame:
    """Слой 3: колонки, типы, ключи."""
    return pd.read_sql(QUERY_COLUMNS, engine)




# ============================================================
# 4. FK-ГРАФ
# Кто на кого ссылается. Одна строка на FK-колонку.
# ============================================================

QUERY_FOREIGN_KEYS = """
SELECT
    n_src.nspname                    AS src_schema,
    c_src.relname                    AS src_table,
    a_src.attname                    AS src_column,
    n_dst.nspname                    AS dst_schema,
    c_dst.relname                    AS dst_table,
    a_dst.attname                    AS dst_column,
    k.conname                        AS fk_name,
    CASE k.confdeltype
        WHEN 'a' THEN 'NO ACTION'
        WHEN 'r' THEN 'RESTRICT'
        WHEN 'c' THEN 'CASCADE'
        WHEN 'n' THEN 'SET NULL'
        WHEN 'd' THEN 'SET DEFAULT'
    END                              AS on_delete,
    CASE k.confupdtype
        WHEN 'a' THEN 'NO ACTION'
        WHEN 'r' THEN 'RESTRICT'
        WHEN 'c' THEN 'CASCADE'
        WHEN 'n' THEN 'SET NULL'
        WHEN 'd' THEN 'SET DEFAULT'
    END                              AS on_update
FROM pg_constraint k
JOIN pg_class c_src      ON c_src.oid = k.conrelid
JOIN pg_namespace n_src  ON n_src.oid = c_src.relnamespace
JOIN pg_class c_dst      ON c_dst.oid = k.confrelid
JOIN pg_namespace n_dst  ON n_dst.oid = c_dst.relnamespace
JOIN LATERAL unnest(k.conkey, k.confkey)
     AS cols(src_attnum, dst_attnum) ON true
JOIN pg_attribute a_src
    ON a_src.attrelid = c_src.oid AND a_src.attnum = cols.src_attnum
JOIN pg_attribute a_dst
    ON a_dst.attrelid = c_dst.oid AND a_dst.attnum = cols.dst_attnum
WHERE k.contype = 'f'
  AND n_src.nspname NOT IN ('pg_catalog', 'information_schema')
ORDER BY 1, 2, 3;
"""


def recon_foreign_keys(engine: Engine) -> pd.DataFrame:
    """Слой 4: FK-граф."""
    return pd.read_sql(QUERY_FOREIGN_KEYS, engine)

