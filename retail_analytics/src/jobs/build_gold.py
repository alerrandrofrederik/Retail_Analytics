"""Job task: build gold from silver (retail_analytics.gold)."""

from _setup import arguments, lake

from retail_analytics import gold

args = arguments()
for table, rows in gold.build(lake(args.catalog, "silver"), lake(args.catalog, "gold")).items():
    print(f"gold.{table}: {rows} linhas")
