# retail_analytics

O bundle do pipeline do projeto: um Declarative Automation Bundle criado com o template `default-python`, sem os exemplos. Ver [`knowledge/architecture/databricks.md`](../knowledge/architecture/databricks.md).

O pipeline roda em Python puro, sem PySpark: DuckDB e pyarrow sobre Parquet nos volumes `<camada>.files`.

* `src/retail_analytics/`: a lógica de cada camada (`bronze.py`, `silver.py` e `gold.py`), mais o esquema e a validação do contrato. Roda igual no job, nos testes e em `scripts/run_pipeline_local.py`.
* `src/jobs/`: as entradas finas das tarefas do job, mais `publish.py`, que publica o Parquet como tabelas do Unity Catalog pelo SQL warehouse.
* `resources/`: a definição dos recursos, um `.yml` por recurso. O job é `rystore_pipeline`.
* `tests/`: testes do código.
* `fixtures/`: dados de teste.

Os targets `dev` (padrão) e `prod` usam o catálogo `lh_retail_analytics`. O workspace vem do perfil do CLI: rode sempre com `-p pessoal`.

```bash
uv sync --dev                                 # dependências locais
databricks bundle validate -p pessoal         # conferir a configuração
databricks bundle deploy -p pessoal           # deploy no dev (só com o sim do engenheiro de dados)
databricks bundle run <recurso> -p pessoal    # executar um job ou pipeline
uv run --no-project --with pytest --with pyyaml --with duckdb --with pyarrow pytest tests -q   # testes, sem Databricks
```
