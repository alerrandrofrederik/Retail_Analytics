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


@pytest.mark.skipif(not CONTRACT.exists(), reason="contract not available (outside the repository)")
def test_valid_values_match_contract():
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    lists = {(t["name"], p["name"]): q["arguments"]["validValues"]
             for t in contract["schema"] for p in t["properties"] for q in p.get("quality") or []
             if (q.get("arguments") or {}).get("validValues")}
    assert rystore_schema.VALID_VALUES == lists


GENERATOR = Path(__file__).resolve().parents[2] / "scripts" / "generate_rystore_schema.py"


@pytest.mark.skipif(not GENERATOR.exists(), reason="generator not available (outside the repository)")
def test_schema_file_is_the_generator_output():
    import importlib.util

    spec = importlib.util.spec_from_file_location("generate_rystore_schema", GENERATOR)
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    expected = generator.render(yaml.safe_load(CONTRACT.read_text(encoding="utf-8")))
    assert Path(rystore_schema.__file__).read_text(encoding="utf-8") == expected
