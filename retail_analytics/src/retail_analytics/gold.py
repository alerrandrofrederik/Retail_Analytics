"""Gold: the dimensional model of RYStore, with DuckDB (no Spark).

| Table | Grain | Note |
|---|---|---|
| dim_data | one day | whole years covering every order date and stock snapshot; day_of_week as in Spark (Sunday = 1) |
| dim_loja | one store | |
| dim_produto | one product | with the supplier |
| dim_fornecedor | one supplier | without e-mail |
| dim_cliente | one customer | without personal data; the member ANON stands for the anonymous sales |
| dim_promocao | one promotion | joins fato_vendas.promotion_id |
| fato_vendas | one order item | is_revenue = order Completed; additive amounts |
| fato_pedidos | one order | revenue_amount = total_amount of Completed only |
| fato_estoque | one store x product, in the snapshot of the day | below_reorder when stock is under the reorder point |

Revenue counts only Completed orders (contract 1.0.0). Reads <silver>/<table>/ and writes <gold>/<table>/part-0.parquet.
"""

from pathlib import Path

import duckdb

from retail_analytics.lake import write

TABLES = {
    "dim_data": """
        WITH dates AS (SELECT order_date AS d FROM orders
                       UNION ALL SELECT CAST(_bronze_ingested_at AS DATE) FROM inventory),
             bounds AS (SELECT make_date(year(min(d)), 1, 1) AS d0, make_date(year(max(d)), 12, 31) AS d1 FROM dates),
             days AS (SELECT CAST(d AS DATE) AS d FROM bounds, generate_series(d0, d1, INTERVAL 1 DAY) AS t(d))
        SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key, d AS "date", year(d) AS year, quarter(d) AS quarter,
               month(d) AS month, strftime(d, '%B') AS month_name, day(d) AS day,
               dayofweek(d) + 1 AS day_of_week, strftime(d, '%A') AS day_name, dayofweek(d) IN (0, 6) AS is_weekend
        FROM days""",
    "dim_loja": "SELECT store_id, store_name, city, region, postcode, store_format, opening_date, staff_count FROM stores",
    "dim_fornecedor": "SELECT supplier_id, supplier_name, main_category, city, postcode, lead_time_days FROM suppliers",
    "dim_produto": """
        SELECT p.product_id, p.product_name, p.category, p.brand, p.supplier_id, f.supplier_name,
               p.unit_cost, p.unit_price, p.vat_rate, p.reorder_level, p.active
        FROM products p LEFT JOIN suppliers f USING (supplier_id)""",
    "dim_promocao": """
        SELECT promotion_id, promotion_name, start_date, end_date, discount_type, discount_value, category
        FROM promotions""",
    "dim_cliente": """
        SELECT customer_id, city, signup_date, loyalty_tier, customer_segment, marketing_opt_in, false AS is_anonymous
        FROM customers
        UNION ALL
        SELECT 'ANON', NULL, NULL, 'None', 'Anonymous', false, true""",
    "fato_pedidos": """
        SELECT o.order_id, CAST(strftime(o.order_date, '%Y%m%d') AS INTEGER) AS date_key,
               o.order_datetime_local, o.order_datetime_utc, o.store_id, coalesce(o.customer_id, 'ANON') AS customer_id,
               o.order_channel, o.payment_method, o.order_status, coalesce(i.item_count, 0) AS item_count,
               o.subtotal, o.discount_total, o.vat_total, o.delivery_fee, o.total_amount,
               CASE WHEN o.order_status = 'Completed' THEN o.total_amount ELSE 0 END AS revenue_amount
        FROM orders o
        LEFT JOIN (SELECT order_id, count(*) AS item_count FROM order_items GROUP BY order_id) i USING (order_id)""",
    "fato_vendas": """
        SELECT i.order_item_id, i.order_id, CAST(strftime(o.order_date, '%Y%m%d') AS INTEGER) AS date_key,
               o.store_id, coalesce(o.customer_id, 'ANON') AS customer_id, i.product_id, p.supplier_id, i.promotion_id,
               o.order_channel, o.order_status, o.order_status = 'Completed' AS is_revenue,
               i.quantity, i.unit_price,
               CAST(i.quantity * i.unit_price AS DECIMAL(12,2)) AS gross_amount,
               i.discount_amount, i.line_net_amount AS net_amount, i.line_vat_amount AS vat_amount,
               CAST(i.quantity * p.unit_cost AS DECIMAL(12,2)) AS cost_amount,
               CAST(i.line_net_amount - i.quantity * p.unit_cost AS DECIMAL(12,2)) AS margin_amount
        FROM order_items i
        JOIN orders o USING (order_id)
        JOIN products p USING (product_id)""",
    "fato_estoque": """
        SELECT CAST(strftime(CAST(v._bronze_ingested_at AS DATE), '%Y%m%d') AS INTEGER) AS snapshot_date_key,
               CAST(v._bronze_ingested_at AS DATE) AS snapshot_date,
               v.store_id, v.product_id, v.stock_on_hand, v.stock_on_order, p.reorder_level,
               v.stock_on_hand < p.reorder_level AS below_reorder, v.last_restock_date, v.aisle_location
        FROM inventory v JOIN products p USING (product_id)""",
}
SILVER = ["orders", "order_items", "customers", "products", "suppliers", "stores", "inventory", "promotions"]


def build(silver_dir, gold_dir) -> dict:
    """Build every gold table from the silver lake; return the rows of each."""
    silver_dir, gold_dir = Path(silver_dir), Path(gold_dir)
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    for table in SILVER:
        con.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{(silver_dir / table).as_posix()}/*.parquet')")
    counts = {}
    for name, sql in TABLES.items():
        write(con, sql, gold_dir / name)
        counts[name] = con.execute(f"SELECT count(*) FROM read_parquet('{(gold_dir / name).as_posix()}/*.parquet')").fetchone()[0]
    return counts
