"""Job task: build silver from bronze (retail_analytics.silver); fails when a check fails."""

from datetime import UTC, datetime

from _setup import arguments, lake

from retail_analytics import silver

args = arguments()
checks = silver.build(lake(args.catalog, "bronze"), lake(args.catalog, "silver"), datetime.now(UTC).replace(tzinfo=None))
for c in checks:
    print(f"{c.status:5} {c.table_name:12} {c.check_name:32} {c.failed_rows}")
failed = [c for c in checks if c.status == "fail"]
if failed:
    raise RuntimeError("Checagens com falha: " + ", ".join(f"{c.table_name}.{c.check_name} ({c.failed_rows})" for c in failed))
