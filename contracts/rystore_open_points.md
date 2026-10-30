# Pontos em aberto: contrato RYStore

Pauta da reunião do engenheiro de dados com o dono da fonte RYStore, sobre o rascunho [`rystore.odcs.yaml`](rystore.odcs.yaml) (versão 0.1.0, `draft`). Cada ponto traz a pergunta, o fato que a motivou e o campo do contrato que muda com a resposta. Os números estão no [perfil da fonte](../reports/profile/rystore_profile.html).

Quando todos forem respondidos, o contrato passa para a versão 1.0.0, `active`, e as respostas entram no [registro de decisões](../knowledge/decisions/decision-log.md).

## Responsáveis e entrega

| # | Pergunta | Fato | Campo do contrato |
|---|---|---|---|
| 1 | Quem é o dono da fonte e qual o canal de suporte? | Nenhum dono definido ainda | `team.members[owner]`, `support` |
| 2 | Os dados chegam como arquivos no Supabase Storage (bucket e caminho?) ou ficam nas tabelas do PostgreSQL? | A ingestão planejada usa `boto3`, que lê só o Storage ([pipeline](../knowledge/architecture/pipeline.md)) | `servers` |
| 3 | Com que frequência chega uma entrega, e até que horas? | Não definido | `slaProperties.frequency`, `timeOfAvailability` |
| 4 | A entrega é sempre completa? Se vier só o que mudou, como saber o que mudou? | Nenhuma tabela tem data de alteração | `schema[].load` |
| 5 | Como chega uma linha excluída? | Não há marca de exclusão: a linha só some do arquivo | `schema[].deletes` |
| 6 | Com quantos dias de antecedência uma mudança de esquema ou de formato é avisada? | Não definido | `customProperties.changeNotice` |

## Semântica dos dados

| # | Pergunta | Fato | Campo do contrato |
|---|---|---|---|
| 7 | Qual é o fuso de `orders.order_datetime`: Europe/London ou UTC? | O valor não tem offset; há pedidos na hora inexistente e na hora repetida do horário de verão britânico | `customProperties.timezone` |
| 8 | Pedidos `Cancelled` (total 0, mas com subtotal, IVA e itens) e `Refunded` (valores mantidos) entram na receita? Como? | Status de `orders` | regra de `orders.quality` |
| 9 | O que `customers.signup_date` representa? | Há pedidos de clientes anteriores à data de cadastro, e cadastros posteriores a 2025 | descrição de `signup_date` |
| 10 | `employees` é completo ou uma amostra? | `stores.staff_count` não bate com a contagem de `employees` em nenhuma loja | descrição de `employees` e `staff_count` |
| 11 | Funcionários admitidos antes da abertura da loja: transferência ou data inválida? | `hire_date` anterior a `stores.opening_date` | regra de `employees.quality` |
| 12 | As vendas na loja física entre 00h e 6h são reais? | Pedidos `In-store` de madrugada; pode ser efeito de fuso (ponto 7) | regra de `orders.quality` |
| 13 | `inventory.aisle_location` mistura corredor (`Aisle N`) e seção (`Bakery`, `Frozen`…). É de propósito? | 10 valores, dos dois tipos | descrição de `aisle_location` |
| 14 | `promotions.discount_value` é percentual quando `discount_type` é `Percentage` e valor em GBP quando é `Fixed`? | Os valores (`10`, `0.3`…) indicam isso, mas o dicionário diz "Integer count" | descrição e regra de `promotions` |
| 15 | As listas de valores (status, canal, pagamento, tier, segmento, cargo, contrato, tipo de desconto, formato de loja, categoria) estão completas? Um valor novo é mudança de contrato? | O contrato fixa os valores vistos no perfil | `quality` `invalidValues` das colunas |

## Formato e documentação

| # | Pergunta | Fato | Campo do contrato |
|---|---|---|---|
| 16 | A fonte pode mandar descrições reais das colunas? | O `data_dictionary.csv` usa só 6 textos genéricos e contradiz os dados em `discount_type` e `discount_value` ([metadata](../metadata/rystore.yaml)) | `description` das colunas |
| 17 | Inteiros podem chegar como decimal (`3.0`)? | Números serializados como float em algumas colunas | `logicalType` das colunas |
| 18 | O total do pedido pode diferir em 0,01 por arredondamento? | 98 pedidos (Completed e Refunded) diferem em ±0,01 da fórmula subtotal − desconto + IVA + frete | regra de `orders.quality` |
| 19 | Os dados pessoais são mesmo fictícios? O contrato os trata como reais (`restricted`). | O README da fonte diz que tudo é fictício | `classification` das colunas |
