# Databricks

Origem: `databricks auth profiles`, `databricks catalogs list`, `databricks schemas list` e `databricks volumes list`, executados em 2026-10-30.

## Acesso

- O projeto usa sempre o perfil **`pessoal`** do Databricks CLI: `-p pessoal` em todo comando.
- O perfil `DEFAULT` da máquina pertence a outro workspace e outra conta. Não usar e não alterar.
- Criar o perfil: `databricks auth login --host <url-do-workspace> --profile pessoal`. Se o navegador já tiver uma sessão do Databricks de outra conta, o login autoriza com ela; nesse caso, use uma janela anônima.
- O `--profile` não troca o host de um perfil existente: o CLI recusa o comando com "conflicts with --host".

## Catálogo

Todos os objetos do projeto ficam no catálogo **`lh_retail_analytics`** (Unity Catalog, gerenciado). Os outros catálogos do workspace (`demo_catalog`, `smart_claims_dev`, `lakehouse_vertice`, `workspace`) são de outros projetos e não devem ser tocados.

| Schema | Uso |
|---|---|
| `bronze` | Dados brutos como chegam da fonte |
| `silver` | Dados limpos e integrados |
| `gold` | Tabelas para consumo |
| `default` | Criado automaticamente; não usar |
| `information_schema` | Metadados do sistema |

## Volumes

| Volume | Tipo | Caminho |
|---|---|---|
| `bronze.raw` | Gerenciado | `/Volumes/lh_retail_analytics/bronze/raw`: os arquivos da fonte como chegaram |
| `bronze.files` | Gerenciado | `/Volumes/lh_retail_analytics/bronze/files`: o lago da bronze em Parquet, mais `_ingested_files` e `_quarantine` |
| `silver.files` | Gerenciado | `/Volumes/lh_retail_analytics/silver/files`: o lago da silver em Parquet, mais `_quarantine` e `_checks` |
| `gold.files` | Gerenciado | `/Volumes/lh_retail_analytics/gold/files`: o lago da gold em Parquet |

Os volumes `*.files` foram criados em 2026-10-30 com `databricks volumes create lh_retail_analytics <camada> files MANAGED -p pessoal`. As tabelas Delta de cada schema são publicadas a partir deles pelo job ([pipeline.md](pipeline.md)).

## SQL warehouse

- **Warehouse:** "Serverless Starter Warehouse" (2X-Small), usado pela tarefa `publish` do job.
- **Configuração:** o bundle encontra o ID pela variável `warehouse_id` (`lookup` pelo nome), então nenhum ID fica no repositório.

## Ferramentas do agente (aitools)

Origem: `databricks aitools install`, executado em 2026-10-30 com o CLI v1.22.1.

- **Instalação:** `databricks aitools install --scope project --agents claude-code --skills-only --skills databricks-core,databricks-dabs,databricks-jobs,databricks-pipelines,databricks-dbsql,databricks-python-sdk,databricks-serverless,databricks-data-discovery -p pessoal`.
- **Onde ficam:** as skills ficam em `.claude/skills/`, e o Claude Code as encontra sozinho. O CLI guarda uma cópia e o estado em `.databricks/aitools/`.
- **Por que `--skills-only`:** a instalação padrão, como plugin, roda `claude plugin marketplace update` e falha quando qualquer marketplace configurado não atualiza (no nosso caso, um marketplace sem relação com a Databricks).
- **Comandos úteis:** `databricks aitools list` mostra o que está instalado e `databricks aitools update` atualiza.

## Bundle

Origem: `databricks bundle init default-python` (2026-10-30), ajustado depois; `databricks bundle validate -p pessoal` retorna OK nos targets dev e prod.

O código do pipeline fica em um Declarative Automation Bundle (antigo Databricks Asset Bundle), na subpasta [`retail_analytics/`](../../retail_analytics/).

- **Ajustes em relação ao template:**
  - nome `retail_analytics`, no lugar de `my_project`;
  - catálogo `lh_retail_analytics` nos dois targets, no lugar de `workspace`;
  - exemplos removidos (pipeline e job de táxi, notebook e teste de exemplo).
- **Targets:**
  - `dev` é o padrão, em `mode: development`: o job ganha o prefixo `[dev usuário]` e o agendamento fica pausado;
  - `prod` usa o caminho do usuário (`root_path`);
  - os dois usam os schemas `bronze`, `silver` e `gold` de `lh_retail_analytics`. O `databricks.yml` só declara as variáveis `catalog` e `warehouse_id` (knowledge-refresh de 2026-10-30).
- **Sem host no arquivo:** o `databricks.yml` não traz URL do workspace nem e-mail. O workspace vem do perfil (`-p pessoal`), e o caminho e a permissão do prod usam `${workspace.current_user.userName}`.
- **Validação:** `databricks bundle validate -p pessoal`, dentro de `retail_analytics/`. Deploy e run só com o sim do engenheiro de dados.
