"""The schema module must match the contract it was generated from (contracts/rystore.odcs.yaml)."""

from pathlib import Path

import pytest

from retail_analytics import rystore_schema

yaml = pytest.importorskip("yaml")
CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "rystore.odcs.yaml"


@pytest.mark.skipif(not CONTRACT.exists(), reason="contract not available (outside the repository)")
def test_schema_matches_contract():
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert rystore_schema.CONTRACT_VERSION == contract["version"]
    for table in contract["schema"]:
        columns = [(p["name"], p["logicalType"], p["required"]) for p in table["properties"]]
        assert rystore_schema.COLUMNS[table["name"]] == columns
        keys = sorted((p for p in table["properties"] if p.get("primaryKey")), key=lambda p: p["primaryKeyPosition"])
        assert rystore_schema.PRIMARY_KEYS[table["name"]] == [p["name"] for p in keys]
