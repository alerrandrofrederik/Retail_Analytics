Antes de construir a ingestão, precisamos fechar as decisões de arquitetura que estão em aberto em knowledge/architecture/pipeline.md e knowledge/decisions/decision-log.md.

Monte um questionário curto para o engenheiro de dados, com a sua recomendação e o motivo de cada uma:

1. Os dados da origem ficam no Supabase Storage como arquivos (o boto3 lê o bucket pela API S3) ou nas tabelas do PostgreSQL (aí o boto3 não serve)? Se for Storage: qual bucket e qual estrutura de pastas (ex.: <tabela>/<data>/arquivo.csv)?
2. Nome do secret scope no Databricks e nome das chaves (S3_ENDPOINT, AWS_DEFAULT_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY).
3. Frequência da ingestão e horário do job.
4. Carga completa ou incremental, e como tratar exclusões, já que a fonte não tem updated_at nem flag de exclusão.
5. As respostas do contrato (prompt_03) que mudam o pipeline, se o dono da fonte já respondeu.

Não crie nada no Databricks nem no Supabase. Depois das respostas, atualize o decision-log (de "em aberto" para "tomada", com data e origem) e a página pipeline.md.

Pré-requisito: prompt_03 concluído. Bloqueia os prompts 05 e 07.
