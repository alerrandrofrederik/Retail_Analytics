# Databricks notebook source
# MAGIC %md
# MAGIC # Silver: RYStore limpa, tipada e integrada
# MAGIC
# MAGIC 1. A versão vigente: o último envio de cada pedido (`orders`, `order_items`, incrementais) e a última
# MAGIC    foto das outras tabelas (completas; a linha que some da foto foi excluída).
# MAGIC 2. Os tipos do contrato; `order_datetime` em hora local (Europe/London) e em UTC.
# MAGIC 3. Quarentena (`silver._quarantine`): conversão de tipo que falha e chave estrangeira sem pai.
# MAGIC 4. PII mascarada: nomes, e-mails e postcode em SHA-256; `annual_salary` não sai da bronze.
# MAGIC 5. As regras do contrato e do glossário como checagens em `silver._checks` (pass, warn ou fail).
# MAGIC
# MAGIC Contrato: `contracts/rystore.odcs.yaml`. Glossário: `knowledge/business/glossary.md`.

# COMMAND ----------

import os
import sys
from datetime import datetime, timezone

from pyspark.sql import Window
from pyspark.sql import functions as F

sys.path.insert(0, os.path.abspath("."))
from retail_analytics.rystore_schema import COLUMNS, FOREIGN_KEYS, LOAD, PRIMARY_KEYS  # noqa: E402

dbutils.widgets.text("catalog", "lh_retail_analytics")
catalog = dbutils.widgets.get("catalog")
run_at = datetime.now(timezone.utc).replace(tzinfo=None)
TZ = "Europe/London"
PERSONAL = {
    "customers": ["first_name", "last_name", "email", "postcode_area"],
    "employees": ["first_name", "last_name"],
    "suppliers": ["email"],
}
DROPPED = {"employees": ["annual_salary"]}
CAST = {"string": None, "integer": "int", "number": "decimal(12,2)", "boolean": "boolean"}

# COMMAND ----------


def current(table):
    """The current version of a bronze table: the latest delivery of each key, or the latest snapshot."""
    df = spark.table(f"{catalog}.bronze.{table}")
    if LOAD[table] == "changes":
        w = Window.partitionBy(*PRIMARY_KEYS[table]).orderBy(F.col("_ingested_at").desc(), F.col("_source_file").desc())
        return df.withColumn("_rn", F.row_number().over(w)).filter("_rn = 1").drop("_rn")
    latest = df.agg(F.max("_ingested_at")).first()[0]
    return df.filter(F.col("_ingested_at") == latest)


def typed(table, df):
    """Cast every column to its contract type; rows where a filled value does not cast go to quarantine."""
    bad = F.lit(None).cast("string")
    for name, logical, _ in COLUMNS[table]:
        if logical == "date":
            value = F.to_date(name, "yyyy-MM-dd")
        elif logical == "timestamp":
            value = F.to_timestamp(name, "yyyy-MM-dd HH:mm:ss")
        elif logical == "boolean":
            value = F.when(F.col(name) == "True", True).when(F.col(name) == "False", False)
        elif CAST[logical]:
            value = F.col(name).cast(CAST[logical])
        else:
            value = F.col(name)
        bad = F.coalesce(bad, F.when(F.col(name).isNotNull() & value.isNull(), F.lit(f"cast:{name}")))
        df = df.withColumn(f"__{name}", value)
    df = df.withColumn("_reason", bad)
    for name, _, _ in COLUMNS[table]:
        df = df.drop(name).withColumnRenamed(f"__{name}", name)
    return df


quarantine = []


def to_quarantine(table, df):
    quarantine.append(df.select(
        F.lit(table).alias("table_name"), "_source_file", "_line", "_reason",
        F.to_json(F.struct(*[c for c, _, _ in COLUMNS[table]])).alias("raw")))


tables = {}
for table in COLUMNS:
    df = typed(table, current(table))
    to_quarantine(table, df.filter("_reason IS NOT NULL"))
    tables[table] = df.filter("_reason IS NULL").drop("_reason")

# Foreign keys: parents first, so a child of a quarantined parent is quarantined too.
for table in ["suppliers", "stores", "promotions", "customers", "products", "employees", "inventory", "orders", "order_items"]:
    df = tables[table]
    for column, target in FOREIGN_KEYS.get(table, []):
        parent, parent_col = target.split(".")
        keys = tables[parent].select(F.col(parent_col).alias("__key")).distinct()
        joined = df.join(keys, df[column] == keys["__key"], "left")
        orphan = F.col(column).isNotNull() & F.col("__key").isNull()
        to_quarantine(table, joined.filter(orphan).withColumn("_reason", F.lit(f"orphan:{column}")))
        df = joined.filter(~orphan).drop("__key")
    tables[table] = df

# COMMAND ----------

# Time zone (contract: Europe/London, no offset). to_utc_timestamp moves a time in the spring gap
# forward and takes the first (BST) of the repeated autumn hour, as the contract says.
tables["orders"] = (tables["orders"]
                    .withColumnRenamed("order_datetime", "order_datetime_local")
                    .withColumn("order_datetime_utc", F.to_utc_timestamp("order_datetime_local", TZ))
                    .withColumn("order_date", F.to_date("order_datetime_local")))

for table, columns in PERSONAL.items():
    for column in columns:
        tables[table] = tables[table].withColumn(column, F.sha2(F.lower(F.trim(column)), 256))
for table, columns in DROPPED.items():
    tables[table] = tables[table].drop(*columns)

for table, df in tables.items():
    (df.withColumnRenamed("_ingested_at", "_bronze_ingested_at")
       .drop("_line")
       .withColumn("_silver_built_at", F.lit(run_at).cast("timestamp"))
       .write.mode("overwrite").option("overwriteSchema", "true")
       .saveAsTable(f"{catalog}.silver.{table}"))
    print(f"silver.{table}: {spark.table(f'{catalog}.silver.{table}').count()} linhas")

q = quarantine[0]
for other in quarantine[1:]:
    q = q.unionByName(other)
(q.withColumnRenamed("_source_file", "source_file").withColumnRenamed("_line", "line")
  .withColumnRenamed("_reason", "reason").withColumn("built_at", F.lit(run_at).cast("timestamp"))
  .write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{catalog}.silver._quarantine"))
print(f"silver._quarantine: {spark.table(f'{catalog}.silver._quarantine').count()} linhas")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Checagens do contrato e do glossário
# MAGIC Cada uma conta as linhas que quebram a regra. `fail` quando a regra é de erro, `warn` quando o
# MAGIC contrato diz alerta (listas fechadas) ou quando a regra é de negócio sem quarentena.

# COMMAND ----------

s = f"{catalog}.silver"
VALID = {
    ("orders", "order_status"): ["Cancelled", "Completed", "Refunded"],
    ("orders", "order_channel"): ["Click & Collect", "In-store", "Online"],
    ("orders", "payment_method"): ["Card", "Cash", "Gift Card", "Mobile Wallet"],
    ("customers", "loyalty_tier"): ["Bronze", "Gold", "Platinum", "Silver"],
    ("promotions", "discount_type"): ["Fixed", "Percentage"],
    ("stores", "store_format"): ["Convenience", "Large Supermarket", "Medium Supermarket"],
}
checks = [
    ("orders", "total_formula", "fail",
     f"SELECT count(*) FROM {s}.orders WHERE order_status <> 'Cancelled' AND "
     "abs(total_amount - (subtotal - discount_total + vat_total + delivery_fee)) > 0.01"),
    ("orders", "cancelled_total_zero", "fail", f"SELECT count(*) FROM {s}.orders WHERE order_status = 'Cancelled' AND total_amount <> 0"),
    ("orders", "subtotal_is_gross", "fail",
     f"SELECT count(*) FROM {s}.orders o JOIN (SELECT order_id, sum(quantity * unit_price) g FROM {s}.order_items GROUP BY order_id) i "
     "USING (order_id) WHERE abs(o.subtotal - i.g) > 0.01"),
    ("orders", "delivery_fee_rule", "warn",
     f"SELECT count(*) FROM {s}.orders WHERE delivery_fee <> CASE WHEN order_channel = 'Online' AND subtotal < 40 THEN 3.49 ELSE 0 END"),
    ("order_items", "line_net_formula", "fail",
     f"SELECT count(*) FROM {s}.order_items WHERE abs(line_net_amount - (quantity * unit_price - discount_amount)) > 0.01"),
    ("order_items", "amounts_not_negative", "fail",
     f"SELECT count(*) FROM {s}.order_items WHERE quantity <= 0 OR unit_price < 0 OR discount_amount < 0 OR line_net_amount < 0 OR line_vat_amount < 0"),
    ("products", "price_positive", "fail", f"SELECT count(*) FROM {s}.products WHERE unit_cost <= 0 OR unit_price <= 0 OR reorder_level < 0"),
    ("inventory", "stock_not_negative", "fail", f"SELECT count(*) FROM {s}.inventory WHERE stock_on_hand < 0 OR stock_on_order < 0"),
    ("promotions", "dates_in_order", "fail", f"SELECT count(*) FROM {s}.promotions WHERE start_date > end_date"),
]
for (table, column), values in VALID.items():
    allowed = ", ".join("'" + v + "'" for v in values)
    checks.append((table, f"valid_values:{column}", "warn", f"SELECT count(*) FROM {s}.{table} WHERE {column} NOT IN ({allowed})"))
for table in COLUMNS:
    checks.append((table, "row_count", "fail", f"SELECT CASE WHEN count(*) = 0 THEN 1 ELSE 0 END FROM {s}.{table}"))
    checks.append((table, "quarantined_rows", "warn", f"SELECT count(*) FROM {s}._quarantine WHERE table_name = '{table}'"))

results = []
for table, name, level, sql in checks:
    failed = spark.sql(sql).first()[0]
    results.append((run_at, table, name, "pass" if failed == 0 else level, int(failed)))
(spark.createDataFrame(results, "run_at timestamp, table_name string, check_name string, status string, failed_rows int")
  .write.mode("append").saveAsTable(f"{catalog}.silver._checks"))
for r in results:
    print(f"{r[3]:5} {r[1]:12} {r[2]:32} {r[4]}")

failed = [r for r in results if r[3] == "fail"]
if failed:
    raise RuntimeError("Checagens com falha: " + ", ".join(f"{r[1]}.{r[2]} ({r[4]})" for r in failed))
