"""Writing the Parquet of the lake from DuckDB, shared by silver and gold.

DuckDB writes a Parquet file out of order, which the /Volumes mount refuses at times (IO error,
2026-10-30, run 966981410696310): every file is written to a local temporary file and copied in one go.
"""

import shutil
import tempfile
from pathlib import Path


def copy(con, sql, target):
    """Write the result of `sql` as one Parquet file at `target`."""
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / "part.parquet"
        con.execute(f"COPY ({sql}) TO '{local.as_posix()}' (FORMAT parquet)")
        shutil.copyfile(local, target)


def write(con, sql, folder):
    """Replace a table of the lake: `folder` holds only part-0.parquet, the result of `sql`."""
    folder = Path(folder)
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    copy(con, sql, folder / "part-0.parquet")
