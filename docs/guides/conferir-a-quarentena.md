# Guia: conferir a quarentena

Uma linha que quebra o contrato não entra na tabela: vai para a quarentena, com o motivo. Há duas quarentenas.

| Onde | Motivos | Escrita por |
|---|---|---|
| `bronze._quarantine` (`bronze/files/_quarantine/`) | `encoding`, `column_count`, `required_empty:<coluna>`, `duplicate_key` | [`validation.py`](../../retail_analytics/src/retail_analytics/validation.py), na leitura do arquivo |
| `silver._quarantine` (`silver/files/_quarantine/`) | `cast:<coluna>` (valor fora do formato do contrato) e `orphan:<coluna>` (chave estrangeira sem pai) | [`silver.py`](../../retail_analytics/src/retail_analytics/silver.py) |

Uma entrega inteira fora do contrato (`schema_drift`, `no_rows`, `unknown_key`) não gera linhas de quarentena. Ela fica em `bronze._ingested_files`, com o status, e faz a `ingest_bronze` falhar no fim.

## Consultas (warehouse ou Catalog Explorer)

```sql
-- linhas em quarentena da última publicação, por tabela e motivo
SELECT table_name, reason, count(*) FROM lh_retail_analytics.silver._quarantine GROUP BY ALL ORDER BY 3 DESC;
SELECT table_name, reason, count(*) FROM lh_retail_analytics.bronze._quarantine GROUP BY ALL ORDER BY 3 DESC;

-- entregas paradas inteiras
SELECT source_file, status, ingested_at FROM lh_retail_analytics.bronze._ingested_files WHERE status <> 'ok';

-- a rodada mais recente, mesmo que a publish não tenha rodado (direto do volume)
SELECT * FROM parquet.`/Volumes/lh_retail_analytics/silver/files/_quarantine`;
```

## O que olhar

- **O campo `raw`:** a linha como chegou. Na silver, as colunas pessoais aparecem em SHA-256 e o `annual_salary` não aparece.
- **O tamanho do problema:** a checagem `quarantined_rows` vira `warn` quando uma tabela tem linhas em quarentena. Ela não para o job.
- **Liberar uma linha:** não existe. A linha volta quando a fonte reenviar o arquivo corrigido ([reprocessar um dia](reprocessar-um-dia.md)).
- **Investigar:** use a skill `quality` ([`llm/prompt_11.md`](../../llm/prompt_11.md)).
