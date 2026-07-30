# Olist 电商数据分析项目（SmartQuery）

基于巴西 Olist 公开电商数据，做 **物流延误 → 客户评价/体验** 分析，并给出履约与补偿建议。

## 这个项目做什么？

| 模块 | 作用 | 入口 |
| :--- | :--- | :--- |
| 数据清洗 | 建有效订单、客户去重、明细宽表、**订单级延误视图** | `scripts/data_cleaning.py` |
| 核心指标 | GMV、品类、支付、州分布等 | `scripts/01_core_metrics.sql` |
| 漏斗 | 下单→送达→评价 | `scripts/02_funnel.sql` |
| RFM | 用户分层（辅线） | `scripts/03_rfm.sql` |
| **延误专题（主线）** | 延误率、容忍度、同品类对比 | `scripts/04_delay_analysis.sql` / `notebooks/01_delay_analysis.ipynb` |
| 分析报告 | 面向阅读的结论与建议 | `分析报告.md` |

## 怎么跑？

1. 准备 DuckDB 库文件 `smartquery.duckdb`（放在项目根目录，或 `E:/workspace/smartquery.duckdb`）。
2. 清洗并创建视图：

```bash
python scripts/data_cleaning.py
```

3. 跑延误分析 SQL，或打开 Notebook：

```bash
# SQL：在 DuckDB 中执行
# scripts/04_delay_analysis.sql

# Notebook
jupyter notebook notebooks/01_delay_analysis.ipynb
```

## 重要口径（必读）

### 两个视图不要混用

| 视图 | 粒度 | 用途 |
| :--- | :--- | :--- |
| `v_analysis_base` | 明细（订单 × 商品 × 支付等，可能多行） | GMV、品类结构、需要明细的 JOIN |
| **`v_order_delay`** | **一单一行（按 order_id 去重）** | **延误率、差评率、容忍度曲线** |

宽表 JOIN 后行数会大于订单数。若直接用 `v_analysis_base` 的 `COUNT(*)` 算延误率/差评率，会被支付、多商品等一对多关系放大。

### 主线与放弃项

- **主线**：延误容忍度阈值 + 同品类分层（控制品类混淆）
- **已放弃**：同客户纵向对比（约九成以上客户只下一单，样本不足）
- **可选后续**：Python `statsmodels` 多元回归
- **不做**：把购物篮硬缝进本项目物流专题（购物篮保留在 QuickMart）

## 目录结构

```
项目/
├── README.md                 # 本说明
├── 代码详解.md               # 全项目代码逐变量/逐查询解析
├── 分析报告.md               # 分析结论
├── 项目大纲.md               # 选题与优化决策记录
├── archive/                  # 原始 CSV
├── notebooks/
│   ├── 00_data_exploration.ipynb
│   └── 01_delay_analysis.ipynb
├── scripts/
│   ├── data_cleaning.py
│   ├── 01_core_metrics.sql
│   ├── 02_funnel.sql
│   ├── 03_rfm.sql
│   └── 04_delay_analysis.sql
└── outputs/                  # 图表输出（运行后生成）
```

## 报告里不会写什么？

未做测算的数字（如「降延误 30–40%」「差评率降到 20%」）已从报告中删除。策略建议只保留方向，量化效果留给上线后验证。

## 已知局限与改进方向

1. RFM 在本数据集区分度有限（单次购买多），仅作辅线。
2. 有空可补：`review_score ~ is_delayed + category + price + state`（statsmodels）。
3. 核心指标 SQL 中涉及 SUM 的部分，若从宽表直接汇总，仍需注意是否应按订单去重后再聚合（后续可按同样口径收紧）。
