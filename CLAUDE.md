# Retail Analytics

## Databricks

- Sempre usar o perfil **`pessoal`** do Databricks CLI neste projeto: passe `-p pessoal` (ou `--profile pessoal`) em todo comando `databricks`.
- Nunca usar o perfil `DEFAULT`: ele pertence a outro workspace/conta.
- Sempre trabalhar no catálogo **`lh_retail_analytics`** do Unity Catalog. Criar schemas, tabelas, volumes e demais objetos do projeto dentro dele e nunca em outros catálogos do workspace.
