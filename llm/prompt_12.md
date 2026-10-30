Use a skill `reconcile` para conferir se os números batem entre a fonte e o lakehouse.

Lados a comparar:
- CSVs da RYStore x origem no Supabase x bronze: linhas por tabela;
- bronze x silver: linhas, mais as que foram para quarentena;
- silver x gold: receita total, quantidade de pedidos e itens por status (Completed, Cancelled, Refunded), por mês e por loja.

Deixe os lados comparáveis (mesmo período, mesmo fuso, mesmos filtros) e quebre as diferenças até achar a fatia e a causa. Não mude nenhum número.

Pré-requisito: prompt_09.

Saída: uma página HTML em reports/ e o knowledge atualizado com as causas encontradas.
