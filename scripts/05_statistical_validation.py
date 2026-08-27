"""延误与差评的统计验证。

运行：python scripts/05_statistical_validation.py
输出：双比例 Z 检验、95% 置信区间、控制品类/州/订单金额的逻辑回归。
"""

import json
from math import sqrt
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import norm
import statsmodels.formula.api as smf
from statsmodels.genmod.families import Binomial
from statsmodels.stats.proportion import proportions_ztest


项目目录 = Path(__file__).resolve().parents[1]
数据库路径 = 项目目录 / "data" / "processed" / "olist.duckdb"
输出路径 = 项目目录 / "outputs" / "metrics" / "statistical-summary.json"


def 读取对比样本(连接: duckdb.DuckDBPyConnection):
    return 连接.execute(
        """
        SELECT
            is_delayed AS 是否延误,
            COUNT(*) AS 订单数,
            SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) AS 差评订单数
        FROM v_order_delay
        WHERE review_score IS NOT NULL
        GROUP BY is_delayed
        ORDER BY is_delayed
        """
    ).fetchdf()


def 构建建模数据(连接: duckdb.DuckDBPyConnection):
    return 连接.execute(
        """
        WITH 订单商品汇总 AS (
            SELECT
                order_id,
                COUNT(DISTINCT 品类) AS 订单包含品类数,
                MIN(品类) AS 品类
            FROM v_order_category
            GROUP BY order_id
        )
        SELECT
            CASE WHEN 延误.review_score <= 2 THEN 1 ELSE 0 END AS 是否差评,
            延误.is_delayed AS 是否延误,
            延误.订单含运费金额,
            商品.品类,
            延误.customer_state AS 客户州
        FROM v_order_delay 延误
        JOIN 订单商品汇总 商品 ON 延误.order_id = 商品.order_id
        WHERE 延误.review_score IS NOT NULL
          AND 商品.订单包含品类数 = 1
          AND 商品.品类 IS NOT NULL
          AND 延误.customer_state IS NOT NULL
          AND 延误.订单含运费金额 IS NOT NULL
        """
    ).fetchdf()


def 主程序() -> None:
    with duckdb.connect(str(数据库路径), read_only=True) as 连接:
        对比样本 = 读取对比样本(连接)
        建模数据 = 构建建模数据(连接)

    差评数 = 对比样本["差评订单数"].to_numpy()
    样本数 = 对比样本["订单数"].to_numpy()
    z统计量, p值 = proportions_ztest(差评数, 样本数, alternative="two-sided")

    未延误率, 延误率 = 差评数 / 样本数
    差异 = 延误率 - 未延误率
    标准误 = sqrt(
        延误率 * (1 - 延误率) / 样本数[1]
        + 未延误率 * (1 - 未延误率) / 样本数[0]
    )
    临界值 = norm.ppf(0.975)

    print("=== 两比例 Z 检验 ===")
    print(对比样本.to_string(index=False))
    print(f"Z 统计量：{z统计量:.2f}")
    print(f"P 值：{'< 0.001' if p值 < 0.001 else f'{p值:.6g}'}")
    print(f"差评率差异：{差异 * 100:.2f} 个百分点")
    print(
        "95% 置信区间："
        f"[{(差异 - 临界值 * 标准误) * 100:.2f}, "
        f"{(差异 + 临界值 * 标准误) * 100:.2f}] 个百分点"
    )

    模型数据 = 建模数据.rename(
        columns={
            "是否差评": "bad_review",
            "是否延误": "is_delayed",
            "订单含运费金额": "order_value",
            "品类": "category",
            "客户州": "customer_state",
        }
    )
    # GLM 二项分布与逻辑链接和 Logit 同样适合二元目标，但对本项目大量类别哑变量更稳健。
    模型 = smf.glm(
        "bad_review ~ is_delayed + np.log1p(order_value) + C(category) + C(customer_state)",
        data=模型数据,
        family=Binomial(),
    ).fit()

    延误系数 = 模型.params["is_delayed"]
    未延误情景 = 模型数据.copy()
    未延误情景["is_delayed"] = 0
    延误情景 = 模型数据.copy()
    延误情景["is_delayed"] = 1

    print("\n=== 逻辑回归（控制品类、客户州、订单金额）===")
    print(f"建模订单数：{len(模型数据):,}")
    print(f"延误优势比：{np.exp(延误系数):.2f}")
    延误模型P值 = 模型.pvalues["is_delayed"]
    print(f"延误 P 值：{'< 0.001' if 延误模型P值 < 0.001 else f'{延误模型P值:.6g}'}")
    未延误预测率 = 模型.predict(未延误情景).mean()
    延误预测率 = 模型.predict(延误情景).mean()
    print(f"未延误预测差评率：{未延误预测率 * 100:.2f}%")
    print(f"延误预测差评率：{延误预测率 * 100:.2f}%")

    统计摘要 = {
        "unadjustedGap": round(差异 * 100, 2),
        "confidenceInterval": [
            round((差异 - 临界值 * 标准误) * 100, 2),
            round((差异 + 临界值 * 标准误) * 100, 2),
        ],
        "pValue": "< 0.001" if p值 < 0.001 else f"{p值:.6g}",
        "modelOrders": len(模型数据),
        "oddsRatio": round(float(np.exp(延误系数)), 2),
        "adjustedOnTimeBadRate": round(float(未延误预测率 * 100), 2),
        "adjustedDelayedBadRate": round(float(延误预测率 * 100), 2),
        "adjustedGap": round(float((延误预测率 - 未延误预测率) * 100), 2),
    }
    输出路径.parent.mkdir(parents=True, exist_ok=True)
    输出路径.write_text(
        json.dumps(统计摘要, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"统计摘要已导出：{输出路径}")


if __name__ == "__main__":
    主程序()
