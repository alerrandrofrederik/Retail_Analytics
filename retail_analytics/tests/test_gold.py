"""Tests of the gold model on the synthetic source, against fixtures/rystore/expected_pipeline.json."""

import json
from decimal import Decimal
from pathlib import Path

EXPECTED = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "rystore" / "expected_pipeline.json").read_text(encoding="utf-8"))["gold"]


def test_gold_rows(lake):
    counts = {t: lake["sql"](f"SELECT count(*) FROM gold.{t}")[0][0] for t in EXPECTED["rows"]}
    assert counts == EXPECTED["rows"]


def test_revenue_only_from_completed(lake):
    assert lake["sql"]("SELECT sum(revenue_amount) FROM gold.fato_pedidos")[0][0] == Decimal(EXPECTED["revenue_amount"])


def test_anonymous_orders_point_to_anon(lake):
    rows = lake["sql"]("SELECT order_id FROM gold.fato_pedidos WHERE customer_id = 'ANON' ORDER BY order_id")
    assert [r[0] for r in rows] == EXPECTED["anon_orders"]
    assert lake["sql"]("SELECT is_anonymous FROM gold.dim_cliente WHERE customer_id = 'ANON'") == [(True,)]


def test_calendar_keeps_spark_numbering(lake):
    case = EXPECTED["date_2025_06_01"]
    rows = lake["sql"]("SELECT day_of_week, is_weekend FROM gold.dim_data WHERE date_key = 20250601")
    assert rows == [(case["day_of_week"], case["is_weekend"])]
    gaps = lake["sql"]("SELECT count(*) FROM (SELECT \"date\" - lag(\"date\") OVER (ORDER BY \"date\") AS step "
                       "FROM gold.dim_data) WHERE step <> 1")
    assert gaps == [(0,)]


def test_stock_below_reorder(lake):
    rows = lake["sql"]("SELECT store_id, product_id FROM gold.fato_estoque WHERE below_reorder ORDER BY 1, 2")
    assert [list(r) for r in rows] == EXPECTED["below_reorder"]


def test_every_date_key_of_a_fact_is_in_the_calendar(lake):
    missing = lake["sql"]("""
        SELECT count(*) FROM (
            SELECT date_key AS k FROM gold.fato_pedidos UNION ALL SELECT date_key FROM gold.fato_vendas
            UNION ALL SELECT snapshot_date_key FROM gold.fato_estoque)
        WHERE k NOT IN (SELECT date_key FROM gold.dim_data)""")
    assert missing == [(0,)]
