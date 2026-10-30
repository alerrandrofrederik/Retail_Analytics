"""Job task: land the new or changed files of the RYStore bucket in bronze (retail_analytics.bronze).

Credentials from the secret scope; the files as they came go to the volume bronze.raw, the rows as
Parquet to bronze.files. A delivery outside the contract fails the task at the end, after the rest landed.
"""

from datetime import UTC, datetime

import boto3
from _setup import arguments, lake
from databricks.sdk import WorkspaceClient

from retail_analytics import bronze

args = arguments("secret_scope", "bucket")
secrets = WorkspaceClient().dbutils.secrets
s3 = boto3.client(
    "s3",
    endpoint_url=secrets.get(args.secret_scope, "s3_endpoint"),
    region_name=secrets.get(args.secret_scope, "aws_default_region"),
    aws_access_key_id=secrets.get(args.secret_scope, "aws_access_key_id"),
    aws_secret_access_key=secrets.get(args.secret_scope, "aws_secret_access_key"),
)

summary = bronze.ingest(bronze.S3Source(s3, args.bucket), lake(args.catalog, "bronze"),
                        datetime.now(UTC).replace(tzinfo=None), raw_dir=lake(args.catalog, "bronze", "raw"))
print(f"Arquivos novos ou alterados: {summary.files}")
for table, rows in sorted(summary.rows.items()):
    print(f"bronze.{table}: +{rows} linhas")
print(f"Quarentena: {summary.quarantined} linhas")
if summary.fatal:
    raise RuntimeError("Entrega fora do contrato:\n" + "\n".join(summary.fatal))
