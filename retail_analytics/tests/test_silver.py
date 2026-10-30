"""Tests of bronze and silver on the synthetic source, against fixtures/rystore/expected_pipeline.json.

Runs locally, without Databricks:
uv run --no-project --with pytest --with pyyaml --with duckdb --with pyarrow pytest tests -p no:cacheprovider
"""

import hashlib
import json
from pathlib import Path

EXPECTED = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "rystore" / "expected_pipeline.json").read_text(encoding="utf-8"))


def _counts(lake, layer, tables):
    return {t: lake["sql"](f"SELECT count(*) FROM {layer}.{t}")[0][0] for t in tables}


def test_bronze_keeps_every_line(lake):
    expected = EXPECTED["bronze"]
    assert lake["first"].files == EXPECTED["source"]["files"]
    assert _counts(lake, "bronze", expected["rows"]) == expected["rows"]
    assert lake["sql"]("SELECT count(*) FROM bronze._quarantine")[0][0] == expected["quarantine"]
    assert (lake["dirs"]["raw"] / "orders" / "dt=2025-06-01" / "orders.csv").exists()


def test_bronze_rerun_ingests_nothing(lake):
    assert lake["rerun"].files == EXPECTED["bronze"]["rerun_new_files"]
    assert lake["sql"]("SELECT count(*) FROM bronze._ingested_files")[0][0] == EXPECTED["source"]["files"]


def test_silver_rows_and_quarantine(lake):
    expected = EXPECTED["silver"]
    assert _counts(lake, "silver", expected["rows"]) == expected["rows"]
    rows = lake["sql"]("SELECT table_name, line, reason FROM silver._quarantine ORDER BY line")
    assert [dict(zip(("table_name", "line", "reason"), r)) for r in rows] == expected["quarantine"]


def test_latest_version_of_an_order(lake):
    case = EXPECTED["silver"]["latest_version"]
    rows = lake["sql"](f"SELECT order_status FROM silver.orders WHERE order_id = '{case['order_id']}'")
    assert rows == [(case["order_status"],)]


def test_order_time_in_utc_follows_the_dst_rule(lake):
    expected = {k: v for k, v in EXPECTED["silver"]["utc"].items() if k.startswith("ORD")}
    rows = lake["sql"]("SELECT order_id, strftime(timezone('UTC', order_datetime_utc), '%Y-%m-%d %H:%M:%S') "
                       f"FROM silver.orders WHERE order_id IN ({', '.join(repr(k) for k in expected)})")
    assert dict(rows) == expected


def test_personal_data_is_hashed_or_dropped(lake):
    email = lake["sql"]("SELECT email FROM silver.suppliers")[0][0]
    assert email == hashlib.sha256(b"one@supplier.test").hexdigest()
    columns = [r[0] for r in lake["sql"]("SELECT column_name FROM (DESCRIBE silver.employees)")]
    assert "annual_salary" not in columns


def test_no_failed_check(lake):
    assert [c for c in lake["checks"] if c.status == "fail"] == EXPECTED["silver"]["failed_checks"]
    assert lake["sql"]("SELECT count(*) FROM silver._checks")[0][0] == len(lake["checks"])
