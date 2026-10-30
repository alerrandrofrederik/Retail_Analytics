"""Roda o pipeline da RYStore (bronze → silver → gold) nesta máquina, com o mesmo código do job do Databricks.

A fonte é o bucket `rystore` do Supabase Storage (credenciais do .env, nunca impressas) ou uma pasta no
layout do bucket (por exemplo retail_analytics/fixtures/rystore/source). O lago fica em --out, uma pasta
com raw/, bronze/, silver/ e gold/ em Parquet. Rodar de novo na mesma pasta só ingere arquivos novos.

Uso, na raiz do repositório:
    uv run python scripts/run_pipeline_local.py --out <pasta>                    # fonte: Supabase
    uv run python scripts/run_pipeline_local.py --out <pasta> --source <pasta>   # fonte: pasta local
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "retail_analytics" / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from retail_analytics import bronze, gold, silver


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # the help has non-ASCII text; a Windows console is cp1252
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, type=Path, help="pasta do lago (fora do repositório)")
    parser.add_argument("--source", type=Path, help="pasta no layout do bucket; sem ela, lê o Supabase")
    args = parser.parse_args()

    if args.source:
        source = bronze.LocalSource(args.source)
    else:
        from load_rystore_to_supabase import BUCKET, client
        source = bronze.S3Source(client(), BUCKET)

    now = datetime.now(UTC).replace(tzinfo=None)
    summary = bronze.ingest(source, args.out / "bronze", now, raw_dir=args.out / "raw")
    print(f"bronze: {summary.files} arquivos novos, {sum(summary.rows.values())} linhas, {summary.quarantined} em quarentena")
    for table, rows in sorted(summary.rows.items()):
        print(f"  {table:12} +{rows}")

    checks = silver.build(args.out / "bronze", args.out / "silver", now)
    for c in checks:
        if c.status != "pass":
            print(f"  {c.status:5} {c.table_name:12} {c.check_name:32} {c.failed_rows}")
    print(f"silver: {sum(c.status == 'pass' for c in checks)} de {len(checks)} checagens passaram")

    for table, rows in gold.build(args.out / "silver", args.out / "gold").items():
        print(f"gold.{table}: {rows} linhas")

    if summary.fatal:
        sys.exit("Entrega fora do contrato:\n" + "\n".join(summary.fatal))
    failed = [c for c in checks if c.status == "fail"]
    if failed:
        sys.exit("Checagens com falha: " + ", ".join(f"{c.table_name}.{c.check_name} ({c.failed_rows})" for c in failed))


if __name__ == "__main__":
    main()
