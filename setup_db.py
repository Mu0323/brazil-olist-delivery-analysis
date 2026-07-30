"""
setup_db.py - Olist 电商数据一键建库脚本
用法： python setup_db.py
       python setup_db.py --reset    # 重建数据库

依赖： pip install duckdb
"""

import duckdb
import os
import sys
import time

# === 配置 ===
DATA_DIR = os.path.join(os.path.dirname(__file__), "项目", "archive")
DB_PATH = os.path.join(os.path.dirname(__file__), "smartquery.duckdb")

# 核心表清单（只导入需要用到的5张核心表 + 辅助表）
TABLES = {
    "customers":     "olist_customers_dataset.csv",
    "orders":        "olist_orders_dataset.csv",
    "order_items":   "olist_order_items_dataset.csv",
    "order_payments":"olist_order_payments_dataset.csv",
    "products":      "olist_products_dataset.csv",
    "sellers":       "olist_sellers_dataset.csv",
    "order_reviews":    "olist_order_reviews_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# === 建表SQL（指定列名和类型，比自动推断更可靠）===
SCHEMA_SQL = {
    "customers": """
        CREATE TABLE customers AS
        SELECT * FROM read_csv_auto('{path}')
    """,
    "orders": """
        CREATE TABLE orders AS
        SELECT * FROM read_csv_auto('{path}')
    """,
    "order_items": """
        CREATE TABLE order_items AS
        SELECT * FROM read_csv_auto('{path}')
    """,
    "order_payments": """
        CREATE TABLE order_payments AS
        SELECT * FROM read_csv_auto('{path}')
    """,
    "products": """
        CREATE TABLE products AS
        SELECT * FROM read_csv_auto('{path}')
    """,
    "sellers": """
        CREATE TABLE sellers AS
        SELECT * FROM read_csv_auto('{path}')
    """,
    "order_reviews": """
        CREATE TABLE order_reviews AS
        SELECT * FROM read_csv_auto('{path}')
    """,
    "category_translation": """
        CREATE TABLE category_translation AS
        SELECT * FROM read_csv_auto('{path}')
    """,
}

# === 建索引 + 视图 ===
INDEX_SQL = [
    # orders 表索引
    "CREATE INDEX idx_orders_customer ON orders(customer_id)",
    "CREATE INDEX idx_orders_date ON orders(order_purchase_timestamp)",
    # order_items 索引
    "CREATE INDEX idx_items_order ON order_items(order_id)",
    "CREATE INDEX idx_items_product ON order_items(product_id)",
    # 其他表索引
    "CREATE INDEX idx_customer_id ON customers(customer_id)",
    "CREATE INDEX idx_payments_order ON order_payments(order_id)",
    "CREATE INDEX idx_products_id ON products(product_id)",
]

VIEWS_SQL = [
    # 视图1：订单+客户+金额（最常用的宽表）
    """
    CREATE OR REPLACE VIEW v_order_summary AS
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
        oi.price,
        oi.freight_value,
        oi.product_id,
        p.product_category_name,
        ct.product_category_name_english,
        op.payment_type,
        op.payment_installments,
        op.payment_value
    FROM orders o
    LEFT JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN order_items oi ON o.order_id = oi.order_id
    LEFT JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
    LEFT JOIN order_payments op ON o.order_id = op.order_id
    """,

    # 视图2：用户维度聚合（用于RFM）
    """
    CREATE OR REPLACE VIEW v_customer_metrics AS
    SELECT
        o.customer_id,
        c.customer_unique_id,
        c.customer_city,
        c.customer_state,
        MAX(o.order_purchase_timestamp) AS last_order_date,
        MIN(o.order_purchase_timestamp) AS first_order_date,
        COUNT(DISTINCT o.order_id) AS order_count,
        SUM(oi.price) AS total_spend
    FROM orders o
    LEFT JOIN customers c ON o.customer_id = c.customer_id
    LEFT JOIN order_items oi ON o.order_id = oi.order_id
    GROUP BY o.customer_id, c.customer_unique_id, c.customer_city, c.customer_state
    """,
]


# === 主流程 ===
def main():
    if "--reset" in sys.argv and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("已删除旧数据库")

    con = duckdb.connect(DB_PATH)
    start = time.time()

    print("=" * 50)
    print("Olist 电商数据集 - 一键建库")
    print("=" * 50)

    # 1. 导入CSV
    print("\n[1/4] 导入CSV文件...")
    for table_name, file_name in TABLES.items():
        file_path = os.path.join(DATA_DIR, file_name)
        if not os.path.exists(file_path):
            print(f"  [WARN]  文件不存在，跳过: {file_name}")
            continue
        # 先删后建
        con.execute(f"DROP TABLE IF EXISTS {table_name}")
        sql = SCHEMA_SQL[table_name].format(path=file_path.replace("\\", "/"))
        con.execute(sql)
        # 统计行数
        row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  [OK] {table_name}: {row_count:,} 行")

    # 2. 建索引
    print("\n[2/4] 创建索引...")
    for sql in INDEX_SQL:
        try:
            con.execute(sql)
        except Exception as e:
            print(f"  [WARN]  索引跳过 ({e})")

    # 3. 创建视图
    print("\n[3/4] 创建分析视图...")
    for sql in VIEWS_SQL:
        try:
            con.execute(sql)
        except Exception as e:
            print(f"  [WARN]  视图创建失败: {e}")
    print("  [OK] 视图已创建")

    # 4. 验证
    print("\n[4/4] 验证...")
    tables = con.execute("SHOW TABLES").fetchall()
    print(f"  数据库中共 {len(tables)} 张表:")
    for t in tables:
        row_count = con.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
        print(f"    [DATA] {t[0]}: {row_count:,} 行")

    views = con.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
    for v in views:
        print(f"    [VIEW]  {v[0]} (视图)")

    elapsed = time.time() - start
    print(f"\n[OK] 建库完成！耗时 {elapsed:.1f} 秒")
    print(f"[FILE] 数据库文件: {DB_PATH}")

    # 运行一个简单查询验证
    print("\n[DATA] 快速验证：各州订单分布 Top5")
    result = con.execute("""
        SELECT c.customer_state, COUNT(*) as order_count
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        GROUP BY c.customer_state
        ORDER BY order_count DESC
        LIMIT 5
    """).fetchall()
    for row in result:
        print(f"  {row[0]}: {row[1]:,} 单")

    con.close()


if __name__ == "__main__":
    main()
