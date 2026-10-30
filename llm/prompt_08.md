Construa a camada silver em lh_retail_analytics.silver, no bundle retail_analytics/.

Entradas: as tabelas bronze (prompt_07), o contrato (prompt_03), o glossário (knowledge/business/glossary.md) e as decisões do decision-log.

O que a silver faz: tipar as colunas (datas, decimais, booleanos), aplicar o fuso decidido para order_datetime, deduplicar pela chave primária, validar as chaves estrangeiras e aplicar as regras do glossário (subtotal bruto x line_net_amount líquido, total = subtotal - discount + vat + fee, Cancelled e Refunded conforme decidido). Linhas que quebram uma regra vão para quarentena com o motivo. Cada regra vira uma checagem com resultado registrado.

Se uma decisão do contrato ainda estiver em aberto, pare e pergunte: não escolha a regra por conta própria.

Use as skills databricks-pipelines/databricks-dbsql se o plano for Lakeflow ou SQL. Perfil pessoal, catálogo lh_retail_analytics, target dev, sim antes de deploy ou run.

Pré-requisito: prompt_07.

Saída: o código no bundle, os testes, o resultado das checagens e o glossário atualizado.
