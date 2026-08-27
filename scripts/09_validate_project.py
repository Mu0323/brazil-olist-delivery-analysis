"""验证关键数据、导出文件和 Dashboard 数据是否一致。

运行：python scripts/09_validate_project.py
"""

import json
from pathlib import Path

import duckdb


项目目录 = Path(__file__).resolve().parents[1]
数据库路径 = 项目目录 / "data" / "processed" / "olist.duckdb"
Dashboard数据路径 = 项目目录 / "dashboard" / "data" / "olist-dashboard.json"


def 主程序() -> None:
    必需文件 = [
        Dashboard数据路径,
        项目目录 / "dashboard" / "data" / "olist-dashboard-data.js",
        项目目录 / "dashboard" / "assets" / "tableau-dashboard.png",
        项目目录 / "outputs" / "tableau" / "olist-business-dashboard.twb",
    ]
    缺失 = [str(path.relative_to(项目目录)) for path in 必需文件 if not path.exists()]
    if 缺失:
        raise FileNotFoundError("缺少项目输出：\n- " + "\n- ".join(缺失))

    with duckdb.connect(str(数据库路径), read_only=True) as 连接:
        指标 = 连接.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM orders) AS created,
                (SELECT COUNT(*) FROM v_order_delay) AS delivered,
                (SELECT SUM(is_delayed) FROM v_order_delay) AS delayed
            """
        ).fetchone()

    期望值 = (99_441, 96_476, 7_827)
    if tuple(int(value) for value in 指标) != 期望值:
        raise AssertionError(f"关键指标与当前项目基准不一致：{指标} != {期望值}")

    Dashboard数据 = json.loads(Dashboard数据路径.read_text(encoding="utf-8"))
    Dashboard指标 = (
        int(Dashboard数据["funnel"]["created"]),
        int(Dashboard数据["summary"]["deliveredOrders"]),
        int(Dashboard数据["summary"]["delayedOrders"]),
    )
    if Dashboard指标 != 期望值:
        raise AssertionError(f"Dashboard 数据与数据库不一致：{Dashboard指标} != {期望值}")

    print("[通过] 数据库关键指标")
    print("[通过] Dashboard JSON 与数据库一致")
    print("[通过] Tableau 和页面资源齐全")


if __name__ == "__main__":
    主程序()
