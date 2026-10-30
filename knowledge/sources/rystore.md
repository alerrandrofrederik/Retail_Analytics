# Fonte: RYStore

Origem: pasta [`RYStore-Retail-Dataset/`](../../RYStore-Retail-Dataset/) e o perfil em [`reports/profile/rystore_profile.html`](../../reports/profile/rystore_profile.html), de 2026-10-30. Os números estão no relatório.

## O que é

Dataset fictício de um supermercado do Reino Unido, com vendas de 2025, de [ryanariefe/RYStore-Retail-Dataset](https://github.com/ryanariefe/RYStore-Retail-Dataset). São 9 CSVs, um por tabela, mais um `data_dictionary.csv` e um `README.md`. A entrega é completa: não há data de alteração nem marca de exclusão.

## Tabelas e chaves

| Tabela | Chave primária | Chaves estrangeiras |
|---|---|---|
| `orders` | `order_id` | `store_id` → stores; `customer_id` → customers (opcional: venda anônima) |
| `order_items` | `order_item_id` | `order_id` → orders; `product_id` → products; `promotion_id` → promotions (opcional) |
| `customers` | `customer_id` | |
| `products` | `product_id` | `supplier_id` → suppliers |
| `suppliers` | `supplier_id` | |
| `stores` | `store_id` | |
| `employees` | `employee_id` | `store_id` → stores |
| `promotions` | `promotion_id` | |
| `inventory` | `store_id` + `product_id` | `store_id` → stores; `product_id` → products |

No perfil, todas as chaves primárias são únicas e não há órfãos.

## Formato

- Delimitador vírgula, sem aspas, ASCII (ler como UTF-8 sem BOM), quebra de linha CRLF, com cabeçalho.
- Nulo é só o campo vazio.
- Decimal com ponto, sem separador de milhar; valores em GBP, com número variável de casas (`18.5`, `3.0`).
- Datas `yyyy-MM-dd`; `orders.order_datetime` em `yyyy-MM-dd HH:mm:ss`, **sem fuso**.
- Booleanos `True`/`False`.

## Dados pessoais

Colunas restritas: `customers.first_name`, `last_name`, `email`, `postcode_area`; `employees.first_name`, `last_name`, `annual_salary`; `suppliers.email`. O README da fonte diz que tudo é fictício, mas o projeto trata essas colunas como reais.

## Regras confirmadas

Ver o [glossário](../business/glossary.md), que traz as fórmulas de valores, o status dos pedidos, o frete e as promoções.

## Pontos em aberto com o dono da fonte

Estão no [registro de decisões](../decisions/decision-log.md): o fuso de `order_datetime`, a semântica de `Cancelled` e `Refunded`, o significado de `signup_date`, se `employees` é completo, as vendas na loja de madrugada e funcionários admitidos antes da abertura da loja.

## Dicionário de dados

O `data_dictionary.csv` cobre as 77 colunas, mas com descrições genéricas. Ele diz que `promotions.discount_type` é inteiro, mas a coluna chega como texto (`Percentage`/`Fixed`). O contrato de dados vai substituí-lo.
