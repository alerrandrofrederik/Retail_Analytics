Use a skill `test-data` para criar os dados de teste da ingestão e da camada bronze.

Entradas: a metadata (prompt_02) e o contrato (prompt_03).

Gere linhas sintéticas no formato da fonte (vírgula, ASCII, CRLF, campo vazio como nulo), nunca dados reais. Escreva primeiro o resultado esperado de cada caso, depois os arquivos:
- entrega limpa;
- linha quebrada e número de colunas errado;
- bytes inválidos na codificação;
- coluna nova e coluna renomeada (drift que a checagem de esquema tem de parar);
- item de pedido antes do pedido (filho antes do pai);
- chave primária duplicada;
- os casos de borda do perfil: pedido Cancelled com total 0, cliente vazio (venda anônima), horário no fim do horário de verão.

Pré-requisito: prompt_02 e prompt_03.

Saída: as fixtures e os testes ao lado do código do bundle (retail_analytics/), no lugar que você propuser.
