# Databricks notebook source
# MAGIC %md
# MAGIC # Gold: modelo dimensional da RYStore
# MAGIC
# MAGIC | Tabela | Grão | Observação |
# MAGIC |---|---|---|
# MAGIC | `dim_data` | um dia | calendário que cobre todas as datas dos pedidos |
# MAGIC | `dim_loja` | uma loja | |
# MAGIC | `dim_produto` | um produto | com o fornecedor |
# MAGIC | `dim_fornecedor` | um fornecedor | sem e-mail |
# MAGIC | `dim_cliente` | um cliente | sem PII; o membro `ANON` representa as vendas anônimas |
# MAGIC | `fato_vendas` | um item de pedido | `is_revenue` = pedido `Completed`; valores somáveis |
# MAGIC | `fato_pedidos` | um pedido | `revenue_amount` = `total_amount` só de `Completed` |
# MAGIC | `fato_estoque` | uma loja × produto, na foto do dia | `below_reorder` quando o estoque está abaixo do ponto de reposição |
# MAGIC
# MAGIC Receita conta só pedidos `Completed` (contrato 1.0.0).

# COMMAND ----------

dbutils.widgets.text("catalog", "lh_retail_analytics")
catalog = dbutils.widgets.get("catalog")
s, g = f"{catalog}.silver", f"{catalog}.gold"


def build(name, sql):
    spark.sql(f"CREATE OR REPLACE TABLE {g}.{name} AS {sql}")
    print(f"gold.{name}: {spark.table(f'{g}.{name}').count()} linhas")

# COMMAND ----------

build("dim_data", f"""
    WITH bounds AS (SELECT make_date(year(min(order_date)), 1, 1) AS d0, make_date(year(max(order_date)), 12, 31) AS d1
                    FROM {s}.orders)
    SELECT CAST(date_format(d, 'yyyyMMdd') AS INT) AS date_key, d AS date, year(d) AS year, quarter(d) AS quarter,
           month(d) AS month, date_format(d, 'MMMM') AS month_name, day(d) AS day,
           dayofweek(d) AS day_of_week, date_format(d, 'EEEE') AS day_name, dayofweek(d) IN (1, 7) AS is_weekend
    FROM bounds LATERAL VIEW explode(sequence(d0, d1, INTERVAL 1 DAY)) t AS d
""")

build("dim_loja", f"""
    SELECT store_id, store_name, city, region, postcode, store_format, opening_date, staff_count FROM {s}.stores
""")

build("dim_fornecedor", f"""
    SELECT supplier_id, supplier_name, main_category, city, postcode, lead_time_days FROM {s}.suppliers
""")

build("dim_produto", f"""
    SELECT p.product_id, p.product_name, p.category, p.brand, p.supplier_id, f.supplier_name,
           p.unit_cost, p.unit_price, p.vat_rate, p.reorder_level, p.active
    FROM {s}.products p LEFT JOIN {s}.suppliers f USING (supplier_id)
""")

build("dim_cliente", f"""
    SELECT customer_id, city, signup_date, loyalty_tier, customer_segment, marketing_opt_in, false AS is_anonymous
    FROM {s}.customers
    UNION ALL
    SELECT 'ANON', NULL, NULL, 'None', 'Anonymous', false, true
""")

# COMMAND ----------

build("fato_pedidos", f"""
    SELECT o.order_id, CAST(date_format(o.order_date, 'yyyyMMdd') AS INT) AS date_key,
           o.order_datetime_local, o.order_datetime_utc, o.store_id, coalesce(o.customer_id, 'ANON') AS customer_id,
           o.order_channel, o.payment_method, o.order_status, coalesce(i.item_count, 0) AS item_count,
           o.subtotal, o.discount_total, o.vat_total, o.delivery_fee, o.total_amount,
           CASE WHEN o.order_status = 'Completed' THEN o.total_amount ELSE 0 END AS revenue_amount
    FROM {s}.orders o
    LEFT JOIN (SELECT order_id, count(*) AS item_count FROM {s}.order_items GROUP BY order_id) i USING (order_id)
""")

build("fato_vendas", f"""
    SELECT i.order_item_id, i.order_id, CAST(date_format(o.order_date, 'yyyyMMdd') AS INT) AS date_key,
           o.store_id, coalesce(o.customer_id, 'ANON') AS customer_id, i.product_id, p.supplier_id, i.promotion_id,
           o.order_channel, o.order_status, o.order_status = 'Completed' AS is_revenue,
           i.quantity, i.unit_price,
           CAST(i.quantity * i.unit_price AS DECIMAL(12,2)) AS gross_amount,
           i.discount_amount, i.line_net_amount AS net_amount, i.line_vat_amount AS vat_amount,
           CAST(i.quantity * p.unit_cost AS DECIMAL(12,2)) AS cost_amount,
           CAST(i.line_net_amount - i.quantity * p.unit_cost AS DECIMAL(12,2)) AS margin_amount
    FROM {s}.order_items i
    JOIN {s}.orders o USING (order_id)
    JOIN {s}.products p USING (product_id)
""")

build("fato_estoque", f"""
    SELECT CAST(date_format(CAST(v._bronze_ingested_at AS DATE), 'yyyyMMdd') AS INT) AS snapshot_date_key,
           CAST(v._bronze_ingested_at AS DATE) AS snapshot_date,
           v.store_id, v.product_id, v.stock_on_hand, v.stock_on_order, p.reorder_level,
           v.stock_on_hand < p.reorder_level AS below_reorder, v.last_restock_date, v.aisle_location
    FROM {s}.inventory v JOIN {s}.products p USING (product_id)
""")
