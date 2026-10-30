"""Job task: publish the Parquet of the lake as Unity Catalog tables, through the SQL warehouse.

Every folder of /Volumes/<catalog>/<layer>/files becomes <catalog>.<layer>.<folder> (Delta, managed),
replaced on every run. The Parquet is the truth; the table is what the consumers read.
"""

import time

from _setup import arguments, lake

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

args = arguments("warehouse_id")
w = WorkspaceClient()


def run(statement):
    response = w.statement_execution.execute_statement(warehouse_id=args.warehouse_id, statement=statement, wait_timeout="50s")
    while response.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(2)
        response = w.statement_execution.get_statement(response.statement_id)
    if response.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(f"{statement}\n{response.status.error}")
    return response


for layer in ("bronze", "silver", "gold"):
    for folder in sorted(p for p in lake(args.catalog, layer).iterdir() if p.is_dir()):
        table = f"`{args.catalog}`.`{layer}`.`{folder.name}`"
        # timestampNtz: the local times (order_datetime_local) have no time zone, as in the contract.
        run(f"CREATE OR REPLACE TABLE {table} TBLPROPERTIES ('delta.feature.timestampNtz' = 'supported') AS SELECT * FROM parquet.`{folder.as_posix()}`")
        rows = run(f"SELECT count(*) FROM {table}").result.data_array[0][0]
        print(f"{layer}.{folder.name}: {rows} linhas")
