# Prompts de execução

Um prompt por tarefa do projeto, em ordem de dependência. Cada um diz qual skill de [`skills/`](../skills/) usar (quando houver), o que ler, o pré-requisito e a saída esperada. Rode um de cada vez e só passe ao próximo com o anterior concluído.

Antes do 05: preparação do ambiente (skills da Databricks em `.claude/skills/` com `databricks aitools install --skills-only`, e o bundle `retail_analytics/` criado com `databricks bundle init default-python`).

| # | Tarefa | Skill | Pré-requisito | Status |
|---|---|---|---|---|
| [01](prompt_01.md) | Perfil da fonte RYStore | profile | — | Concluído ([relatório](../reports/profile/rystore_profile.html)) |
| [02](prompt_02.md) | Metadata da RYStore | metadata | 01 | Concluído ([metadata](../metadata/rystore.yaml)) |
| [03](prompt_03.md) | Contrato de dados com a fonte | contract | 02 | Concluído, 1.0.0 ([contrato](../contracts/rystore.odcs.yaml), [pauta](../contracts/rystore_open_points.md)) |
| [04](prompt_04.md) | Decisões de arquitetura em aberto | — | 03 | Concluído ([decisões](../knowledge/decisions/decision-log.md)) |
| [05](prompt_05.md) | Carga dos CSVs no Supabase (origem) | — | 04 | Concluído ([script](../scripts/load_rystore_to_supabase.py)) |
| [06](prompt_06.md) | Dados de teste da ingestão e da bronze | test-data | 02, 03 | Concluído ([fixtures](../retail_analytics/fixtures/rystore/expected.json)) |
| [07](prompt_07.md) | Ingestão boto3 e camada bronze | — | 04, 05, 06 | Concluído (Python puro com DuckDB, sem PySpark; rodada 173663739566769 no dev) |
| [08](prompt_08.md) | Camada silver | — | 07 | Concluído (Python puro com DuckDB, sem PySpark; rodada 173663739566769 no dev) |
| [09](prompt_09.md) | Camada gold (modelo dimensional) | — | 08 | Concluído (Python puro com DuckDB, sem PySpark; rodada 173663739566769 no dev) |
| [10](prompt_10.md) | Revisão do código do pipeline | pr-review | 09 | Concluído ([revisão](../reports/pr-review/pr_review_pipeline_07_09.html): 16 achados; 1 a 9 corrigidos, 10 e 13 decididos; rodada 498752805931100) |
| [11](prompt_11.md) | Qualidade das tabelas | quality | 09 rodando | Concluído ([qualidade 2026-10](../reports/quality/rystore_quality_2026-10.html)) |
| [12](prompt_12.md) | Reconciliação fonte x lakehouse | reconcile | 09 | Concluído ([reconciliação](../reports/reconcile/rystore_reconcile_2026-10-30.html): diferença zero) |
| [13](prompt_13.md) | Impacto de uma mudança (ex.: fuso) | impact | 09 | Concluído ([impacto: order_datetime em UTC](../reports/impact/rystore_impact_order_datetime_utc.html)) |
| [14](prompt_14.md) | Produto de dados `fato_vendas` | data-product | 11, 12 | Concluído ([produto](../docs/data-products/fato_vendas/README.md), [página](../docs/data-products/index.html)) |
| [15](prompt_15.md) | Runbook e guias | docs | 07–09 | Concluído ([runbook](../docs/runbook.md), 4 [guias](../docs/guides/)) |
| [16](prompt_16.md) | Site de documentação | toolkit | 15 | Concluído ([site](../docs/site/index.html), gerador [`tools/site/build_site.py`](../tools/site/build_site.py)) |
| [17](prompt_17.md) | Atualização do knowledge | knowledge-refresh | 16 | Pendente |
| [18](prompt_18.md) | Modelo: incidente de job | incident | quando um job falhar | Modelo |
| [19](prompt_19.md) | Modelo: revisão geral e de custo | big-review, cost-review | 1 a 3 meses rodando | Modelo |

A skill `migration` não tem prompt: o projeto não tem ambiente legado (ver o [registro de decisões](../knowledge/decisions/decision-log.md)).

## Onde paramos (2026-10-30)

O pipeline roda no dev em Python puro, sem PySpark: DuckDB e pyarrow sobre Parquet nos volumes `<camada>.files`, publicado no Unity Catalog pelo SQL warehouse. Detalhes em [`knowledge/architecture/pipeline.md`](../knowledge/architecture/pipeline.md).

- **Rodada `173663739566769`:** SUCCESS nas 4 tarefas.
  - As contagens batem com a fonte: 59.052 linhas na bronze, 0 em quarentena e 33 de 33 checagens aprovadas.
  - Foi a segunda carga, e a bronze ingeriu 0 arquivos, como esperado.
- **Executar localmente:** `uv run python scripts/run_pipeline_local.py --out <pasta>`. Roda o mesmo código em cerca de 23 s.
- **Testes:** dentro de `retail_analytics/`, `uv run --no-project --with pytest --with pyyaml --with duckdb --with pyarrow pytest tests -q`, com 24 testes.

Os achados 1 a 9 da [revisão](../reports/pr-review/pr_review_pipeline_07_09.html) foram corrigidos (31 testes; rodada `498752805931100` com SUCCESS). Continuam abertos o achado 11 (a montagem do ambiente leva cerca de 220 s) e os baixos, de 12 a 16. O prompt 11 (qualidade) também está concluído: os dados estão certos, a gold está "usar com cuidado" porque não tem rodada agendada e passou do SLA, e nenhuma das 38 checagens tem um teste que confira o status com dado ruim. O prompt 12 (reconciliação) deu diferença zero em todos os pares; a armadilha do fuso (agrupar em UTC) ficou registrada no glossário. Próximo passo: prompts 13 a 19.
