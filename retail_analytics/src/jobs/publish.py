"""Job task: publish the Parquet of the lake as Unity Catalog tables, through the SQL warehouse.

Every folder of /Volumes/<catalog>/<layer>/files becomes <catalog>.<layer>.<folder> (Delta, managed).
The Parquet is the truth; the table is what the consumers read.

Two phases, so a failure never leaves the layers half new and half old (run 966981410696310):
1. stage: every table is built as <layer>._stage_<folder> from its Parquet; any failure stops here,
   and the published tables are untouched;
2. swap: only then each published table is replaced from its stage (Delta to Delta, a quick copy),
   layer by layer, and the stages are dropped.
"""

import time

from _setup import arguments, lake
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

args = arguments("warehouse_id")
w = WorkspaceClient()
# timestampNtz: the local times (order_datetime_local) have no time zone, as in the contract.
PROPERTIES = "TBLPROPERTIES ('delta.feature.timestampNtz' = 'supported')"


def run(statement):
    response = w.statement_execution.execute_statement(warehouse_id=args.warehouse_id, statement=statement, wait_timeout="50s")
    while response.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(2)
        response = w.statement_execution.get_statement(response.statement_id)
    if response.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(f"{statement}\n{response.status.error}")
    return response


tables = [(layer, folder) for layer in ("bronze", "silver", "gold")
          for folder in sorted(p for p in lake(args.catalog, layer).iterdir() if p.is_dir())]


def name(layer, table):
    return f"`{args.catalog}`.`{layer}`.`{table}`"


for layer, folder in tables:
    run(f"CREATE OR REPLACE TABLE {name(layer, '_stage_' + folder.name)} {PROPERTIES} "
        f"AS SELECT * FROM parquet.`{folder.as_posix()}`")

for layer, folder in tables:
    stage = name(layer, "_stage_" + folder.name)
    run(f"CREATE OR REPLACE TABLE {name(layer, folder.name)} {PROPERTIES} AS SELECT * FROM {stage}")
    run(f"DROP TABLE {stage}")
    rows = run(f"SELECT count(*) FROM {name(layer, folder.name)}").result.data_array[0][0]
    print(f"{layer}.{folder.name}: {rows} linhas")
