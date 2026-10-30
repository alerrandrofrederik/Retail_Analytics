"""Bronze: land every new or changed delivery file of the RYStore source as Parquet, values kept as text.

Plain Python (pyarrow, no Spark), so the job and the local tests run the same code. The lake is a folder:
in the job, the volume /Volumes/<catalog>/bronze/files; locally, any folder.

    <lake>/<table>/<stamp>.parquet           accepted rows, all columns as text, plus _source_file, _line, _ingested_at
    <lake>/_quarantine/<stamp>.parquet       rejected lines (validation.validate_delivery)
    <lake>/_ingested_files/<stamp>.parquet   one row per file seen: key, ETag, rows, status

A file is new when its (key, ETag) is not yet in _ingested_files. Fatal files (schema drift, no rows)
are logged too, so they are not retried until the source sends them again with a new ETag.
"""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from retail_analytics.rystore_schema import COLUMNS
from retail_analytics.validation import validate_delivery

TIMESTAMP = pa.timestamp("us", tz="UTC")
LOG_SCHEMA = pa.schema([("source_file", pa.string()), ("etag", pa.string()), ("table_name", pa.string()),
                        ("rows", pa.int32()), ("quarantined", pa.int32()), ("status", pa.string()),
                        ("ingested_at", TIMESTAMP)])
QUARANTINE_SCHEMA = pa.schema([("table_name", pa.string()), ("source_file", pa.string()), ("line", pa.int32()),
                               ("reason", pa.string()), ("raw", pa.string()), ("ingested_at", TIMESTAMP)])


class LocalSource:
    """A folder in the bucket layout (<table>/.../<file>.csv); the ETag is the MD5 of the bytes, as in S3."""

    def __init__(self, root):
        self.root = Path(root)

    def list(self):
        files = sorted(p for p in self.root.rglob("*") if p.is_file())
        return [(p.relative_to(self.root).as_posix(), f'"{hashlib.md5(p.read_bytes()).hexdigest()}"') for p in files]

    def read(self, key):
        return (self.root / key).read_bytes()


class S3Source:
    """A bucket of the S3 API (the Supabase Storage of the source)."""

    def __init__(self, client, bucket):
        self.client, self.bucket = client, bucket

    def list(self):
        objects = []
        for page in self.client.get_paginator("list_objects_v2").paginate(Bucket=self.bucket):
            objects += [(o["Key"], o["ETag"]) for o in page.get("Contents", [])]
        return objects

    def read(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()


@dataclass
class Summary:
    files: int = 0
    rows: dict = field(default_factory=dict)
    quarantined: int = 0
    fatal: list = field(default_factory=list)


def ingested(lake):
    """The (key, ETag) pairs already in the log."""
    folder = Path(lake) / "_ingested_files"
    if not folder.exists():
        return set()
    done = set()
    for path in folder.glob("*.parquet"):
        log = pq.read_table(path, columns=["source_file", "etag"]).to_pydict()
        done.update(zip(log["source_file"], log["etag"]))
    return done


def _write(rows, schema, folder, stamp):
    folder.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows, schema), folder / f"{stamp}.parquet")


def ingest(source, lake, ingested_at: datetime, raw_dir=None, threads=8) -> Summary:
    """Land the new or changed files of `source` in `lake`; copy each file as it came to `raw_dir`, if given.

    `ingested_at` is the UTC time of the run (naive or aware). Returns a Summary; the caller decides what
    a fatal file means (the job fails at the end, after everything else has landed).
    """
    lake = Path(lake)
    stamp = ingested_at.strftime("%Y%m%dT%H%M%S%f")
    done = ingested(lake)
    todo = [(key, etag) for key, etag in source.list() if (key, etag) not in done]
    with ThreadPoolExecutor(max_workers=threads) as pool:
        bodies = list(pool.map(source.read, [key for key, _ in todo]))

    summary = Summary(files=len(todo))
    rows_by_table = {t: [] for t in COLUMNS}
    quarantine, log = [], []
    for (key, etag), body in zip(todo, bodies):
        if raw_dir is not None:
            target = Path(raw_dir) / key
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        table = key.split("/")[0]
        if table not in COLUMNS:
            summary.fatal.append(f"{key}: tabela fora do contrato")
            log.append(dict(source_file=key, etag=etag, table_name=table, rows=0, quarantined=0,
                            status="unknown_table", ingested_at=ingested_at))
            continue
        result = validate_delivery(table, body)
        if result.fatal:
            summary.fatal.append(f"{key}: {result.fatal}")
        for row in result.rows:
            row["_source_file"] = key
            row["_ingested_at"] = ingested_at
        rows_by_table[table] += result.rows
        quarantine += [dict(table_name=table, source_file=key, line=q.line, reason=q.reason, raw=q.raw,
                            ingested_at=ingested_at) for q in result.quarantine]
        log.append(dict(source_file=key, etag=etag, table_name=table, rows=len(result.rows),
                        quarantined=len(result.quarantine), status=result.fatal or "ok", ingested_at=ingested_at))

    for table, rows in rows_by_table.items():
        if rows:
            schema = pa.schema([(name, pa.string()) for name, _, _ in COLUMNS[table]]
                               + [("_source_file", pa.string()), ("_line", pa.int32()), ("_ingested_at", TIMESTAMP)])
            _write(rows, schema, lake / table, stamp)
            summary.rows[table] = len(rows)
    if quarantine or not (lake / "_quarantine").exists():  # an empty first file, so the table always exists
        _write(quarantine, QUARANTINE_SCHEMA, lake / "_quarantine", stamp)
    if log:
        _write(log, LOG_SCHEMA, lake / "_ingested_files", stamp)
    summary.quarantined = len(quarantine)
    return summary
