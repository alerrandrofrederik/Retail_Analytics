# Pipeline

Origem: definição do engenheiro de dados em 2026-10-30; [README do projeto](../../README.md); [databricks.md](databricks.md).

## Papéis

| Sistema | Papel |
|---|---|
| **Supabase (PostgreSQL)** | Banco OLTP da empresa (simulado). É o **sistema de origem**: os CSVs da [fonte RYStore](../sources/rystore.md) são carregados nele. |
| **Databricks** | **Plataforma de dados**, onde se constrói o lakehouse com a arquitetura medalhão, lendo os dados do Supabase. |

## Fluxo

```
CSVs RYStore ──▶ Supabase (OLTP) ──▶ Databricks: bronze ──▶ silver ──▶ gold ──▶ consumo
```

- **Supabase:** tabelas transacionais, uma por CSV.
- **Ingestão:** um notebook Python no Databricks lê o Supabase com `boto3`, pela API compatível com S3 do Supabase Storage, e grava no volume `bronze.raw`. As credenciais são as variáveis do `.env` (`S3_ENDPOINT`, `AWS_DEFAULT_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`; modelo em [`.env.example`](../../.env.example)), guardadas nos *secrets* do Databricks e nunca no notebook.
- **bronze:** cópia fiel do que vem do Supabase, sem regra de negócio.
- **silver:** dados limpos, tipados e integrados, com as regras do [glossário](../business/glossary.md).
- **gold:** modelo dimensional para consumo, com as dimensões `dim_produto`, `dim_cliente`, `dim_loja`, `dim_fornecedor` e `dim_data`, e as fatos `fato_vendas`, `fato_estoque` e `fato_pedidos`.
- **Consumo:** análise sobre a camada gold (o README cita o Chat Genie).

Os schemas e volumes estão em [databricks.md](databricks.md).

## Em aberto

- A frequência da ingestão (agendamento do job).
- O nome do *secret scope* e das chaves no Databricks.
- O `boto3` lê objetos do Supabase Storage (arquivos no bucket), não as tabelas do PostgreSQL. Falta confirmar se os dados ficam no Storage como arquivos exportados do OLTP.
- A carga é completa ou incremental? A fonte não tem data de alteração nem marca de exclusão. Ver o [registro de decisões](../decisions/decision-log.md).
