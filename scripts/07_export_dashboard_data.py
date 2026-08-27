"""导出 GitHub Pages 看板所需的轻量级 JSON 数据。

运行：
    python scripts/07_export_dashboard_data.py
"""

import json
from pathlib import Path

import duckdb


项目目录 = Path(__file__).resolve().parents[1]
数据库路径 = 项目目录 / "data" / "processed" / "olist.duckdb"
输出路径 = 项目目录 / "dashboard" / "data" / "olist-dashboard.json"
脚本输出路径 = 项目目录 / "dashboard" / "data" / "olist-dashboard-data.js"
统计摘要路径 = 项目目录 / "outputs" / "metrics" / "statistical-summary.json"


def 查询记录(连接, 语句):
    数据框 = 连接.execute(语句).fetchdf()
    return json.loads(数据框.to_json(orient="records"))


def 主程序():
    输出路径.parent.mkdir(parents=True, exist_ok=True)

    if not 统计摘要路径.exists():
        raise FileNotFoundError(
            f"找不到统计摘要：{统计摘要路径}。"
            "请先运行 scripts/05_statistical_validation.py。"
        )

    with duckdb.connect(str(数据库路径), read_only=True) as 连接:
        数据 = {
            "summary": 查询记录(
                连接,
                """
                SELECT
                    COUNT(*) AS deliveredOrders,
                    SUM(is_delayed) AS delayedOrders,
                    ROUND(AVG(is_delayed) * 100, 2) AS delayRate,
                    ROUND(AVG(CASE WHEN review_score IS NOT NULL THEN review_score END), 2) AS averageScore
                FROM v_order_delay
                """,
            )[0],
            "delayComparison": 查询记录(
                连接,
                """
                SELECT
                    is_delayed AS delayed,
                    COUNT(*) AS orders,
                    ROUND(AVG(review_score), 2) AS score,
                    ROUND(AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) * 100, 2) AS badRate
                FROM v_order_delay
                WHERE review_score IS NOT NULL
                GROUP BY is_delayed
                ORDER BY is_delayed
                """,
            ),
            "monthly": 查询记录(
                连接,
                """
                SELECT
                    下单月份 AS month,
                    COUNT(*) AS orders,
                    ROUND(SUM(商品GMV), 2) AS gmv,
                    ROUND(AVG(订单含运费金额), 2) AS aov
                FROM v_order_facts
                WHERE order_status NOT IN ('canceled', 'unavailable')
                  AND 商品GMV IS NOT NULL
                GROUP BY 下单月份
                ORDER BY 下单月份
                """,
            ),
            "delayBuckets": 查询记录(
                连接,
                """
                SELECT
                    CASE
                        WHEN is_delayed = 0 THEN '按时或提前'
                        WHEN delay_days = 0 THEN '延误不足1天'
                        WHEN delay_days <= 2 THEN '延误1-2天'
                        WHEN delay_days <= 5 THEN '延误3-5天'
                        WHEN delay_days <= 10 THEN '延误6-10天'
                        ELSE '延误11天及以上'
                    END AS bucket,
                    COUNT(*) AS orders,
                    ROUND(AVG(review_score), 2) AS score,
                    ROUND(AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) * 100, 2) AS badRate,
                    MIN(CASE WHEN is_delayed = 0 THEN -1 ELSE delay_days END) AS sortKey
                FROM v_order_delay
                WHERE review_score IS NOT NULL
                GROUP BY bucket
                ORDER BY sortKey
                """,
            ),
            "priority": 查询记录(
                连接,
                """
                WITH experience AS (
                    SELECT
                        category.品类 AS category,
                        delay.is_delayed,
                        delay.review_score
                    FROM v_order_category category
                    JOIN v_order_delay delay ON category.order_id = delay.order_id
                    WHERE delay.review_score IS NOT NULL
                ), category_metrics AS (
                    SELECT
                        category,
                        SUM(CASE WHEN is_delayed = 0 THEN 1 ELSE 0 END) AS ontimeOrders,
                        SUM(CASE WHEN is_delayed = 1 THEN 1 ELSE 0 END) AS delayedOrders,
                        AVG(CASE WHEN is_delayed = 0 AND review_score <= 2 THEN 1 WHEN is_delayed = 0 THEN 0 END) AS ontimeBadRate,
                        AVG(CASE WHEN is_delayed = 1 AND review_score <= 2 THEN 1 WHEN is_delayed = 1 THEN 0 END) AS delayedBadRate
                    FROM experience
                    GROUP BY category
                ), sales AS (
                    SELECT
                        品类 AS category,
                        ROUND(SUM(price), 2) AS gmv
                    FROM v_order_item_detail
                    WHERE order_status NOT IN ('canceled', 'unavailable')
                      AND 品类 IS NOT NULL
                    GROUP BY 品类
                )
                SELECT
                    metric.category,
                    sales.gmv,
                    metric.delayedOrders,
                    ROUND((metric.delayedBadRate - metric.ontimeBadRate) * 100, 2) AS badRateLift,
                    ROUND(metric.delayedOrders * (metric.delayedBadRate - metric.ontimeBadRate), 0) AS risk
                FROM category_metrics metric
                JOIN sales ON metric.category = sales.category
                WHERE metric.ontimeOrders >= 30 AND metric.delayedOrders >= 30
                ORDER BY risk DESC
                LIMIT 20
                """,
            ),
            "funnel": 查询记录(
                连接,
                """
                SELECT
                    COUNT(*) AS created,
                    SUM(is_approved) AS approved,
                    SUM(is_shipped) AS shipped,
                    SUM(is_delivered) AS delivered
                FROM v_order_delivery
                """,
            )[0],
        }

    统计摘要 = json.loads(统计摘要路径.read_text(encoding="utf-8"))
    数据["analysis"] = {
        "adjustedGap": 统计摘要["adjustedGap"],
        "oddsRatio": 统计摘要["oddsRatio"],
        "confidenceInterval": 统计摘要["confidenceInterval"],
        "pValue": 统计摘要["pValue"],
    }
    输出路径.write_text(
        json.dumps(数据, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    脚本输出路径.write_text(
        "window.OLIST_DASHBOARD_DATA = "
        + json.dumps(数据, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    print(f"已导出：{输出路径}")
    print(f"已导出：{脚本输出路径}")


if __name__ == "__main__":
    主程序()
