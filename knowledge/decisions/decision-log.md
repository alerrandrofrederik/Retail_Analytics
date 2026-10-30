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
| 2026-10-30 | A ingestão é um notebook Python no Databricks que lê o Supabase com `boto3`, com as credenciais do `.env` nos *secrets* do Databricks, e grava em `bronze.raw` | Engenheiro de dados, em conversa |
| 2026-10-30 | As tarefas do projeto viram prompts em ordem em `llm/prompt_NN.md`, com índice em [`llm/README.md`](../../llm/README.md); a skill `migration` fica de fora (não há ambiente legado) | Engenheiro de dados, ao aprovar o plano |
| 2026-10-30 | Skills da Databricks instaladas só no projeto, sem plugin: `databricks aitools install --scope project --agents claude-code --skills-only` com 8 skills, em `.claude/skills/`. O plugin falhou porque outro marketplace do Claude Code não atualizava | Engenheiro de dados, em conversa |
| 2026-10-30 | O código do pipeline fica em um Databricks Asset Bundle `default-python`, na subpasta `retail_analytics/`, com target dev | Engenheiro de dados, ao aprovar o plano |
| 2026-10-30 | Contrato RYStore 1.0.0 `active`: as 19 respostas da pauta (fuso Europe/London, receita só `Completed`, `employees` amostra, `hire_date` de transferência, vendas de madrugada válidas, entrega diária…) | Engenheiro de dados e decisões delegadas; ver a [pauta](../../contracts/rystore_open_points.md) |
| 2026-10-30 | A origem são arquivos CSV no Supabase Storage, bucket `rystore`: `orders` e `order_items` em `<tabela>/dt=yyyy-MM-dd/`, e as outras tabelas completas em `<tabela>/` | Engenheiro de dados (Storage); layout delegado |
| 2026-10-30 | Entrega diária: `orders`/`order_items` incrementais (vale a última entrega do pedido) e as demais tabelas completas; exclusão = linha que some da foto | Engenheiro de dados; detalhe delegado |
| 2026-10-30 | *Secret scope* `retail_analytics`, com as chaves `s3_endpoint`, `aws_default_region`, `aws_access_key_id` e `aws_secret_access_key` | Delegada (prompt_04) |
| 2026-10-30 | O job de ingestão roda uma vez por dia às 07:00 UTC, 1h depois da entrega | Delegada (prompt_04) |

## Em aberto

| Desde | Pergunta | Para quem | Origem |
|---|---|---|---|
| 2026-10-30 | Descrições reais das 77 colunas, para a próxima versão do contrato | Dono da fonte | [Pauta do contrato](../../contracts/rystore_open_points.md), ponto 16 |
