# Glossário e regras de negócio

Origem: perfil da fonte RYStore em [`reports/profile/rystore_profile.html`](../../reports/profile/rystore_profile.html), de 2026-10-30. Cada regra abaixo foi testada linha a linha nos dados; As respostas do dono da fonte estão no [contrato](../../contracts/rystore.odcs.yaml) e na [pauta](../../contracts/rystore_open_points.md).

## Pedido

| Termo | Significado |
|---|---|
| `order_status` | `Completed`, `Refunded` ou `Cancelled` |
| Pedido cancelado | `Cancelled`: `total_amount` = 0, mas `subtotal`, `vat_total`, `discount_total` e os itens são mantidos. Fica fora da receita ([contrato](../../contracts/rystore.odcs.yaml)) |
| Pedido reembolsado | `Refunded`: mantém todos os valores. Fica fora da receita |
| Receita | Soma de `total_amount` só dos pedidos `Completed` (contrato 1.0.0) |
| `order_channel` | `In-store` (loja), `Online` (entrega) ou `Click & Collect` (compra online, retirada na loja) |
| `payment_method` | `Card`, `Mobile Wallet`, `Cash` ou `Gift Card` |
| Venda anônima | Pedido sem `customer_id`: cliente fora do programa de fidelidade |

## Valores

- `subtotal` é **bruto**: Σ `quantity` × `unit_price` dos itens, antes do desconto.
- `total_amount` = `subtotal` − `discount_total` + `vat_total` + `delivery_fee` (exceto `Cancelled`, que tem total 0). A fórmula fecha com tolerância de 0,01: 98 pedidos diferem em ±0,01 por arredondamento (conferido por script em 2026-10-30, ao escrever o [contrato](../../contracts/rystore.odcs.yaml)).
- `line_net_amount` é **líquido**: `quantity` × `unit_price` − `discount_amount`.
- `line_vat_amount` = `line_net_amount` × `products.vat_rate`. O `vat_rate` é 0 ou 0,2 (IVA do Reino Unido).
- `vat_total` e `discount_total` do pedido são a soma dos itens.
- `order_items.unit_price` é igual a `products.unit_price`: não há preço por loja nem por data.
- Moeda: GBP.

## Frete

`delivery_fee` = 3,49 GBP só no canal `Online`, e é 0 quando o `subtotal` ≥ 40 GBP (frete grátis). Nos outros canais é sempre 0.

## Promoção

- Uma promoção vale para uma categoria de produto, entre `start_date` e `end_date`.
- O item tem `promotion_id` se e somente se `discount_amount` > 0, sempre dentro da vigência e na categoria da promoção.
- `discount_type`: `Percentage` (o `discount_value` é %) ou `Fixed` (o `discount_value` é GBP).

## Cliente, produto e loja

- `loyalty_tier`: `Bronze`, `Silver`, `Gold` ou `Platinum`.
- `signup_date`: data de adesão ao programa de fidelidade. Pedido anterior a ela é válido (contrato 1.0.0).
- `products.active` = `False` marca o produto fora de linha. Os produtos inativos não têm vendas em 2025.
- `inventory` é uma foto do estoque por loja e produto. `reorder_level` (em `products`) é o ponto de reposição.
- `aisle_location` é texto livre: corredor numerado (`Aisle 1`…) ou nome de seção (`Bakery`, `Frozen`…). Os dois valem.
- `employees` é uma amostra do quadro; `stores.staff_count` é o quadro oficial. `hire_date` é a admissão na empresa e pode ser anterior à abertura da loja (transferência).

## Data e hora

`orders.order_datetime` é hora local do Reino Unido (Europe/London), sem offset. Na hora que não existe (troca de primavera) avança 1h; na hora repetida (troca de outono) vale a primeira (BST, +01:00). Vendas na loja física de madrugada são reais.
