"""Every silver check is tested with bad data: fixtures/rystore/source_bad/ has one bad row per rule and per
closed list, and the expected status of each check is in fixtures/rystore/expected_pipeline.json (checks_bad).
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rystore"
EXPECTED = json.loads((FIXTURES / "expected_pipeline.json").read_text(encoding="utf-8"))["checks_bad"]

pytest.importorskip("duckdb")
pytest.importorskip("pyarrow")
from retail_analytics import bronze, silver


def run(source, tmp_path):
    lake = tmp_path / "bronze"
    bronze.ingest(bronze.LocalSource(source), lake, datetime(2026, 1, 1, 7, 0))
    return silver.build(lake, tmp_path / "silver", datetime(2026, 1, 1, 7, 5))


def test_every_check_catches_its_bad_row(tmp_path):
    checks = run(FIXTURES / "source_bad", tmp_path)
    got = sorted((c.table_name, c.check_name, c.status, c.failed_rows) for c in checks if c.status != "pass")
    want = sorted((c["table_name"], c["check_name"], c["status"], c["failed_rows"]) for c in EXPECTED["not_pass"])
    assert got == want
    assert len(checks) == 38


def test_row_count_fails_when_every_row_is_quarantined(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(FIXTURES / "source_bad", source)
    (source / "employees" / "employees.csv").write_bytes(
        b"employee_id,first_name,last_name,store_id,role,hire_date,contract_type,annual_salary\r\n"
        b"EMP904,Gil,Test,ST901,Cashier,not-a-date,Full-time,18000\r\n")
    checks = run(source, tmp_path)
    want = EXPECTED["row_count_case"]["expected"]
    assert [vars(c) for c in checks if (c.table_name, c.check_name) == (want["table_name"], want["check_name"])] == [want]
