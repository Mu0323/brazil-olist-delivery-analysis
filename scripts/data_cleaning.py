"""建立 Olist 分析数据层。

运行：python scripts/data_cleaning.py

设计原则：
1. 订单、商品、支付和评价存在一对多关系，先按 order_id 聚合，再连接。
2. 延误以“实际送达时间是否晚于承诺时间”判定，不以整天数比较替代。
3. 订单级指标只使用一笔订单一行的视图。
"""

from pathlib import Path

import duckdb


项目目录 = Path(__file__).resolve().parents[1]
数据库路径 = 项目目录 / "data" / "processed" / "olist.duckdb"

if not 数据库路径.exists():
    raise FileNotFoundError(
        f"找不到数据库：{数据库路径}。请先运行 scripts/00_setup_database.py。"
    )


建模语句 = [
    (
        "业务订单",
        """
        CREATE OR REPLACE VIEW v_business_orders AS
        SELECT *
        FROM orders
        WHERE order_status NOT IN ('canceled', 'unavailable')
        """,
    ),
    (
        "订单商品聚合",
        """
        CREATE OR REPLACE VIEW v_order_items_agg AS
        SELECT
            order_id,
            COUNT(*) AS 商品明细数,
            COUNT(DISTINCT product_id) AS 商品种类数,
            ROUND(SUM(price), 2) AS 商品GMV,
            ROUND(SUM(freight_value), 2) AS 运费总额,
            ROUND(SUM(price + freight_value), 2) AS 订单含运费金额
        FROM order_items
        GROUP BY order_id
        """,
    ),
    (
        "订单支付聚合",
        """
        CREATE OR REPLACE VIEW v_order_payments_agg AS
        SELECT
            order_id,
            COUNT(*) AS 支付记录数,
            COUNT(DISTINCT payment_type) AS 支付方式数,
            ROUND(SUM(payment_value), 2) AS 支付总金额,
            MAX(payment_installments) AS 最大分期数
        FROM order_payments
        GROUP BY order_id
        """,
    ),
    (
        "订单评价聚合",
        """
        CREATE OR REPLACE VIEW v_order_reviews_agg AS
        SELECT
            order_id,
            COUNT(*) AS 评价记录数,
            AVG(review_score) AS 平均评价分数
        FROM order_reviews
        GROUP BY order_id
        """,
    ),
    (
        "订单品类桥表",
        """
        CREATE OR REPLACE VIEW v_order_category AS
        SELECT DISTINCT
            oi.order_id,
            ct.product_category_name_english AS 品类
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        LEFT JOIN category_translation ct
            ON p.product_category_name = ct.product_category_name
        WHERE ct.product_category_name_english IS NOT NULL
        """,
    ),
    (
        "订单级事实表",
        """
        CREATE OR REPLACE VIEW v_order_facts AS
        SELECT
            o.order_id,
            o.customer_id,
            c.customer_unique_id,
            c.customer_city,
            c.customer_state,
            o.order_status,
            o.order_purchase_timestamp,
            o.order_approved_at,
            o.order_delivered_carrier_date,
            o.order_delivered_customer_date,
            o.order_estimated_delivery_date,
            STRFTIME(o.order_purchase_timestamp, '%Y-%m') AS 下单月份,
            商品.商品明细数,
            商品.商品种类数,
            商品.商品GMV,
            商品.运费总额,
            商品.订单含运费金额,
            支付.支付记录数,
            支付.支付方式数,
            支付.支付总金额,
            支付.最大分期数,
            评价.评价记录数,
            评价.平均评价分数 AS review_score,
            DATEDIFF('day', o.order_purchase_timestamp, o.order_delivered_customer_date)
                AS actual_delivery_days,
            DATEDIFF('day', o.order_purchase_timestamp, o.order_estimated_delivery_date)
                AS estimated_delivery_days,
            DATEDIFF('day', o.order_estimated_delivery_date, o.order_delivered_customer_date)
                AS delay_days,
            CASE
                WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1
                WHEN o.order_delivered_customer_date IS NOT NULL THEN 0
                ELSE NULL
            END AS is_delayed
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.customer_id
        LEFT JOIN v_order_items_agg 商品 ON o.order_id = 商品.order_id
        LEFT JOIN v_order_payments_agg 支付 ON o.order_id = 支付.order_id
        LEFT JOIN v_order_reviews_agg 评价 ON o.order_id = 评价.order_id
        """,
    ),
    (
        "履约订单视图",
        """
        CREATE OR REPLACE VIEW v_order_delivery AS
        SELECT
            order_id,
            order_status,
            order_purchase_timestamp,
            order_approved_at,
            order_delivered_carrier_date,
            order_delivered_customer_date,
            order_estimated_delivery_date,
            CASE WHEN order_approved_at IS NOT NULL THEN 1 ELSE 0 END AS is_approved,
            CASE WHEN order_delivered_carrier_date IS NOT NULL THEN 1 ELSE 0 END AS is_shipped,
            CASE WHEN order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END AS is_delivered,
            CASE
                WHEN order_delivered_customer_date <= order_estimated_delivery_date THEN 1
                WHEN order_delivered_customer_date IS NOT NULL THEN 0
                ELSE NULL
            END AS is_on_time,
            actual_delivery_days,
            estimated_delivery_days,
            delay_days,
            is_delayed
        FROM v_order_facts
        """,
    ),
    (
        "延误分析订单视图",
        """
        CREATE OR REPLACE VIEW v_order_delay AS
        SELECT *
        FROM v_order_facts
        WHERE order_delivered_customer_date IS NOT NULL
        """,
    ),
    (
        "订单商品明细视图",
        """
        CREATE OR REPLACE VIEW v_order_item_detail AS
        SELECT
            订单.*,
            oi.order_item_id,
            oi.product_id,
            oi.seller_id,
            oi.price,
            oi.freight_value,
            p.product_category_name,
            ct.product_category_name_english AS 品类
        FROM v_order_facts 订单
        LEFT JOIN order_items oi ON 订单.order_id = oi.order_id
        LEFT JOIN products p ON oi.product_id = p.product_id
        LEFT JOIN category_translation ct
            ON p.product_category_name = ct.product_category_name
        """,
    ),
    (
        "兼容旧宽表名称",
        "CREATE OR REPLACE VIEW v_analysis_base AS SELECT * FROM v_order_item_detail",
    ),
]


def 主程序() -> None:
    with duckdb.connect(str(数据库路径)) as 连接:
        print(f"数据库：{数据库路径}")
        for 名称, 语句 in 建模语句:
            连接.execute(语句)
            print(f"[完成] {名称}")

        核验 = 连接.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM v_order_facts) AS 订单级行数,
                (SELECT COUNT(*) FROM v_order_delay) AS 可计算延误订单数,
                (SELECT COUNT(*) FROM v_order_item_detail) AS 商品明细行数,
                (SELECT COUNT(*) FROM v_order_facts WHERE customer_unique_id IS NULL)
                    AS 客户信息缺失订单数
            """
        ).fetchdf()
        print("\n核验结果：")
        print(核验.to_string(index=False))


if __name__ == "__main__":
    主程序()
