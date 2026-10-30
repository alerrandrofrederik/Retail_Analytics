# Pipeline

Origem: definição do engenheiro de dados em 2026-10-30; [README do projeto](../../README.md); [databricks.md](databricks.md); [contrato RYStore](../../contracts/rystore.odcs.yaml) e o [registro de decisões](../decisions/decision-log.md) (prompt_04).

## Papéis

| Sistema | Papel |
|---|---|
| **Supabase** | Sistema de origem: o OLTP simulado da empresa. Entrega os dados como arquivos CSV no Storage, um por tabela. |
| **Databricks** | **Plataforma de dados**: o lakehouse em arquitetura medalhão, que lê os dados do Supabase. |

## Fluxo

```
CSVs RYStore ──▶ Supabase Storage (bucket rystore) ──▶ Databricks: bronze ──▶ silver ──▶ gold ──▶ consumo
```

- **Origem:** bucket `rystore` do Supabase Storage, lido pela API compatível com S3.
  - `orders` e `order_items` chegam em `<tabela>/dt=yyyy-MM-dd/<tabela>.csv`, um arquivo por dia com os pedidos do dia (incremental). Vale a última entrega de cada pedido.
  - As outras 7 tabelas chegam completas em `<tabela>/<tabela>.csv`. A linha que some da foto foi excluída.
  - Uma entrega por dia, até 06:00 UTC.
  - A carga dos CSVs no bucket é feita por [`scripts/load_rystore_to_supabase.py`](../../scripts/load_rystore_to_supabase.py) (`uv run python scripts/load_rystore_to_supabase.py`; `--check` só confere). Em 2026-10-30 ela gravou 737 arquivos (365 dias × 2 tabelas incrementais + 7 tabelas completas), com 59.052 linhas iguais às da fonte.
- **Motor:** Python puro, sem PySpark. As transformações usam DuckDB e pyarrow sobre Parquet nos volumes `<camada>.files` (decisão de 2026-10-30, no [registro de decisões](../decisions/decision-log.md)). O código fica em [`retail_analytics/src/retail_analytics/`](../../retail_analytics/src/retail_analytics/) (`bronze.py`, `silver.py`, `gold.py`). O mesmo código roda no job e nesta máquina ([`scripts/run_pipeline_local.py`](../../scripts/run_pipeline_local.py)).
- **Job `rystore_pipeline`:** serverless, com 4 tarefas `spark_python_task` que não usam o Spark.
  - `ingest_bronze`, `build_silver` e `build_gold` gravam Parquet nos volumes.
  - `publish` transforma cada pasta de `/Volumes/lh_retail_analytics/<camada>/files/` na tabela Delta `<camada>.<pasta>`, pelo SQL warehouse ("Serverless Starter Warehouse"). O Parquet é a verdade, e a tabela é a vitrine para os consumidores.
- **Ingestão:** a tarefa `ingest_bronze` lê o bucket com `boto3`, usando 8 downloads em paralelo. Copia cada arquivo como chegou para o volume `bronze.raw`, valida contra o contrato e grava as linhas como texto em `bronze/files/<tabela>/<carimbo>.parquet`.
  - Só entram os arquivos cujo par (chave, ETag) ainda não está em `bronze._ingested_files`.
  - As credenciais ficam no *secret scope* `retail_analytics`, nas chaves `s3_endpoint`, `aws_default_region`, `aws_access_key_id` e `aws_secret_access_key`. São as variáveis do `.env` (modelo em [`.env.example`](../../.env.example)) e nunca vão para o código.
  - O job roda uma vez por dia, às 07:00 UTC.
- **bronze:** cópia fiel do que vem do Supabase, sem regra de negócio, mais as colunas técnicas `_source_file`, `_line` e `_ingested_at`. As linhas rejeitadas vão para `bronze._quarantine`.
- **Horário de verão:** `order_datetime_utc` segue o contrato. O DuckDB 2.0 já avança 1h a hora inexistente da primavera, mas escolhe a segunda ocorrência (GMT) da hora repetida do outono. Por isso o código escolhe explicitamente a primeira (BST), com teste em `tests/test_silver.py`.
- **silver:** dados limpos, tipados e integrados, com as regras do [glossário](../business/glossary.md) e do contrato.
- **gold:** modelo dimensional para consumo:
  - dimensões `dim_produto`, `dim_cliente`, `dim_loja`, `dim_fornecedor` e `dim_data`;
  - fatos `fato_vendas`, `fato_estoque` e `fato_pedidos`.
- **Consumo:** análise sobre a camada gold (o README cita o Chat Genie).

## Lições da primeira execução sem Spark (2026-10-30)

Origem: rodada `966981410696310` do job no dev.

- **O DuckDB não grava direto em `/Volumes`.** O `COPY … TO '/Volumes/…'` falhou uma vez com "Async write failed … Input/output error", porque o DuckDB grava fora de ordem e o volume montado não aceita isso de forma confiável. Agora o DuckDB grava num arquivo temporário local, que é copiado inteiro para o volume (`silver._copy`). O pyarrow grava em sequência e não teve o problema na bronze.
- **Hora local vira `TIMESTAMP_NTZ`.** As colunas `order_datetime_local` (silver.orders e gold.fato_pedidos) não têm fuso. A tabela Delta precisa do recurso `timestampNtz`, que a `publish` habilita no `CREATE OR REPLACE`. Sem isso, substituir uma tabela que já existia falha com `DELTA_FEATURES_REQUIRE_MANUAL_ENABLEMENT`.

Os schemas e os volumes estão em [databricks.md](databricks.md).
