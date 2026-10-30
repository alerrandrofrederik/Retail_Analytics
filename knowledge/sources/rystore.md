# Fonte: RYStore

Origem: pasta [`RYStore-Retail-Dataset/`](../../RYStore-Retail-Dataset/) e o perfil em [`reports/profile/rystore_profile.html`](../../reports/profile/rystore_profile.html), de 2026-10-30. Os números estão no relatório.

## O que é

Dataset fictício de um supermercado do Reino Unido, com vendas de 2025, de [ryanariefe/RYStore-Retail-Dataset](https://github.com/ryanariefe/RYStore-Retail-Dataset). São 9 CSVs, um por tabela, mais um `data_dictionary.csv` e um `README.md`. Não há data de alteração nem marca de exclusão; a entrega está definida no contrato.

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

## Contrato de dados

O contrato está em [`contracts/rystore.odcs.yaml`](../../contracts/rystore.odcs.yaml) (skill `contract`, 2026-10-30).

- Segue o ODCS v3.1.0, versão 1.0.0, com `status: active` desde 2026-10-30, e foi validado contra o JSON Schema do padrão.
- Colunas, tipos, chaves e descrições vêm da metadata.
- Define 2 colunas opcionais, 8 colunas `restricted` (PII) e as 9 chaves estrangeiras.
- As regras de qualidade não usam SQL: são métricas `library` (nulos, duplicados, formato dos IDs e listas de valores) e regras de negócio em texto.

As respostas aos 19 pontos estão na [pauta](../../contracts/rystore_open_points.md): entrega diária no Supabase Storage, `orders`/`order_items` incrementais e as demais completas, fuso Europe/London, receita só `Completed`.

## Pontos em aberto com o dono da fonte

Só as descrições reais das colunas, para a próxima versão do contrato ([registro de decisões](../decisions/decision-log.md)).

## Dicionário de dados

O `data_dictionary.csv` cobre as 77 colunas, mas só com 6 textos genéricos repetidos (ex.: "Categorical or descriptive attribute.").

Ele contradiz os dados em duas colunas de `promotions`, que descreve como "Integer count or threshold.":
- `discount_type` chega como texto (`Percentage`/`Fixed`);
- `discount_value` chega como decimal (há `0.3`).

O contrato de dados vai substituí-lo.

## Metadata

A metadata da fonte está em [`metadata/rystore.yaml`](../../metadata/rystore.yaml), gerada por [`metadata/scripts/extract_metadata.py`](../../metadata/scripts/extract_metadata.py) (skill `metadata`, 2026-10-30).

- Traz 9 tabelas e 77 colunas, com o tipo inferido dos dados, as chaves do perfil e as descrições do dicionário e do README da fonte.
- As descrições são genéricas e, nas 2 colunas acima, ficaram vazias: não foram inventadas. Descrições reais são uma pergunta para o dono da fonte (contrato).
- Para atualizar, rode o script de novo; não edite o YAML à mão.

## Reconciliação

Origem: [reconciliação de 2026-10-30](../../reports/reconcile/rystore_reconcile_2026-10-30.html) (skill `reconcile`), depois da rodada `498752805931100`. Os números estão na página.

- **CSVs, bucket e bronze:** as linhas batem por tabela e por arquivo (os 737 arquivos estão no log da bronze).
- **Bronze e silver:** a versão vigente da bronze é igual à silver mais a quarentena, nas 9 tabelas.
- **Silver, gold e fonte:** receita, pedidos e itens batem por status, mês e loja, e também nas fatias status × mês × loja.
- **Nenhuma causa de diferença foi encontrada.** A única armadilha é de quem consome os dados: agrupar pela data em UTC muda o dia e o mês de vendas feitas logo depois da meia-noite em BST ([glossário](../business/glossary.md)).

