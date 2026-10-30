"""Copia as credenciais do Supabase Storage do .env para o secret scope do Databricks.

Scope `retail_analytics`, chaves em minúsculas (s3_endpoint, aws_default_region, aws_access_key_id,
aws_secret_access_key). Cada valor vai pela entrada padrão do CLI: nunca na linha de comando nem na tela.

Uso, na raiz do repositório:
    uv run python scripts/sync_secrets_to_databricks.py
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "pessoal"
SCOPE = "retail_analytics"
KEYS = ["S3_ENDPOINT", "AWS_DEFAULT_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]


def databricks(*args, value=None):
    return subprocess.run(["databricks", *args, "-p", PROFILE], input=value, capture_output=True, text=True, check=False)


def main():
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    load_dotenv(ROOT / ".env")
    missing = [k for k in KEYS if not os.getenv(k)]
    if missing:
        sys.exit(f"Faltam variáveis no .env: {', '.join(missing)}")
    scopes = databricks("secrets", "list-scopes", "-o", "json")
    if f'"{SCOPE}"' not in scopes.stdout:
        created = databricks("secrets", "create-scope", SCOPE)
        if created.returncode:
            sys.exit(f"Falha ao criar o scope {SCOPE}: {created.stderr.strip()}")
        print(f"Scope criado: {SCOPE}")
    for key in KEYS:
        put = databricks("secrets", "put-secret", SCOPE, key.lower(), value=os.environ[key])
        if put.returncode:
            sys.exit(f"Falha ao gravar {key.lower()}: {put.stderr.strip()}")
        print(f"Gravado: {SCOPE}/{key.lower()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
