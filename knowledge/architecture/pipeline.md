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
- **Ingestão:** um notebook Python no Databricks lê o bucket com `boto3` e grava os arquivos no volume `bronze.raw`.
  - As credenciais ficam no *secret scope* `retail_analytics`, nas chaves `s3_endpoint`, `aws_default_region`, `aws_access_key_id` e `aws_secret_access_key`. São as variáveis do `.env` (modelo em [`.env.example`](../../.env.example)) e nunca vão para o código.
  - O job roda uma vez por dia, às 07:00 UTC.
- **bronze:** cópia fiel do que vem do Supabase, sem regra de negócio, mais as colunas técnicas.
- **silver:** dados limpos, tipados e integrados, com as regras do [glossário](../business/glossary.md) e do contrato.
- **gold:** modelo dimensional para consumo:
  - dimensões `dim_produto`, `dim_cliente`, `dim_loja`, `dim_fornecedor` e `dim_data`;
  - fatos `fato_vendas`, `fato_estoque` e `fato_pedidos`.
- **Consumo:** análise sobre a camada gold (o README cita o Chat Genie).

Os schemas e os volumes estão em [databricks.md](databricks.md).
