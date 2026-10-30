# Guia: reprocessar um dia

O que "reprocessar" quer dizer depende da camada. O comportamento abaixo é o do código em 2026-10-30, em [`bronze.py`](../../retail_analytics/src/retail_analytics/bronze.py) e [`silver.py`](../../retail_analytics/src/retail_analytics/silver.py).

## Silver e gold: sempre inteiras

Toda rodada reconstrói a silver e a gold inteiras a partir da bronze. Para refazer um dia depois de corrigir o código, refaça tudo (dentro de `retail_analytics/`):

```bash
databricks bundle deploy -p pessoal
databricks bundle run rystore_pipeline -p pessoal --only build_silver,build_gold,publish
```

## Bronze: só o que mudou na fonte

A bronze ingere um arquivo só quando o par (chave, ETag) ainda não está em `bronze/files/_ingested_files`.

- **A fonte corrigiu `orders/dt=AAAA-MM-DD/orders.csv`.** Quando o dono da fonte sobe o arquivo de novo, o ETag muda. Rode o job inteiro (`databricks bundle run rystore_pipeline -p pessoal`): a bronze ingere o arquivo, e a silver fica com a última entrega de cada pedido.
- **Recarregar a origem a partir dos CSVs locais.** Rode `uv run python scripts/load_rystore_to_supabase.py`. A carga sobrescreve as chaves, mas, se o conteúdo for o mesmo, o ETag não muda e a bronze não ingere nada.
- **Reingerir um arquivo que não mudou:** não há caminho suportado. Seria preciso tirar a linha do arquivo do log (`_ingested_files`), que é Parquet, uma rodada por arquivo, sem ferramenta para isso. Pergunte ao engenheiro de dados antes de mexer no volume.

## Uma rodada que caiu no meio

Os arquivos de tabela sem log, que sobram quando uma rodada cai antes de gravar o log, são apagados no início da rodada seguinte. Basta rodar o job de novo.

## Retenção

As fotos das tabelas completas ficam 30 dias em `bronze/files`, e a mais recente nunca é apagada. Um dia de mais de 30 dias atrás só volta se a fonte entregar o arquivo de novo. Os arquivos brutos continuam em `/Volumes/lh_retail_analytics/bronze/raw/`.
