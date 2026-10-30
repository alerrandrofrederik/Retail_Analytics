# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze: ingestão da fonte RYStore
# MAGIC
# MAGIC Lê o bucket `rystore` do Supabase Storage (API S3, credenciais do secret scope), copia cada arquivo
# MAGIC novo ou alterado para o volume `bronze.raw`, valida contra o contrato (`retail_analytics.validation`)
# MAGIC e grava as linhas como texto em `bronze.<tabela>`, com `_source_file`, `_line` e `_ingested_at`.
# MAGIC Linhas rejeitadas vão para `bronze._quarantine`; drift de esquema faz o job falhar no fim.
# MAGIC Contrato: `contracts/rystore.odcs.yaml`.

# COMMAND ----------

# MAGIC %pip install boto3==1.43.* --quiet

# COMMAND ----------

import os
import sys
from datetime import datetime, timezone

import boto3

sys.path.insert(0, os.path.abspath("."))
from retail_analytics.rystore_schema import COLUMNS  # noqa: E402
from retail_analytics.validation import validate_delivery  # noqa: E402

dbutils.widgets.text("catalog", "lh_retail_analytics")
dbutils.widgets.text("secret_scope", "retail_analytics")
dbutils.widgets.text("bucket", "rystore")
catalog = dbutils.widgets.get("catalog")
scope = dbutils.widgets.get("secret_scope")
bucket = dbutils.widgets.get("bucket")
volume = f"/Volumes/{catalog}/bronze/raw"
ingested_at = datetime.now(timezone.utc).replace(tzinfo=None)

# COMMAND ----------

s3 = boto3.client(
    "s3",
    endpoint_url=dbutils.secrets.get(scope, "s3_endpoint"),
    region_name=dbutils.secrets.get(scope, "aws_default_region"),
    aws_access_key_id=dbutils.secrets.get(scope, "aws_access_key_id"),
    aws_secret_access_key=dbutils.secrets.get(scope, "aws_secret_access_key"),
)

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {catalog}.bronze._ingested_files (
        source_file STRING, etag STRING, table_name STRING, rows INT, quarantined INT,
        status STRING, ingested_at TIMESTAMP)
""")
spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {catalog}.bronze._quarantine (
        table_name STRING, source_file STRING, line INT, reason STRING, raw STRING, ingested_at TIMESTAMP)
""")
done = {(r.source_file, r.etag) for r in spark.table(f"{catalog}.bronze._ingested_files").select("source_file", "etag").collect()}

objects = []
for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
    objects += [o for o in page.get("Contents", []) if (o["Key"], o["ETag"]) not in done]
print(f"Arquivos novos ou alterados: {len(objects)}")

# COMMAND ----------

rows_by_table = {t: [] for t in COLUMNS}
quarantine, log, fatal = [], [], []

for obj in sorted(objects, key=lambda o: o["Key"]):
    key, table = obj["Key"], obj["Key"].split("/")[0]
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    target = f"{volume}/{key}"
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "wb") as f:
        f.write(body)
    if table not in COLUMNS:
        fatal.append(f"{key}: tabela fora do contrato")
        log.append((key, obj["ETag"], table, 0, 0, "unknown_table", ingested_at))
        continue
    result = validate_delivery(table, body)
    if result.fatal:
        fatal.append(f"{key}: {result.fatal}")
    for row in result.rows:
        row["_source_file"] = key
    rows_by_table[table] += result.rows
    quarantine += [(table, key, q.line, q.reason, q.raw, ingested_at) for q in result.quarantine]
    log.append((key, obj["ETag"], table, len(result.rows), len(result.quarantine), result.fatal or "ok", ingested_at))

# COMMAND ----------

from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.types import IntegerType, StringType, StructField, StructType  # noqa: E402

for table, rows in rows_by_table.items():
    if not rows:
        continue
    names = [name for name, _, _ in COLUMNS[table]]
    schema = StructType([StructField(n, StringType()) for n in names]
                        + [StructField("_source_file", StringType()), StructField("_line", IntegerType())])
    df = spark.createDataFrame([tuple(r[n] for n in names) + (r["_source_file"], r["_line"]) for r in rows], schema)
    df.withColumn("_ingested_at", F.lit(ingested_at).cast("timestamp")) \
      .write.mode("append").option("mergeSchema", "false").saveAsTable(f"{catalog}.bronze.{table}")
    print(f"bronze.{table}: +{len(rows)} linhas")

if quarantine:
    spark.createDataFrame(quarantine, spark.table(f"{catalog}.bronze._quarantine").schema) \
        .write.mode("append").saveAsTable(f"{catalog}.bronze._quarantine")
if log:
    spark.createDataFrame(log, spark.table(f"{catalog}.bronze._ingested_files").schema) \
        .write.mode("append").saveAsTable(f"{catalog}.bronze._ingested_files")
print(f"Quarentena: {len(quarantine)} linhas; arquivos registrados: {len(log)}")

if fatal:
    raise RuntimeError("Entrega fora do contrato:\n" + "\n".join(fatal))
