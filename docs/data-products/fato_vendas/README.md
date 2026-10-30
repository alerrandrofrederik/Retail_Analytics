# Produto de dados: Vendas RYStore (`gold.fato_vendas`)

Versão 1.0.0, 2026-10-30, criada pela skill `data-product`. O contrato com o consumidor está em [`fato_vendas.odcs.yaml`](fato_vendas.odcs.yaml) (ODCS v3.1.0, validado contra o JSON Schema). A página navegável de todos os produtos é [`../index.html`](../index.html).

## Visão geral

| | |
|---|---|
| Tabela | `lh_retail_analytics.gold.fato_vendas` (Delta, gerenciada) |
| Para que serve | Vendas, margem e mix da RYStore por dia, loja, produto, fornecedor, cliente, canal e promoção, no Genie ou em SQL |
| Granularidade | Um item de pedido (`order_item_id`), com todos os status; receita = linhas com `is_revenue` |
| Linhas | 47.512 itens de 10.000 pedidos, de 2025-01-01 a 2025-12-31 (rodada `498752805931100`) |
| Quem lê | Ninguém além do engenheiro de dados até 2026-10-30 (`system.query.history`); o público previsto são os analistas no Genie |
| Nível de serviço | Reconstruída todo dia pelo job `rystore_pipeline` (07:00 UTC), pronta até **08:00 UTC** ([decisão](../../../knowledge/decisions/decision-log.md)) |
| Dono e suporte | O engenheiro de dados; issues do repositório no GitHub |
| Código | [`gold.py`](../../../retail_analytics/src/retail_analytics/gold.py), tabela `fato_vendas` |

## Guia

**No que confiar:**
- A [reconciliação de 2026-10-30](../../../reports/reconcile/rystore_reconcile_2026-10-30.html) bate com os arquivos da fonte: as linhas e, por status, mês e loja, a receita, os pedidos e os itens têm diferença zero.
- A [qualidade de 2026-10](../../../reports/quality/rystore_quality_2026-10.html) deu 38 checagens aprovadas e 0 linhas em quarentena.
- Toda chave da tabela encontra a sua dimensão: os joins com loja, cliente, produto, fornecedor e data não perdem nenhuma linha.

**Problemas conhecidos:**
1. **Margem com o custo de hoje.** `cost_amount` e `margin_amount` usam o `unit_cost` atual do produto, e não o custo no dia da venda. Se um custo mudar, a margem de todo o histórico muda junto. A fonte não guarda o histórico de custos.
2. **Itens × total do pedido.** A soma de `net_amount + vat_amount` de um pedido não inclui a taxa de entrega, que é cobrada por pedido. Nos pedidos Completed, os itens somam £244.156,27; com as taxas de entrega (£5.364,13), chegam a £249.520,40, contra os £249.520,30 de receita da `fato_pedidos`. A diferença de £0,10 vem de 82 pedidos com ±0,01, que é o arredondamento da fonte, dentro da tolerância do contrato. Para a receita do pedido, use `gold.fato_pedidos.revenue_amount`.
3. **Desconto por item × desconto do pedido.** Em 22 pedidos, a soma de `discount_amount` difere de `discount_total` do pedido em ±0,01, também por arredondamento da fonte.
4. **Promoção sem dimensão.** `promotion_id` existe, mas a gold ainda não tem `dim_promocao`. Há 6 promoções em 1.990 linhas, e só elas têm desconto.
5. **Atualização.** No dev, o agendamento está pausado; em 2026-10-30, a tabela foi reconstruída à mão às 18:22 UTC, depois do SLA.
6. **Dia e mês.** Use sempre `date_key`, que é a data local do Reino Unido. Agrupar por um horário em UTC muda 247 pedidos de dia e 6 de mês ([glossário](../../../knowledge/business/glossary.md)).

**Por onde começar:** pela consulta 1 (receita e margem por mês), sempre com `WHERE is_revenue`.

## Modelo de dados

| Chave em `fato_vendas` | Junta com | Observação |
|---|---|---|
| `date_key` | `gold.dim_data.date_key` | data local; a dimensão cobre 2025 e 2026 |
| `store_id` | `gold.dim_loja.store_id` | 8 lojas |
| `customer_id` | `gold.dim_cliente.customer_id` | `ANON` = venda anônima (13.098 itens); sem dados pessoais |
| `product_id` | `gold.dim_produto.product_id` | inclui o nome do fornecedor |
| `supplier_id` | `gold.dim_fornecedor.supplier_id` | o fornecedor do produto |
| `order_id` | `gold.fato_pedidos.order_id` | o pedido (total, taxa de entrega, receita do pedido) |
| `promotion_id` | — | sem dimensão na gold (problema conhecido 4) |

É um esquema estrela: os joins são N:1 e não multiplicam linhas.

## Métricas

| Medida | Regra | Soma? |
|---|---|---|
| Receita líquida de itens | `sum(net_amount)` com `is_revenue` | sim |
| IVA | `sum(vat_amount)` com `is_revenue` | sim |
| Receita bruta de itens | `sum(gross_amount)` = quantidade × preço, antes do desconto | sim |
| Desconto | `sum(discount_amount)` | sim |
| Custo | `sum(cost_amount)`, com o custo atual | sim, com o problema 1 |
| Margem | `sum(margin_amount)` = receita líquida − custo | sim, com o problema 1 |
| Margem % | `sum(margin_amount) / sum(net_amount)` | não; recalcule a partir das somas |
| Unidades | `sum(quantity)` | sim |
| Preço unitário | `unit_price` | não; use `sum(gross_amount) / sum(quantity)` |
| Pedidos | `count(DISTINCT order_id)` | não; conte de novo em cada recorte |
| Receita do pedido (com entrega) | `gold.fato_pedidos.revenue_amount` | sim, mas na outra tabela |

Os números de 2025 (pedidos Completed): receita líquida de itens de £228.457,01, IVA de £15.699,26 e margem de £107.706,81.

## Consultas iniciais

O histórico de consultas ainda não tem nenhuma consulta de consumidor, então estas são propostas. Todas foram testadas na gold da rodada `498752805931100`.

```sql
-- 1. Receita líquida, IVA e margem por mês (só pedidos Completed)
SELECT d.year, d.month, sum(v.net_amount) AS receita_liquida, sum(v.vat_amount) AS iva, sum(v.margin_amount) AS margem
FROM lh_retail_analytics.gold.fato_vendas v
JOIN lh_retail_analytics.gold.dim_data d ON d.date_key = v.date_key
WHERE v.is_revenue
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- 2. Os 10 produtos com mais receita líquida
SELECT p.product_name, p.category, sum(v.quantity) AS unidades, sum(v.net_amount) AS receita_liquida
FROM lh_retail_analytics.gold.fato_vendas v
JOIN lh_retail_analytics.gold.dim_produto p ON p.product_id = v.product_id
WHERE v.is_revenue
GROUP BY p.product_name, p.category
ORDER BY receita_liquida DESC
LIMIT 10;

-- 3. Receita líquida por loja e canal
SELECT l.store_name, v.order_channel, count(DISTINCT v.order_id) AS pedidos, sum(v.net_amount) AS receita_liquida
FROM lh_retail_analytics.gold.fato_vendas v
JOIN lh_retail_analytics.gold.dim_loja l ON l.store_id = v.store_id
WHERE v.is_revenue
GROUP BY l.store_name, v.order_channel
ORDER BY l.store_name, v.order_channel;

-- 4. Itens cancelados e devolvidos por mês
SELECT d.month, v.order_status, count(*) AS itens, sum(v.net_amount) AS valor_liquido
FROM lh_retail_analytics.gold.fato_vendas v
JOIN lh_retail_analytics.gold.dim_data d ON d.date_key = v.date_key
WHERE v.order_status IN ('Cancelled', 'Refunded')
GROUP BY d.month, v.order_status
ORDER BY d.month, v.order_status;

-- 5. Linhas com e sem promoção
SELECT v.promotion_id IS NOT NULL AS com_promocao, count(*) AS itens, sum(v.discount_amount) AS desconto, sum(v.net_amount) AS receita_liquida
FROM lh_retail_analytics.gold.fato_vendas v
WHERE v.is_revenue
GROUP BY 1;

-- 6. Receita líquida por segmento de cliente (ANON = vendas anônimas)
SELECT c.customer_segment, count(DISTINCT v.order_id) AS pedidos, sum(v.net_amount) AS receita_liquida
FROM lh_retail_analytics.gold.fato_vendas v
JOIN lh_retail_analytics.gold.dim_cliente c ON c.customer_id = v.customer_id
WHERE v.is_revenue
GROUP BY c.customer_segment
ORDER BY receita_liquida DESC;
```

## Qualidade

| Regra | Onde | Resultado em 2026-10-30 |
|---|---|---|
| As 38 checagens da silver (fórmulas, listas fechadas, contagens) | `silver._checks` | todas aprovadas |
| Quarentena de tipo e de chave estrangeira | `silver._quarantine` | 0 linhas |
| Toda `date_key` existe em `dim_data` | `tests/test_gold.py` | aprovado |
| Reconciliação com a fonte | [página](../../../reports/reconcile/rystore_reconcile_2026-10-30.html) | diferença zero |
| Atualização até 08:00 UTC | [qualidade](../../../reports/quality/rystore_quality_2026-10.html) | não cumprida em 2026-10-30 (rodada manual) |

## Versões

| Versão | Data | O que mudou |
|---|---|---|
| 1.0.0 | 2026-10-30 | Primeira versão: 47.512 itens, 2025. Nenhuma correção reportada por consumidores. |

## Pontos em aberto para o engenheiro de dados

Nada foi alterado na tabela nem no SQL.

1. Criar uma `dim_promocao` na gold, a partir de `silver.promotions`.
2. Decidir se a margem deve usar o custo histórico. Isso depende de a fonte entregar o histórico de `unit_cost`, então é uma pergunta para o dono da fonte.
3. Reativar o agendamento no prod, para cumprir o SLA de 08:00 UTC.
