# Runbook: pipeline RYStore

Cada comando em ordem, como roda hoje (2026-10-30), conferido com `--help` sem gravar dado nem iniciar job (skill `docs`).

Regras de sempre:
- Use o perfil `pessoal` em todo comando `databricks` (`-p pessoal`). Nunca use o perfil `DEFAULT`.
- Use só o catálogo `lh_retail_analytics`.
- Os comandos `databricks bundle …` rodam dentro de `retail_analytics/`; os demais, na raiz do repositório.

O desenho do pipeline está em [`knowledge/architecture/pipeline.md`](../knowledge/architecture/pipeline.md), e o acesso ao Databricks em [`knowledge/architecture/databricks.md`](../knowledge/architecture/databricks.md).

## 0. Preparar a máquina (uma vez)

| Passo | Comando | Grava? |
|---|---|---|
| Dependências do projeto | `uv sync` | só o `.venv` local |
| Login no Databricks | `databricks auth login --host <url-do-workspace> --profile pessoal` | só o `~/.databrickscfg` |
| Credenciais do Supabase | copiar [`.env.example`](../.env.example) para `.env` e preencher | só o `.env` local, que nunca vai para o git |
| Credenciais no Databricks | `uv run python scripts/sync_secrets_to_databricks.py` | **sim**: cria o scope `retail_analytics` e grava as 4 chaves |
| Conferir as credenciais | `databricks secrets list-secrets retail_analytics -p pessoal` | não; mostra só os nomes |
| Volumes do lago | `databricks volumes create lh_retail_analytics <bronze\|silver\|gold> files MANAGED -p pessoal` | **sim**: já criados em 2026-10-30 |

> `sync_secrets_to_databricks.py` não tem `--help`: qualquer execução grava as credenciais.

## 1. Carregar a origem no Supabase

| Passo | Comando | Grava? |
|---|---|---|
| Ajuda | `uv run python scripts/load_rystore_to_supabase.py --help` | não |
| Carga dos CSVs no bucket `rystore` | `uv run python scripts/load_rystore_to_supabase.py` | **sim**: sobrescreve as mesmas chaves |
| Conferência do bucket com a fonte | `uv run python scripts/load_rystore_to_supabase.py --check` | não |

Esperado no `--check`: as 9 tabelas com `ok`, 737 arquivos e 59.052 linhas.

## 2. Testar e rodar localmente

| Passo | Comando | Grava? |
|---|---|---|
| Testes (dentro de `retail_analytics/`) | `uv run --no-project --with pytest --with pyyaml --with duckdb --with pyarrow pytest tests -q -p no:cacheprovider` | não |
| Pipeline local contra o Supabase | `uv run python -X utf8 scripts/run_pipeline_local.py --out <pasta fora do repo>` | só a pasta indicada |
| Pipeline local contra uma pasta | `uv run python -X utf8 scripts/run_pipeline_local.py --out <pasta> --source retail_analytics/fixtures/rystore/source` | só a pasta indicada |

Esperado: 31 testes aprovados. Contra o Supabase, 59.052 linhas na bronze, as 38 checagens aprovadas e 10.000 pedidos na gold.

> O `-X utf8` é necessário no Windows: sem ele, o `--help` do script quebra com `UnicodeEncodeError` (o "→" do texto de ajuda não existe no cp1252).

## 3. Deploy e execução no Databricks (dentro de `retail_analytics/`)

| Passo | Comando | Grava? |
|---|---|---|
| Conferir a configuração | `databricks bundle validate -p pessoal` | não |
| Ver os recursos implantados | `databricks bundle summary -p pessoal` | não |
| Deploy no dev | `databricks bundle deploy -p pessoal` | **sim**: arquivos e job no workspace |
| Rodar o job inteiro | `databricks bundle run rystore_pipeline -p pessoal --no-wait` | **sim**: inicia o job |
| Rodar só algumas tarefas | `databricks bundle run rystore_pipeline -p pessoal --only build_silver,build_gold,publish` | **sim** |
| Acompanhar as rodadas | `databricks jobs list-runs --job-id <id> -p pessoal` e `databricks jobs get-run <run_id> -p pessoal` | não |
| Ver o erro de uma tarefa | `databricks jobs get-run-output <task_run_id> -p pessoal` | não |

**As tarefas do job:**
1. `ingest_bronze`: arquivos novos ou alterados do bucket.
2. `build_silver`: tipos, quarentena, PII e checagens.
3. `build_gold`: o modelo dimensional.
4. `publish`: o Parquet vira tabela no Unity Catalog, em duas fases.

**Tempo e agendamento:** cerca de 9 minutos, dos quais mais ou menos 220 s montando o ambiente serverless. O agendamento é às 07:00 UTC; no dev fica pausado (`mode: development`).

O `<id>` do job aparece no `bundle summary`. No dev, ele não fica no repositório porque muda a cada workspace.

## 4. Reprocessar

| Situação | O que fazer |
|---|---|
| Uma checagem falhou e a causa foi corrigida no código | deploy, depois `bundle run rystore_pipeline --only build_silver,build_gold,publish`. A silver e a gold são sempre reconstruídas inteiras a partir da bronze |
| A fonte reenviou um arquivo corrigido | `bundle run rystore_pipeline`: o ETag mudou, então a bronze ingere o arquivo de novo e vale a última entrega |
| Reingerir um arquivo que **não** mudou | sem caminho suportado: a bronze pula todo par (chave, ETag) que já está em `_ingested_files`. Veja o [guia](guides/reprocessar-um-dia.md) |
| A `publish` falhou no meio | `bundle run rystore_pipeline --only publish`. As tabelas publicadas só são trocadas quando todas as stages ficam prontas |

## 5. Quando uma checagem falha

1. **Onde falhou.** O job falha na tarefa `build_silver` com `RuntimeError: Checagens com falha: <tabela>.<checagem> (<linhas>)`. Leia a mensagem com `jobs get-run-output`.
2. **O que os consumidores veem.** A `build_gold` e a `publish` não rodam, então as tabelas do Unity Catalog continuam na versão anterior. Os Parquet de `silver/files` já foram reescritos, e o resultado das checagens está em `silver/files/_checks`.
3. **Ler as checagens da rodada.** A tabela `silver._checks` só é atualizada pela `publish`, então leia direto do volume:
   ```sql
   SELECT * FROM parquet.`/Volumes/lh_retail_analytics/silver/files/_checks` WHERE status <> 'pass' ORDER BY run_at DESC
   ```
4. **Investigar.** Use a skill `incident` ([`llm/prompt_18.md`](../llm/prompt_18.md)) para chegar à causa raiz, aos rascunhos de e-mail e à entrada do [registro de incidentes](../knowledge/incidents/incident-log.md).
5. **Depois da correção.** Reprocesse como na seção 4 e confira com a skill `quality` ([`llm/prompt_11.md`](../llm/prompt_11.md)).

Uma entrega fora do contrato (coluna nova, arquivo vazio ou chave fora do layout) faz a `ingest_bronze` falhar **no fim**, depois de gravar o resto. Veja o [guia da quarentena](guides/conferir-a-quarentena.md).

## 6. Reconstruir o site de documentação (depois de cada release)

| Passo | Comando | Grava? |
|---|---|---|
| Ajuda | `uv run --with pyyaml python tools/site/build_site.py --help` | não |
| Gerar a partir do snapshot | `uv run --with pyyaml python tools/site/build_site.py` | só `docs/site/` |
| Ler o Databricks e gerar | `uv run --with pyyaml python tools/site/build_site.py --refresh` | só `docs/site/`; no Databricks, só leitura |

## Guias

- [Adicionar uma tabela da fonte](guides/adicionar-tabela-da-fonte.md)
- [Reprocessar um dia](guides/reprocessar-um-dia.md)
- [Conferir a quarentena](guides/conferir-a-quarentena.md)
- [Atualizar a página de produtos de dados](guides/atualizar-produtos-de-dados.md)

## Pontos em aberto achados ao escrever este runbook

- `scripts/run_pipeline_local.py --help` quebra no console do Windows sem `-X utf8`.
- `scripts/sync_secrets_to_databricks.py` e `docs/data-products/build_index.py` não tratam `--help`: rodam direto. O primeiro grava segredos.
- `rystore_schema.py` diz que é gerado do contrato, mas o gerador não está no repositório. Hoje ele é editado à mão, e o `test_schema.py` confere o resultado.
