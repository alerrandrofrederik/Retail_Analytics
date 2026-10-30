# Registro de decisões

Uma linha por decisão. Uma decisão em aberto passa para "tomada" quando o engenheiro de dados (ou o dono da fonte) responde, com a data e a origem da resposta.

## Tomadas

| Data | Decisão | Origem |
|---|---|---|
| 2026-10-30 | Usar sempre o perfil `pessoal` do Databricks CLI; nunca o `DEFAULT` | Engenheiro de dados, em conversa |
| 2026-10-30 | Todos os objetos do projeto ficam no catálogo `lh_retail_analytics` | Engenheiro de dados, em conversa |
| 2026-10-30 | As skills do projeto ficam em `skills/<nome>/SKILL.md` | Engenheiro de dados, em conversa |
| 2026-10-30 | Relatórios gerados ficam em `reports/<tipo>/`, em português | Engenheiro de dados, ao aprovar o plano do perfil |
| 2026-10-30 | O conhecimento do projeto fica em `knowledge/<assunto>/` | Engenheiro de dados, em conversa |
| 2026-10-30 | Supabase é o banco OLTP simulado da empresa (origem); Databricks é a plataforma de dados, com lakehouse em arquitetura medalhão que lê do Supabase | Engenheiro de dados, em conversa; ver [pipeline.md](../architecture/pipeline.md) |
| 2026-10-30 | A ingestão é um notebook Python no Databricks que lê o Supabase com `boto3`, com as credenciais do `.env` nos *secrets* do Databricks, e grava em `bronze.raw` (substituída em 2026-10-30 pelo pipeline em Python puro, sem PySpark; ver abaixo) | Engenheiro de dados, em conversa |
| 2026-10-30 | As tarefas do projeto viram prompts em ordem em `llm/prompt_NN.md`, com índice em [`llm/README.md`](../../llm/README.md); a skill `migration` fica de fora (não há ambiente legado) | Engenheiro de dados, ao aprovar o plano |
| 2026-10-30 | Skills da Databricks instaladas só no projeto, sem plugin: `databricks aitools install --scope project --agents claude-code --skills-only` com 8 skills, em `.claude/skills/`. O plugin falhou porque outro marketplace do Claude Code não atualizava | Engenheiro de dados, em conversa |
| 2026-10-30 | O código do pipeline fica em um Databricks Asset Bundle `default-python`, na subpasta `retail_analytics/`, com target dev | Engenheiro de dados, ao aprovar o plano |
| 2026-10-30 | Contrato RYStore 1.0.0 `active`: as 19 respostas da pauta (fuso Europe/London, receita só `Completed`, `employees` amostra, `hire_date` de transferência, vendas de madrugada válidas, entrega diária…) | Engenheiro de dados e decisões delegadas; ver a [pauta](../../contracts/rystore_open_points.md) |
| 2026-10-30 | A origem são arquivos CSV no Supabase Storage, bucket `rystore`: `orders` e `order_items` em `<tabela>/dt=yyyy-MM-dd/`, e as outras tabelas completas em `<tabela>/` | Engenheiro de dados (Storage); layout delegado |
| 2026-10-30 | Entrega diária: `orders`/`order_items` incrementais (vale a última entrega do pedido) e as demais tabelas completas; exclusão = linha que some da foto | Engenheiro de dados; detalhe delegado |
| 2026-10-30 | *Secret scope* `retail_analytics`, com as chaves `s3_endpoint`, `aws_default_region`, `aws_access_key_id` e `aws_secret_access_key` | Delegada (prompt_04) |
| 2026-10-30 | O job de ingestão roda uma vez por dia às 07:00 UTC, 1h depois da entrega | Delegada (prompt_04) |
| 2026-10-30 | Pipeline sem PySpark: Python puro com DuckDB e pyarrow, Parquet nos volumes `<camada>.files` e publicação no Unity Catalog pelo SQL warehouse. O mesmo código roda localmente, nos testes e no job serverless. Motivo: a primeira execução com Spark passou de 10 min só na bronze e foi abortada; com DuckDB, o pipeline inteiro roda em cerca de 23 s localmente | Engenheiro de dados (sem PySpark, no Databricks, com DuckDB); [incidente de 2026-10-30](../incidents/incident-log.md) |
| 2026-10-30 | Os volumes `bronze.files`, `silver.files` e `gold.files` são criados pelo CLI, como o `bronze.raw`, e não pelo bundle, para que o modo de desenvolvimento não mude os nomes | Delegada (refatoração sem PySpark) |
| 2026-10-30 | As decisões delegadas foram confirmadas: os pontos 6, 9 e 13 a 19 da pauta, a `inventory` completa, a PII em SHA-256 na silver e o `annual_salary` fora da silver e da gold | Engenheiro de dados, em conversa |
| 2026-10-30 | As fotos diárias das tabelas completas ficam 30 dias em `bronze/files`, e a mais recente nunca é apagada. Os arquivos brutos em `bronze.raw` ficam para sempre | Engenheiro de dados ([revisão 07 a 09](../../reports/pr-review/pr_review_pipeline_07_09.html), achado 10) |
| 2026-10-30 | A `gold.fato_estoque` guarda só a última foto do estoque, sem histórico | Engenheiro de dados ([revisão 07 a 09](../../reports/pr-review/pr_review_pipeline_07_09.html), achado 13, recusado) |
| 2026-10-30 | A bronze (tabelas e volume `bronze.raw`) fica sem restrição de acesso, porque o workspace é pessoal e tem um usuário só. A PII é mascarada a partir da silver, inclusive no JSON da quarentena. Rever se outra pessoa ganhar acesso ao workspace | Engenheiro de dados ([revisão 07 a 09](../../reports/pr-review/pr_review_pipeline_07_09.html), achado 2, parte recusada) |
| 2026-10-30 | Os CSVs ficam no git byte a byte (`.gitattributes`: `*.csv -text`), com CRLF como no contrato | Revisão 07 a 09, achado 4 |
| 2026-10-30 | SLA da gold: as tabelas gold ficam prontas até 08:00 UTC, 1h depois do início do job (07:00 UTC) | Engenheiro de dados, ao aprovar o plano do prompt 11 |
| 2026-10-30 | Criar a `gold.dim_promocao` (de `silver.promotions`), que junta com `fato_vendas.promotion_id`; o produto `fato_vendas` passa para a versão 1.1.0 | Engenheiro de dados |
| 2026-10-30 | O job ainda não vai para o prod: fica só o dev, pausado, sem custo recorrente. O SLA de 08:00 UTC segue sem ser cumprido até o deploy no prod | Engenheiro de dados |
| 2026-10-30 | `rystore_schema.py` é gerado do contrato por `scripts/generate_rystore_schema.py` e nunca editado à mão; o teste confere | Engenheiro de dados (correção dos pontos em aberto) |
| 2026-10-30 | Todas as 38 checagens da silver são testadas com dado ruim (`fixtures/rystore/source_bad/`) | Engenheiro de dados (correção dos pontos em aberto) |

## Em aberto

| Desde | Pergunta | Para quem | Origem |
|---|---|---|---|
| 2026-10-30 | Descrições reais das 77 colunas, para a próxima versão do contrato | Dono da fonte | [Pauta do contrato](../../contracts/rystore_open_points.md), pontos 16 e 21 |
| 2026-10-30 | A margem deve usar o custo do dia da venda? A fonte não entrega o histórico de `unit_cost` | Dono da fonte | [Pauta do contrato](../../contracts/rystore_open_points.md), ponto 20 |
| 2026-10-30 | Reativar o agendamento do job no prod, para cumprir o SLA de 08:00 UTC | Engenheiro de dados | [Qualidade 2026-10](../../reports/quality/rystore_quality_2026-10.html) |
