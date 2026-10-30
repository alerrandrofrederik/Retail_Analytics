"""Tests of the bronze landing: the bucket layout, a second day, a run that died, and the retention.

Expected results: fixtures/rystore/expected_pipeline.json (layout, day2, crash, retention).
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

EXPECTED = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "rystore" / "expected_pipeline.json").read_text(encoding="utf-8"))
SOURCE = Path(__file__).resolve().parents[1] / "fixtures" / "rystore" / "source"

pytest.importorskip("duckdb")
pytest.importorskip("pyarrow")
from retail_analytics import bronze


class DictSource:
    """A source whose keys are given by the test (keys a folder cannot hold, such as ../)."""

    def __init__(self, files):
        self.files = files

    def list(self):
        return [(key, f'"{n}"') for n, key in enumerate(self.files)]

    def read(self, key):
        return self.files[key]


def test_only_keys_of_the_bucket_layout_are_read(tmp_path):
    body = (SOURCE / "customers" / "customers.csv").read_bytes()
    orders = (SOURCE / "orders" / "dt=2025-06-01" / "orders.csv").read_bytes()
    files = {key: orders if key.startswith("orders/") else body for key in EXPECTED["layout"]["keys"]}
    summary = bronze.ingest(DictSource(files), tmp_path / "bronze", datetime(2026, 1, 1), raw_dir=tmp_path / "raw")
    fatal = {line.split(": ")[0] for line in summary.fatal}
    expected = {key for key, outcome in EXPECTED["layout"]["keys"].items() if outcome == "fatal"}
    assert fatal == expected
    written = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*.csv")}
    assert written == {f"raw/{k}" for k, outcome in EXPECTED["layout"]["keys"].items() if outcome == "ok"}


def test_second_day(day2):
    expected = EXPECTED["day2"]
    assert day2["second"].files == expected["new_files"]
    assert day2["second"].fatal == expected["fatal"]
    for key, status in expected["log_status"].items():
        assert day2["sql"](f"SELECT status FROM bronze._ingested_files WHERE source_file = '{key}'") == [(status,)]
    for table, rows in expected["silver_rows"].items():
        assert day2["sql"](f"SELECT count(*) FROM silver.{table}")[0][0] == rows
    for order, status in expected["order_status"].items():
        assert day2["sql"](f"SELECT order_status FROM silver.orders WHERE order_id = '{order}'") == [(status,)]


def test_retention_of_full_snapshots(day2):
    files = {t: len(list((day2["dirs"]["bronze"] / t).glob("*.parquet"))) for t in EXPECTED["retention"]["files_after_day2"]}
    assert files == EXPECTED["retention"]["files_after_day2"]


def test_a_run_that_died_before_the_log_is_cleaned(tmp_path):
    lake = tmp_path / "bronze"
    bronze.ingest(bronze.LocalSource(SOURCE), lake, datetime(2026, 1, 1, 7, 0))
    first = next((lake / "orders").glob("*.parquet"))
    shutil.copyfile(first, lake / "orders" / "20260101T080000000000.parquet")  # rows of a run without log
    bronze.ingest(bronze.LocalSource(SOURCE), lake, datetime(2026, 1, 1, 9, 0))
    import pyarrow.parquet as pq

    rows = sum(pq.read_metadata(p).num_rows for p in (lake / "orders").glob("*.parquet"))
    assert rows == EXPECTED["crash"]["rows_after_rerun"]["orders"]
