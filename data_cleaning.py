"""
data_cleaning.py — Olist 数据清洗
基于 notebook 探索结果，处理已知的数据质量问题。
用法： python scripts/data_cleaning.py
"""

import duckdb
import os

_ROOT = os.path.dirname(os.path.dirname(__file__))
_DB_CANDIDATES = [
    os.path.join(_ROOT, "smartquery.duckdb"),
    os.path.join(os.path.dirname(_ROOT), "smartquery.duckdb"),  # E:/workspace/smartquery.duckdb
]
DB_PATH = next((p for p in _DB_CANDIDATES if os.path.exists(p)), None)
if DB_PATH is None:
    raise FileNotFoundError(
        "找不到 smartquery.duckdb。请放到项目根目录或 E:/workspace/ 下。"
    )
OUTPUT_DIR = os.path.join(_ROOT, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

con = duckdb.connect(DB_PATH)
print(f"使用数据库: {DB_PATH}")

print("=" * 50)
print("Olist 数据清洗")
print("=" * 50)

# 1. 只保留有效订单视图（排除 canceled + unavailable）
print("\n[1/5] 创建 v_valid_orders (有效订单视图)...")
con.execute("""
    CREATE OR REPLACE VIEW v_valid_orders AS
    SELECT * FROM orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
""")
cnt = con.execute("SELECT COUNT(*) FROM v_valid_orders").fetchone()[0]
print(f"  有效订单: {cnt:,} / 99,441")

# 2. 创建去重客户视图（customer_unique_id 去重：取最早出现的记录）
print("\n[2/5] 创建 v_unique_customers (去重客户视图)...")
con.execute("""
    CREATE OR REPLACE VIEW v_unique_customers AS
    SELECT customer_id, customer_unique_id, customer_city, customer_state
    FROM (
        SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY customer_id) as rn
        FROM customers
    ) t
    WHERE rn = 1
""")
cnt = con.execute("SELECT COUNT(*) FROM v_unique_customers").fetchone()[0]
print(f"  去重后客户数: {cnt:,} (原 99,441，去重 {99_441 - cnt:,})")

# 3. 创建订单完成情况视图（用于漏斗分析）
print("\n[3/5] 创建 v_order_delivery (订单送达视图)...")
con.execute("""
    CREATE OR REPLACE VIEW v_order_delivery AS
    SELECT 
        order_id,
        order_status,
        order_purchase_timestamp,
        CASE 
            WHEN order_delivered_customer_date IS NOT NULL THEN 1
            ELSE 0
        END as is_delivered,
        CASE 
            WHEN order_approved_at IS NOT NULL THEN 1
            ELSE 0
        END as is_approved,
        CASE 
            WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN 1
            WHEN order_delivered_customer_date IS NOT NULL THEN 0
            ELSE NULL
        END as is_on_time,
        order_estimated_delivery_date,
        order_delivered_customer_date,
        DATEDIFF('day', order_purchase_timestamp, order_delivered_customer_date) as delivery_days
    FROM orders
    WHERE order_status = 'delivered'
""")
cnt = con.execute("SELECT COUNT(*) FROM v_order_delivery").fetchone()[0]
early = con.execute("SELECT COUNT(*) FROM v_order_delivery WHERE is_on_time = 1").fetchone()[0]
print(f"  已送达订单: {cnt:,}")
print(f"  按时送达: {early:,} ({round(early/cnt*100, 1)}%)")

# 4. 创建分析用主视图（明细粒度：订单×商品×支付，可能一行多行）
print("\n[4/5] 创建 v_analysis_base (分析主视图，明细粒度)...")
con.execute("""
    CREATE OR REPLACE VIEW v_analysis_base AS
    SELECT 
        o.order_id,
        o.customer_id,
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,
        o.order_status,
        o.order_purchase_timestamp,
        o.order_approved_at,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        STRFTIME(o.order_purchase_timestamp, '%Y-%m') as order_month,
        STRFTIME(o.order_purchase_timestamp, '%Y') as order_year,
        oi.product_id,
        p.product_category_name,
        ct.product_category_name_english,
        oi.price,
        oi.freight_value,
        (oi.price + oi.freight_value) as total_item_value,
        op.payment_type,
        op.payment_installments,
        op.payment_value,
        r.review_score,
        DATEDIFF('day', o.order_purchase_timestamp, o.order_delivered_customer_date) as actual_delivery_days,
        DATEDIFF('day', o.order_purchase_timestamp, o.order_estimated_delivery_date) as estimated_delivery_days,
        CASE 
            WHEN o.order_delivered_customer_date IS NOT NULL 
            THEN DATEDIFF('day', o.order_purchase_timestamp, o.order_delivered_customer_date) 
                 - DATEDIFF('day', o.order_purchase_timestamp, o.order_estimated_delivery_date)
            ELSE NULL 
        END as delay_days,
        CASE 
            WHEN o.order_delivered_customer_date IS NOT NULL 
             AND DATEDIFF('day', o.order_purchase_timestamp, o.order_delivered_customer_date) 
                 > DATEDIFF('day', o.order_purchase_timestamp, o.order_estimated_delivery_date)
            THEN 1 
            ELSE 0 
        END as is_delayed
    FROM v_valid_orders o
    LEFT JOIN v_unique_customers c ON o.customer_id = c.customer_id
    LEFT JOIN order_items oi ON o.order_id = oi.order_id
    LEFT JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
    LEFT JOIN order_payments op ON o.order_id = op.order_id
    LEFT JOIN order_reviews r ON o.order_id = r.order_id
""")
row_cnt = con.execute("SELECT COUNT(*) FROM v_analysis_base").fetchone()[0]
print(f"  明细行数: {row_cnt:,}（含一对多 JOIN，订单级指标请用 v_order_delay）")

# 5. 订单级延误视图：一单一行，供延误率/差评率等订单指标使用
print("\n[5/5] 创建 v_order_delay (订单级延误视图，按 order_id 去重)...")
con.execute("""
    CREATE OR REPLACE VIEW v_order_delay AS
    SELECT
        order_id,
        ANY_VALUE(customer_id) AS customer_id,
        ANY_VALUE(customer_unique_id) AS customer_unique_id,
        ANY_VALUE(customer_city) AS customer_city,
        ANY_VALUE(customer_state) AS customer_state,
        ANY_VALUE(order_status) AS order_status,
        ANY_VALUE(order_month) AS order_month,
        ANY_VALUE(actual_delivery_days) AS actual_delivery_days,
        ANY_VALUE(estimated_delivery_days) AS estimated_delivery_days,
        ANY_VALUE(delay_days) AS delay_days,
        ANY_VALUE(is_delayed) AS is_delayed,
        AVG(review_score) AS review_score
    FROM v_analysis_base
    WHERE delay_days IS NOT NULL
    GROUP BY order_id
""")
order_cnt = con.execute("SELECT COUNT(*) FROM v_order_delay").fetchone()[0]
print(f"  订单级数: {order_cnt:,}")

print("\n" + "=" * 50)
print("清洗完成！新增视图：")
print("  v_valid_orders      — 有效订单（排除 canceled/unavailable）")
print("  v_unique_customers  — 去重客户（同一客户只保留一条）")
print("  v_order_delivery    — 订单完成情况（送达率、准时率）")
print("  v_analysis_base     — 明细宽表（订单×商品×支付，可能多行）")
print("  v_order_delay       — 订单级延误（一单一行，算延误率/差评率用这个）")
print("=" * 50)

con.close()
