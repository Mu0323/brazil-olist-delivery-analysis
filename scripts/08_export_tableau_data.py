"""导出 Tableau 看板使用的订单级和订单×品类级 CSV。

运行：python scripts/08_export_tableau_data.py
"""

from pathlib import Path

import duckdb


项目目录 = Path(__file__).resolve().parents[1]
数据库路径 = 项目目录 / "data" / "processed" / "olist.duckdb"
输出目录 = 项目目录 / "outputs" / "tableau"


def 主程序() -> None:
    if not 数据库路径.exists():
        raise FileNotFoundError(
            f"找不到数据库：{数据库路径}。请先运行 scripts/00_setup_database.py。"
        )

    输出目录.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(数据库路径), read_only=True) as 连接:
        订单级数据 = 连接.execute(
            """
            SELECT
                order_id AS 订单ID,
                customer_unique_id AS 真实客户ID,
                customer_state AS 客户州代码,
                CASE customer_state
                    WHEN 'AC' THEN 'Acre' WHEN 'AL' THEN 'Alagoas' WHEN 'AM' THEN 'Amazonas'
                    WHEN 'AP' THEN 'Amapa' WHEN 'BA' THEN 'Bahia' WHEN 'CE' THEN 'Ceara'
                    WHEN 'DF' THEN 'Distrito Federal' WHEN 'ES' THEN 'Espirito Santo' WHEN 'GO' THEN 'Goias'
                    WHEN 'MA' THEN 'Maranhao' WHEN 'MG' THEN 'Minas Gerais' WHEN 'MS' THEN 'Mato Grosso do Sul'
                    WHEN 'MT' THEN 'Mato Grosso' WHEN 'PA' THEN 'Para' WHEN 'PB' THEN 'Paraiba'
                    WHEN 'PE' THEN 'Pernambuco' WHEN 'PI' THEN 'Piaui' WHEN 'PR' THEN 'Parana'
                    WHEN 'RJ' THEN 'Rio de Janeiro' WHEN 'RN' THEN 'Rio Grande do Norte'
                    WHEN 'RO' THEN 'Rondonia' WHEN 'RR' THEN 'Roraima' WHEN 'RS' THEN 'Rio Grande do Sul'
                    WHEN 'SC' THEN 'Santa Catarina' WHEN 'SE' THEN 'Sergipe' WHEN 'SP' THEN 'Sao Paulo'
                    WHEN 'TO' THEN 'Tocantins'
                END AS 客户州全称,
                'Brazil' AS 国家,
                order_status AS 订单状态,
                order_purchase_timestamp AS 下单时间,
                order_approved_at AS 付款批准时间,
                order_delivered_carrier_date AS 发货时间,
                order_delivered_customer_date AS 实际送达时间,
                order_estimated_delivery_date AS 承诺送达时间,
                下单月份,
                商品明细数,
                商品种类数,
                商品GMV,
                运费总额,
                订单含运费金额,
                支付记录数,
                支付总金额,
                最大分期数,
                review_score AS 评价分数,
                评价记录数,
                actual_delivery_days AS 实际配送天数,
                estimated_delivery_days AS 承诺配送天数,
                delay_days AS 延误完整天数,
                is_delayed AS 是否延误,
                CASE WHEN review_score <= 2 THEN 1 WHEN review_score IS NOT NULL THEN 0 END AS 是否差评,
                CASE WHEN order_approved_at IS NOT NULL THEN 1 ELSE 0 END AS 是否批准,
                CASE WHEN order_delivered_carrier_date IS NOT NULL THEN 1 ELSE 0 END AS 是否发货,
                CASE WHEN order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END AS 是否送达
            FROM v_order_facts
            """
        ).fetchdf()

        订单品类数据 = 连接.execute(
            """
            WITH 品类金额 AS (
                SELECT
                    明细.order_id,
                    明细.品类,
                    SUM(明细.price) AS 品类商品GMV,
                    SUM(明细.freight_value) AS 品类运费总额
                FROM v_order_item_detail 明细
                WHERE 明细.品类 IS NOT NULL
                GROUP BY 明细.order_id, 明细.品类
            )
            SELECT
                品类金额.order_id AS 订单ID,
                品类金额.品类,
                订单.customer_state AS 客户州代码,
                订单.下单月份,
                品类金额.品类商品GMV,
                品类金额.品类运费总额,
                品类金额.品类商品GMV + 品类金额.品类运费总额 AS 品类含运费金额,
                订单.review_score AS 评价分数,
                订单.is_delayed AS 是否延误,
                订单.delay_days AS 延误完整天数,
                CASE WHEN 订单.review_score <= 2 THEN 1 WHEN 订单.review_score IS NOT NULL THEN 0 END AS 是否差评
            FROM 品类金额
            JOIN v_order_facts 订单 ON 品类金额.order_id = 订单.order_id
            """
        ).fetchdf()

    订单级路径 = 输出目录 / "olist_order_facts_tableau.csv"
    品类路径 = 输出目录 / "olist_order_category_tableau.csv"
    订单级数据.to_csv(订单级路径, index=False, encoding="utf-8-sig")
    订单品类数据.to_csv(品类路径, index=False, encoding="utf-8-sig")

    print(f"[完成] {订单级路径}: {len(订单级数据):,} 行")
    print(f"[完成] {品类路径}: {len(订单品类数据):,} 行")


if __name__ == "__main__":
    主程序()
