Construa a ingestão da camada bronze no bundle retail_analytics/.

Use as skills do Databricks em .claude/skills (databricks-dabs, databricks-jobs, databricks-python-sdk) para seguir o padrão do bundle.

O notebook Python lê o Supabase com boto3 (decisão do prompt_04), com as credenciais lidas do secret scope via dbutils.secrets, nunca escritas no código. Ele grava os arquivos brutos no volume lh_retail_analytics.bronze.raw e cria as tabelas bronze em lh_retail_analytics.bronze: cópia fiel da origem, todas as colunas como texto, mais colunas técnicas (arquivo de origem, data da carga). A checagem de esquema contra o contrato para a carga quando houver drift, e os registros inválidos vão para quarentena.

O job do bundle roda no agendamento decidido no prompt_04. Os testes do prompt_06 precisam passar.

Regras: perfil pessoal (-p pessoal), catálogo lh_retail_analytics, só target dev. Mostre o plano antes; peça o sim antes de criar o secret scope e antes de qualquer bundle deploy ou run.

Pré-requisito: prompt_04, prompt_05 e prompt_06.

Saída: o código e o job no bundle, os testes passando, a contagem bronze x origem e knowledge/architecture/pipeline.md atualizado.
