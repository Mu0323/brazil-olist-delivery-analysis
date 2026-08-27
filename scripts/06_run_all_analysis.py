"""在 Jupyter 或命令行中顺序运行全部业务分析 SQL。

运行：
    python scripts/06_run_all_analysis.py

前提：先运行 data_cleaning.py，建立最新分析视图。
"""

import re
from pathlib import Path
from typing import List

import duckdb


项目目录 = Path(__file__).resolve().parents[1]
数据库路径 = 项目目录 / "data" / "processed" / "olist.duckdb"
分析文件 = [
    ("01 核心经营指标", "01_core_metrics.sql"),
    ("02 履约漏斗", "02_funnel.sql"),
    ("03 客户购买行为", "03_rfm.sql"),
    ("04 延误与客户体验", "04_delay_analysis.sql"),
]


def 拆分SQL(原文: str) -> List[str]:
    """去除单行注释后，按分号拆分当前项目中的 SQL 语句。"""
    无注释文本 = re.sub(r"(?m)^\s*--.*$", "", 原文)
    return [语句.strip() for 语句 in 无注释文本.split(";") if 语句.strip()]


def 展示结果(结果表) -> None:
    try:
        from IPython.display import display

        display(结果表)
    except ImportError:
        print(结果表.to_string(index=False))


def 主程序() -> None:
    if not 数据库路径.exists():
        raise FileNotFoundError(f"找不到数据库：{数据库路径}")

    with duckdb.connect(str(数据库路径)) as 连接:
        for 模块名, 文件名 in 分析文件:
            文件路径 = 项目目录 / "scripts" / 文件名
            print(f"\n{'=' * 72}\n{模块名}\n{'=' * 72}")

            for 序号, 语句 in enumerate(拆分SQL(文件路径.read_text(encoding="utf-8-sig")), start=1):
                print(f"\n[{模块名} · 查询 {序号}]")
                执行结果 = 连接.execute(语句)

                if 语句.lstrip().upper().startswith(("SELECT", "WITH")):
                    展示结果(执行结果.fetchdf())
                else:
                    print("视图已更新。")


if __name__ == "__main__":
    主程序()
