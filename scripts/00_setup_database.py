"""从 Olist 原始 CSV 创建 DuckDB，并建立项目分析视图。

运行：python scripts/00_setup_database.py
"""

from pathlib import Path
import runpy

import duckdb


项目目录 = Path(__file__).resolve().parents[1]
原始数据目录 = 项目目录 / "data" / "raw"
数据库路径 = 项目目录 / "data" / "processed" / "olist.duckdb"

数据表 = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}


def 主程序() -> None:
    缺失文件 = [文件名 for 文件名 in 数据表.values() if not (原始数据目录 / 文件名).exists()]
    if 缺失文件:
        缺失列表 = "\n".join(f"- {文件名}" for 文件名 in 缺失文件)
        raise FileNotFoundError(
            f"data/raw 缺少以下 Olist 原始文件：\n{缺失列表}\n"
            "请先按照 data/README.md 下载并解压数据。"
        )

    数据库路径.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(数据库路径)) as 连接:
        for 表名, 文件名 in 数据表.items():
            文件路径 = 原始数据目录 / 文件名
            连接.execute(
                f"""
                CREATE OR REPLACE TABLE {表名} AS
                SELECT * FROM read_csv_auto(?, header = true, sample_size = -1)
                """,
                [str(文件路径)],
            )
            行数 = 连接.execute(f"SELECT COUNT(*) FROM {表名}").fetchone()[0]
            print(f"[完成] {表名}: {行数:,} 行")

    runpy.run_path(str(项目目录 / "scripts" / "data_cleaning.py"), run_name="__main__")
    print(f"\n数据库已生成：{数据库路径}")


if __name__ == "__main__":
    主程序()
