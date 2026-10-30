# retail_analytics

O bundle do pipeline do projeto: um Declarative Automation Bundle criado com o template `default-python`, sem os exemplos. Ver [`knowledge/architecture/databricks.md`](../knowledge/architecture/databricks.md).

* `src/retail_analytics/`: código Python compartilhado pelos jobs e pipelines.
* `resources/`: definição dos recursos (jobs, pipelines), um `.yml` por recurso.
* `tests/`: testes do código.
* `fixtures/`: dados de teste.

Os targets `dev` (padrão) e `prod` usam o catálogo `lh_retail_analytics`. O workspace vem do perfil do CLI: rode sempre com `-p pessoal`.

```bash
uv sync --dev                                 # dependências locais
databricks bundle validate -p pessoal         # conferir a configuração
databricks bundle deploy -p pessoal           # deploy no dev (só com o sim do engenheiro de dados)
databricks bundle run <recurso> -p pessoal    # executar um job ou pipeline
uv run pytest                                 # testes
```
