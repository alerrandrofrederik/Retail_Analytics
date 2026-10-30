"""Validation of one RYStore delivery file against the contract, before it lands in bronze.

Pure Python, so it runs in the notebooks and in the local tests alike. A file either stops
(fatal: schema drift or no rows) or is split into accepted rows and quarantined lines.
Values stay text; only the empty field becomes None (the null token of the contract).
"""

from dataclasses import dataclass, field

from retail_analytics.rystore_schema import COLUMNS, PRIMARY_KEYS

EOL = b"\r\n"


@dataclass
class Quarantined:
    line: int
    reason: str
    raw: str


@dataclass
class Result:
    rows: list = field(default_factory=list)
    quarantine: list = field(default_factory=list)
    fatal: str | None = None


def validate_delivery(table: str, data: bytes) -> Result:
    """Check one file of `table`: header, encoding, column count, required columns, unique key.

    Each accepted row is a dict of column -> text (None when empty), plus `_line`, the line number
    in the file (the header is line 1).
    """
    expected = [name for name, _, _ in COLUMNS[table]]
    required = [name for name, _, req in COLUMNS[table] if req]
    key = PRIMARY_KEYS[table]
    result = Result()

    lines = data.split(EOL)
    if lines and lines[-1] == b"":
        lines.pop()
    if not lines or lines[0].decode("ascii", errors="replace").split(",") != expected:
        result.fatal = "schema_drift" if lines else "no_rows"
        return result
    if len(lines) == 1:
        result.fatal = "no_rows"
        return result

    seen = set()
    for number, raw in enumerate(lines[1:], start=2):
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            result.quarantine.append(Quarantined(number, "encoding", raw.decode("ascii", errors="replace")))
            continue
        values = text.split(",")
        if len(values) != len(expected):
            result.quarantine.append(Quarantined(number, "column_count", text))
            continue
        row = {name: (value if value != "" else None) for name, value in zip(expected, values)}
        empty = next((name for name in required if row[name] is None), None)
        if empty:
            result.quarantine.append(Quarantined(number, f"required_empty:{empty}", text))
            continue
        pk = tuple(row[name] for name in key)
        if pk in seen:
            result.quarantine.append(Quarantined(number, "duplicate_key", text))
            continue
        seen.add(pk)
        row["_line"] = number
        result.rows.append(row)
    return result


def find_orphans(rows: list, column: str, parent_keys: set) -> tuple[list, list]:
    """Split rows into those whose `column` exists in `parent_keys` (or is empty) and the orphans."""
    kept, orphans = [], []
    for row in rows:
        value = row[column]
        if value is None or value in parent_keys:
            kept.append(row)
        else:
            raw = ",".join("" if row[k] is None else str(row[k]) for k in row if not k.startswith("_"))
            orphans.append(Quarantined(row["_line"], f"orphan:{column}", raw))
    return kept, orphans
