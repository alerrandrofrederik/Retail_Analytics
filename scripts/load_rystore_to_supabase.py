"""Carrega os CSVs da RYStore no Supabase Storage, no layout do contrato (contracts/rystore.odcs.yaml).

- orders e order_items: um arquivo por dia do pedido, em <tabela>/dt=yyyy-MM-dd/<tabela>.csv
  (o dia é a data de orders.order_datetime, hora local Europe/London).
- As demais tabelas: o arquivo completo em <tabela>/<tabela>.csv.

As linhas são copiadas byte a byte da fonte (CRLF, sem aspas); nada é reformatado. Rodar de novo
sobrescreve as mesmas chaves. As credenciais vêm do .env (modelo em .env.example) e nunca são impressas.

Uso, na raiz do repositório:
    uv run python scripts/load_rystore_to_supabase.py            # carrega e confere
    uv run python scripts/load_rystore_to_supabase.py --check    # só confere o que está no bucket
"""

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "RYStore-Retail-Dataset"
BUCKET = "rystore"
TABLES = ["customers", "employees", "inventory", "order_items", "orders", "products", "promotions", "stores", "suppliers"]
INCREMENTAL = {"orders", "order_items"}
EOL = b"\r\n"


def client():
    load_dotenv(ROOT / ".env")
    missing = [k for k in ("S3_ENDPOINT", "AWS_DEFAULT_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY") if not os.getenv(k)]
    if missing:
        sys.exit(f"Faltam variáveis no .env: {', '.join(missing)}")
    return boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT"],
        region_name=os.environ["AWS_DEFAULT_REGION"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )


def read_lines(table):
    """Cabeçalho e linhas de dados, como bytes, sem o fim de linha."""
    data = (SOURCE_DIR / f"{table}.csv").read_bytes()
    lines = data.split(EOL)
    if lines and lines[-1] == b"":
        lines.pop()
    return lines[0], lines[1:]


def files_to_write():
    """{chave no bucket: conteúdo} no layout do contrato."""
    files = {}
    order_header, order_rows = read_lines("orders")
    columns = order_header.decode("ascii").split(",")
    i_id, i_dt = columns.index("order_id"), columns.index("order_datetime")
    order_day = {}
    by_day = defaultdict(list)
    for row in order_rows:
        fields = row.decode("ascii").split(",")
        day = fields[i_dt][:10]
        order_day[fields[i_id]] = day
        by_day[day].append(row)
    for day, rows in by_day.items():
        files[f"orders/dt={day}/orders.csv"] = EOL.join([order_header, *rows]) + EOL

    item_header, item_rows = read_lines("order_items")
    i_order = item_header.decode("ascii").split(",").index("order_id")
    items_by_day = defaultdict(list)
    for row in item_rows:
        items_by_day[order_day[row.decode("ascii").split(",")[i_order]]].append(row)
    for day, rows in items_by_day.items():
        files[f"order_items/dt={day}/order_items.csv"] = EOL.join([item_header, *rows]) + EOL

    for table in TABLES:
        if table not in INCREMENTAL:
            files[f"{table}/{table}.csv"] = (SOURCE_DIR / f"{table}.csv").read_bytes()
    return files


def ensure_bucket(s3):
    try:
        s3.head_bucket(Bucket=BUCKET)
    except ClientError:
        s3.create_bucket(Bucket=BUCKET)
        print(f"Bucket criado: {BUCKET}")


def check(s3):
    """Lê de volta o bucket e compara as linhas por tabela com a fonte."""
    counts = defaultdict(int)
    keys = 0
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET):
        for obj in page.get("Contents", []):
            body = s3.get_object(Bucket=BUCKET, Key=obj["Key"])["Body"].read()
            counts[obj["Key"].split("/")[0]] += body.count(EOL) - 1
            keys += 1
    ok = True
    for table in TABLES:
        expected = len(read_lines(table)[1])
        status = "ok" if counts[table] == expected else "DIFERENTE"
        ok &= counts[table] == expected
        print(f"{table:12} bucket {counts[table]:>6}  fonte {expected:>6}  {status}")
    print(f"Arquivos no bucket: {keys}; linhas: {sum(counts.values())}")
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="só confere o bucket, sem carregar")
    args = parser.parse_args()
    s3 = client()
    if not args.check:
        ensure_bucket(s3)
        files = files_to_write()
        for key, body in sorted(files.items()):
            s3.put_object(Bucket=BUCKET, Key=key, Body=body, ContentType="text/csv")
        print(f"Arquivos gravados: {len(files)}")
    return 0 if check(s3) else 1


if __name__ == "__main__":
    sys.exit(main())
