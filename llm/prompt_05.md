Prepare a origem: carregar os CSVs da RYStore no Supabase, no formato decidido no prompt_04 (arquivos no Storage e/ou tabelas no PostgreSQL).

Entradas: a decisão do prompt_04, o contrato (prompt_03), a metadata (prompt_02) e o .env.example. As credenciais estão no .env: nunca leia nem mostre o .env, use as variáveis de ambiente.

Escreva um script Python local (gerenciado com uv, dependências no pyproject.toml) que faça a carga de forma idempotente: rodar duas vezes não duplica nada. Mostre o plano e o script antes de rodar. A carga escreve no Supabase, então peça o sim antes de executar.

Confira depois: contagem de linhas por tabela/arquivo na origem igual à do perfil.

Pré-requisito: prompt_04 decidido.

Saída: o script de carga, o resultado da conferência e knowledge/architecture/pipeline.md atualizado.
