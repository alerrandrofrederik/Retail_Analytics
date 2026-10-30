"""Tests of the delivery validation of the RYStore source, against the expected results written first.

Fixtures and expected results: fixtures/rystore/ (synthetic rows, never real data; skill test-data).
Runs locally, without a cluster: uv run --no-project --with pytest --with pyyaml pytest tests -p no:cacheprovider
"""

import json
from pathlib import Path

import pytest

from retail_analytics.validation import find_orphans, validate_delivery

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rystore"
EXPECTED = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))


def _quarantine(result):
    return [{"line": q.line, "reason": q.reason} for q in result.quarantine]


@pytest.mark.parametrize("case", EXPECTED["cases"], ids=lambda c: c["file"])
def test_delivery(case):
    result = validate_delivery(case["table"], (FIXTURES / case["file"]).read_bytes())
    assert result.fatal == case["fatal"]
    assert len(result.rows) == case["accepted"]
    assert _quarantine(result) == case["quarantine"]


def test_rows_stay_text():
    result = validate_delivery("orders", (FIXTURES / "orders_clean.csv").read_bytes())
    first = result.rows[0]
    assert first["order_id"] == "ORD900001"
    assert first["subtotal"] == "10.0"
    assert result.rows[1]["customer_id"] is None


def test_orphans():
    case = EXPECTED["orphans"]
    parents = validate_delivery("orders", (FIXTURES / case["parent"]).read_bytes())
    children = validate_delivery("order_items", (FIXTURES / case["child"]).read_bytes())
    kept, quarantine = find_orphans(children.rows, "order_id", {r["order_id"] for r in parents.rows})
    assert len(kept) == case["accepted"]
    assert [{"line": q.line, "reason": q.reason} for q in quarantine] == case["quarantine"]
