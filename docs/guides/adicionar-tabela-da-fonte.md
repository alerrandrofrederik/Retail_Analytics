# Guia: adicionar uma tabela da fonte

Quando a RYStore passar a entregar uma tabela nova, por exemplo `returns`. Os nomes e os caminhos abaixo são os do código em 2026-10-30.

1. **Contrato primeiro.** Combine a tabela com o dono da fonte e acrescente-a em [`contracts/rystore.odcs.yaml`](../../contracts/rystore.odcs.yaml), com colunas, tipos, chave, carga (`full` ou `changes`) e regras de qualidade. Suba a versão do contrato; uma tabela nova é uma mudança aditiva (skill `contract`).
2. **Esquema do código.** Gere [`rystore_schema.py`](../../retail_analytics/src/retail_analytics/rystore_schema.py) a partir do contrato, com `uv run --with pyyaml python scripts/generate_rystore_schema.py`. O gerador lê `COLUMNS`, as chaves, as chaves estrangeiras, a carga e as listas fechadas. Nunca edite o arquivo à mão: o `tests/test_schema.py` confere que ele é a saída do gerador.
3. **Silver.** Em [`silver.py`](../../retail_analytics/src/retail_analytics/silver.py):
   - acrescente a tabela em `PARENTS_FIRST`, depois dos pais dela;
   - acrescente em `PERSONAL` as colunas com `classification: restricted`;
   - acrescente em `DROPPED` o que não pode sair da bronze;
   - acrescente regras novas em `RULES`.
4. **Gold**, se for preciso: uma entrada nova em `TABLES` de [`gold.py`](../../retail_analytics/src/retail_analytics/gold.py).
5. **Carga da origem.** Acrescente a tabela em `TABLES` de [`load_rystore_to_supabase.py`](../../scripts/load_rystore_to_supabase.py). Se a carga for `changes`, inclua também a regra de partição por dia.
6. **Dados de teste antes do código** (skill `test-data`):
   - um arquivo da tabela em `retail_analytics/fixtures/rystore/source/<tabela>/`, com CRLF;
   - as contagens esperadas em `expected_pipeline.json`;
   - em seguida, rode os testes ([runbook, seção 2](../runbook.md#2-testar-e-rodar-localmente)).
7. **O que é automático.**
   - A bronze aceita qualquer tabela de `COLUMNS` cuja chave siga o layout do bucket.
   - A `publish` publica toda pasta nova dos volumes.
   - O Unity Catalog ganha `bronze.<tabela>` e `silver.<tabela>` sem mudar nada no job.
8. **Deploy e conferência.** Faça o deploy, rode o job ([runbook, seção 3](../runbook.md)) e confira as contagens com a skill `reconcile`.
9. **Conhecimento.** Atualize [`knowledge/sources/rystore.md`](../../knowledge/sources/rystore.md) e o [glossário](../../knowledge/business/glossary.md), se a tabela trouxer termos novos.
