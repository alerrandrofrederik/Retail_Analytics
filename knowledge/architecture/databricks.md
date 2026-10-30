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
| `bronze.raw` | Gerenciado | `/Volumes/lh_retail_analytics/bronze/raw` |
