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

## Em aberto

| Desde | Pergunta | Para quem | Origem |
|---|---|---|---|
| 2026-10-30 | Qual é o fuso de `orders.order_datetime` (Europe/London ou UTC)? | Dono da fonte | [Pauta do contrato](../../contracts/rystore_open_points.md) |
| 2026-10-30 | Pedidos `Cancelled` (total 0) e `Refunded` (valores mantidos) entram na receita? Como? | Dono da fonte e consumidores | [Pauta do contrato](../../contracts/rystore_open_points.md) |
| 2026-10-30 | O que `customers.signup_date` representa, se há pedidos anteriores a ela? | Dono da fonte | [Pauta do contrato](../../contracts/rystore_open_points.md) |
| 2026-10-30 | `employees` é completo ou uma amostra (não bate com `stores.staff_count`)? | Dono da fonte | [Pauta do contrato](../../contracts/rystore_open_points.md) |
| 2026-10-30 | As vendas na loja física entre 00h e 6h são reais ou efeito de fuso? | Dono da fonte | [Pauta do contrato](../../contracts/rystore_open_points.md) |
| 2026-10-30 | Funcionários admitidos antes da abertura da loja: transferência ou data inválida? | Dono da fonte | [Pauta do contrato](../../contracts/rystore_open_points.md) |
| 2026-10-30 | A carga é sempre completa? Como chega uma exclusão? | Dono da fonte | [Pauta do contrato](../../contracts/rystore_open_points.md) |
| 2026-10-30 | Com que frequência roda a ingestão? Qual o nome do *secret scope*? | Engenheiro de dados | [pipeline.md](../architecture/pipeline.md) |
| 2026-10-30 | Os dados ficam no Supabase Storage como arquivos (o `boto3` lê o bucket, não as tabelas do PostgreSQL)? | Engenheiro de dados | [pipeline.md](../architecture/pipeline.md) |
