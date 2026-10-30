"""Pytest setup: the package in src/ and the whole pipeline run once on the synthetic source.

Everything runs locally, without Databricks: the pipeline is plain Python and DuckDB.
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "rystore"


@pytest.fixture(scope="session")
def lake(tmp_path_factory):
    """Run bronze (twice), silver and gold on fixtures/rystore/source/ into a temporary lake.

    Returns the run summaries and `sql`, which runs a query where every lake table is a view
    named <layer>.<table> (for example silver.orders, bronze._quarantine).
    """
    duckdb = pytest.importorskip("duckdb")
    pytest.importorskip("pyarrow")
    from retail_analytics import bronze, gold, silver

    root = tmp_path_factory.mktemp("lake")
    dirs = {layer: root / layer for layer in ("raw", "bronze", "silver", "gold")}
    source = bronze.LocalSource(FIXTURES / "source")
    first = bronze.ingest(source, dirs["bronze"], datetime(2026, 1, 1, 7, 0), raw_dir=dirs["raw"])
    rerun = bronze.ingest(source, dirs["bronze"], datetime(2026, 1, 1, 8, 0))
    checks = silver.build(dirs["bronze"], dirs["silver"], datetime(2026, 1, 1, 7, 5))
    gold.build(dirs["silver"], dirs["gold"])

    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    for layer in ("bronze", "silver", "gold"):
        con.execute(f"CREATE SCHEMA {layer}")
        for folder in sorted(p for p in dirs[layer].iterdir() if p.is_dir()):
            con.execute(f'CREATE VIEW {layer}."{folder.name}" AS SELECT * FROM read_parquet(\'{folder.as_posix()}/*.parquet\')')
    return {"dirs": dirs, "first": first, "rerun": rerun, "checks": checks, "sql": lambda q: con.execute(q).fetchall()}
