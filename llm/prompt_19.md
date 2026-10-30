Modelo: use depois que o pipeline estiver rodando há tempo suficiente.

## Revisão geral da plataforma (mensal; precisa de 90 dias de query logs para achar dados sem uso)

Use a skill `big-review` para o período [período; padrão: último mês]. Uso (tabelas mais lidas, consultas mais lentas, linhas lidas x necessárias), dados sem uso nos últimos 90 dias (conferindo jobs de fim de mês, trimestre e ano), código morto e propostas com esforço e risco. Não muda nada.

Saída: uma página HTML em reports/.

## Revisão de custo (mensal; depois da revisão geral)

Use a skill `cost-review` para o período [período; padrão: último mês]. Custo de computação por job e pipeline, armazenamento por tabela (as tabelas sem uso vêm da revisão geral acima), custo por execução contra o período anterior, gasto ocioso e o que cortar. Propõe; não para nem apaga nada.

Saída: uma página HTML em reports/.

Perfil pessoal, catálogo lh_retail_analytics.
