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
| [07](prompt_07.md) | Ingestão boto3 e camada bronze | — | 04, 05, 06 | Código pronto e no dev, **sem execução** (falta o secret scope) |
| [08](prompt_08.md) | Camada silver | — | 07 | Código pronto e no dev, **sem execução** (falta o secret scope) |
| [09](prompt_09.md) | Camada gold (modelo dimensional) | — | 08 | Código pronto e no dev, **sem execução** (falta o secret scope) |
| [10](prompt_10.md) | Revisão do código do pipeline | pr-review | 09 | Pendente |
| [11](prompt_11.md) | Qualidade das tabelas | quality | 09 rodando | Pendente |
| [12](prompt_12.md) | Reconciliação fonte x lakehouse | reconcile | 09 | Pendente |
| [13](prompt_13.md) | Impacto de uma mudança (ex.: fuso) | impact | 09 | Pendente |
| [14](prompt_14.md) | Produto de dados `fato_vendas` | data-product | 11, 12 | Pendente |
| [15](prompt_15.md) | Runbook e guias | docs | 07–09 | Pendente |
| [16](prompt_16.md) | Site de documentação | toolkit | 15 | Pendente |
| [17](prompt_17.md) | Atualização do knowledge | knowledge-refresh | 16 | Pendente |
| [18](prompt_18.md) | Modelo: incidente de job | incident | quando um job falhar | Modelo |
| [19](prompt_19.md) | Modelo: revisão geral e de custo | big-review, cost-review | 1 a 3 meses rodando | Modelo |

A skill `migration` não tem prompt: o projeto não tem ambiente legado (ver o [registro de decisões](../knowledge/decisions/decision-log.md)).

## Onde paramos (2026-10-30)

O pipeline (job `rystore_pipeline`: `ingest_bronze` → `build_silver` → `build_gold`) está no dev, mas nunca rodou: falta gravar as credenciais no *secret scope* `retail_analytics`. Para destravar, rode na raiz do repositório:

```bash
uv run python scripts/sync_secrets_to_databricks.py
```

Depois: rodar o job no dev (`databricks bundle run rystore_pipeline -p pessoal`, dentro de `retail_analytics/`), corrigir o que falhar, conferir a bronze, a silver e a gold contra a fonte, e seguir do prompt 10 ao 19.
