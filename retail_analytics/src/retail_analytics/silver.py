"""Silver: the RYStore source clean, typed and integrated, with DuckDB (no Spark).

1. The current version: the latest delivery of each order (orders, order_items, incremental) and the
   latest snapshot of the other tables (full; a row that leaves the snapshot was deleted).
2. The types of the contract; order_datetime in local time (Europe/London) and in UTC.
3. Quarantine (_quarantine): a filled value that does not cast, and a foreign key without parent.
4. Personal data masked: names, e-mails and postcode in SHA-256; annual_salary does not leave bronze.
5. The rules of the contract and of the glossary as checks (_checks, appended): pass, warn or fail.

Reads the bronze lake (retail_analytics.bronze) and writes <silver>/<table>/part-0.parquet, replaced
on every run. Contract: contracts/rystore.odcs.yaml. Glossary: knowledge/business/glossary.md.
"""

import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import duckdb

from retail_analytics.rystore_schema import COLUMNS, FOREIGN_KEYS, LOAD, PRIMARY_KEYS, VALID_VALUES

TZ = "Europe/London"
PERSONAL = {
    "customers": ["first_name", "last_name", "email", "postcode_area"],
    "employees": ["first_name", "last_name"],
    "suppliers": ["email"],
}
DROPPED = {"employees": ["annual_salary"]}
PARENTS_FIRST = ["suppliers", "stores", "promotions", "customers", "products", "employees", "inventory",
                 "orders", "order_items"]
RULES = [
    ("orders", "total_formula", "fail",
     "SELECT count(*) FROM orders WHERE order_status <> 'Cancelled' AND "
     "abs(total_amount - (subtotal - discount_total + vat_total + delivery_fee)) > 0.01"),
    ("orders", "cancelled_total_zero", "fail", "SELECT count(*) FROM orders WHERE order_status = 'Cancelled' AND total_amount <> 0"),
    ("orders", "subtotal_is_gross", "fail",
     "SELECT count(*) FROM orders o JOIN (SELECT order_id, sum(quantity * unit_price) g FROM order_items GROUP BY order_id) i "
     "USING (order_id) WHERE abs(o.subtotal - i.g) > 0.01"),
    ("orders", "delivery_fee_rule", "warn",
     "SELECT count(*) FROM orders WHERE delivery_fee <> CASE WHEN order_channel = 'Online' AND subtotal < 40 THEN 3.49 ELSE 0 END"),
    ("order_items", "line_net_formula", "fail",
     "SELECT count(*) FROM order_items WHERE abs(line_net_amount - (quantity * unit_price - discount_amount)) > 0.01"),
    ("order_items", "amounts_not_negative", "fail",
     "SELECT count(*) FROM order_items WHERE quantity <= 0 OR unit_price < 0 OR discount_amount < 0 OR line_net_amount < 0 OR line_vat_amount < 0"),
    ("products", "price_positive", "fail", "SELECT count(*) FROM products WHERE unit_cost <= 0 OR unit_price <= 0 OR reorder_level < 0"),
    ("inventory", "stock_not_negative", "fail", "SELECT count(*) FROM inventory WHERE stock_on_hand < 0 OR stock_on_order < 0"),
    ("promotions", "dates_in_order", "fail", "SELECT count(*) FROM promotions WHERE start_date > end_date"),
]


@dataclass
class Check:
    table_name: str
    check_name: str
    status: str
    failed_rows: int


def _typed(name, logical):
    """The SQL that casts one text column of bronze to its contract type (NULL when it does not cast)."""
    column = f'"{name}"'
    if logical == "date":
        return f"CAST(try_strptime({column}, '%Y-%m-%d') AS DATE)"
    if logical == "timestamp":
        return f"try_strptime({column}, '%Y-%m-%d %H:%M:%S')"
    if logical == "boolean":
        return f"CASE {column} WHEN 'True' THEN true WHEN 'False' THEN false END"
    # Only the format of the contract casts: a cast alone would round 5.5 to 6 and 1.005 to 1.01.
    if logical == "integer":
        return f"CASE WHEN regexp_full_match({column}, '-?[0-9]+') THEN TRY_CAST({column} AS INTEGER) END"
    if logical == "number":
        return f"CASE WHEN regexp_full_match({column}, '-?[0-9]+([.][0-9]{{1,2}})?') THEN TRY_CAST({column} AS DECIMAL(12,2)) END"
    return column


def _masked(table, name):
    """The text of a column as quarantine may keep it: personal data hashed, as in the silver tables."""
    if name in PERSONAL.get(table, []):
        return f'sha256(lower(trim("{name}")))'
    return f'"{name}"'


def _current(table, files):
    """The current version of a bronze table: the latest delivery of each key, or the latest snapshot."""
    source = f"read_parquet('{files}')"
    if LOAD[table] == "changes":
        keys = ", ".join(PRIMARY_KEYS[table])
        return (f"SELECT * FROM {source} QUALIFY row_number() OVER "
                f"(PARTITION BY {keys} ORDER BY _ingested_at DESC, _source_file DESC) = 1")
    return f"SELECT * FROM {source} WHERE _ingested_at = (SELECT max(_ingested_at) FROM {source})"


def _utc(local):
    """Local time of Europe/London to UTC, as the contract says (open point 5): a time in the spring gap
    moves forward 1h (what DuckDB does by itself); of the repeated autumn hour, the first one (BST),
    which DuckDB does not pick by itself: one hour earlier is taken when it shows the same local time."""
    first = f"timezone('{TZ}', {local})"
    earlier = f"({first} - INTERVAL 1 HOUR)"
    return f"CASE WHEN timezone('{TZ}', {earlier}) = {local} THEN {earlier} ELSE {first} END"


def _copy(con, sql, target):
    """Write the result of `sql` as one Parquet file. DuckDB writes out of order, which the /Volumes mount
    refuses at times (IO error, 2026-10-30): it writes to a local temporary file, copied in one go."""
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / "part.parquet"
        con.execute(f"COPY ({sql}) TO '{local.as_posix()}' (FORMAT parquet)")
        shutil.copyfile(local, target)


def _write(con, sql, folder):
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    _copy(con, sql, folder / "part-0.parquet")


def build(bronze_dir, silver_dir, built_at: datetime) -> list[Check]:
    """Build every silver table from the bronze lake; return the checks (the caller fails on a 'fail')."""
    bronze_dir, silver_dir = Path(bronze_dir), Path(silver_dir)
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    con.execute("CREATE TABLE quarantine (table_name VARCHAR, source_file VARCHAR, line INTEGER, reason VARCHAR, raw VARCHAR)")

    for table, columns in COLUMNS.items():
        typed = ", ".join(f'{_typed(name, logical)} AS "{name}"' for name, logical, _ in columns)
        reason = ", ".join(f"""CASE WHEN "{name}" IS NOT NULL AND {_typed(name, logical)} IS NULL THEN 'cast:{name}' END"""
                           for name, logical, _ in columns)
        raw = ", ".join(f"'{name}', {_masked(table, name)}" for name, _, _ in columns
                        if name not in DROPPED.get(table, []))
        files = (bronze_dir / table).as_posix() + "/*.parquet"
        con.execute(f"""CREATE TABLE stage AS SELECT {typed}, _source_file, _line, _ingested_at,
                        coalesce({reason}) AS _reason, CAST(json_object({raw}) AS VARCHAR) AS _raw
                        FROM ({_current(table, files)})""")
        con.execute(f"INSERT INTO quarantine SELECT '{table}', _source_file, _line, _reason, _raw FROM stage WHERE _reason IS NOT NULL")
        con.execute(f"CREATE TABLE {table} AS SELECT * EXCLUDE (_reason) FROM stage WHERE _reason IS NULL")
        con.execute("DROP TABLE stage")

    # Foreign keys: parents first, so a child of a quarantined parent is quarantined too.
    for table in PARENTS_FIRST:
        for column, target in FOREIGN_KEYS.get(table, []):
            parent, parent_column = target.split(".")
            orphan = f"{column} IS NOT NULL AND {column} NOT IN (SELECT {parent_column} FROM {parent})"
            con.execute(f"INSERT INTO quarantine SELECT '{table}', _source_file, _line, 'orphan:{column}', _raw FROM {table} WHERE {orphan}")
            con.execute(f"DELETE FROM {table} WHERE {orphan}")

    con.execute(f"""CREATE OR REPLACE TABLE orders AS
                    SELECT * RENAME (order_datetime AS order_datetime_local),
                           {_utc('order_datetime')} AS order_datetime_utc,
                           CAST(order_datetime AS DATE) AS order_date
                    FROM orders""")
    for table, columns in PERSONAL.items():
        con.execute(f"UPDATE {table} SET " + ", ".join(f"{c} = sha256(lower(trim({c})))" for c in columns))
    for table, columns in DROPPED.items():
        for column in columns:
            con.execute(f"ALTER TABLE {table} DROP COLUMN {column}")

    built = f"timezone('UTC', TIMESTAMP '{built_at:%Y-%m-%d %H:%M:%S.%f}')"
    for table in COLUMNS:
        _write(con, f"SELECT * EXCLUDE (_line, _raw) RENAME (_ingested_at AS _bronze_ingested_at), {built} AS _silver_built_at "
                    f"FROM {table}", silver_dir / table)
    _write(con, f"SELECT *, {built} AS built_at FROM quarantine", silver_dir / "_quarantine")

    checks = list(RULES)
    for (table, column), values in VALID_VALUES.items():
        allowed = ", ".join("'" + v.replace("'", "''") + "'" for v in values)
        checks.append((table, f"valid_values:{column}", "warn", f"SELECT count(*) FROM {table} WHERE {column} NOT IN ({allowed})"))
    for table in COLUMNS:
        checks.append((table, "row_count", "fail", f"SELECT CASE WHEN count(*) = 0 THEN 1 ELSE 0 END FROM {table}"))
        checks.append((table, "quarantined_rows", "warn", f"SELECT count(*) FROM quarantine WHERE table_name = '{table}'"))
    results = []
    for table, name, level, sql in checks:
        failed = con.execute(sql).fetchone()[0]
        results.append(Check(table, name, "pass" if failed == 0 else level, int(failed)))

    folder = silver_dir / "_checks"
    folder.mkdir(parents=True, exist_ok=True)
    con.execute("CREATE TABLE checks (run_at TIMESTAMPTZ, table_name VARCHAR, check_name VARCHAR, status VARCHAR, failed_rows INTEGER)")
    con.executemany(f"INSERT INTO checks VALUES ({built}, ?, ?, ?, ?)",
                    [(c.table_name, c.check_name, c.status, c.failed_rows) for c in results])
    _copy(con, "SELECT * FROM checks", folder / f"{built_at:%Y%m%dT%H%M%S%f}.parquet")
    return results
