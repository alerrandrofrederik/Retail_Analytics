Construa a camada gold em lh_retail_analytics.gold: o modelo dimensional descrito no README.

Dimensões: dim_produto, dim_cliente, dim_loja, dim_fornecedor, dim_data. Fatos: fato_vendas, fato_estoque, fato_pedidos.

Para cada tabela, defina antes a granularidade, as chaves e as medidas (e quais podem ser somadas), e mostre o plano. Trate os casos do perfil: venda anônima (cliente desconhecido na dim_cliente), pedidos Cancelled e Refunded conforme a decisão, produtos inativos, PII que não deve chegar ao consumidor (mascarar ou não levar e-mail, telefone e endereço).

Perfil pessoal, catálogo lh_retail_analytics, target dev, sim antes de deploy ou run.

Pré-requisito: prompt_08.

Saída: o código no bundle, os testes, as tabelas gold criadas no dev e knowledge/architecture/pipeline.md atualizado.
