# 数据目录

原始数据来自 Olist 在 Kaggle 发布的 [Brazilian E-Commerce Public Dataset](https://www.kaggle.com/olistbr/brazilian-ecommerce)。数据覆盖2016–2018年。

为控制仓库体积并遵守数据源的使用要求，原始 CSV、派生 CSV 和 DuckDB 数据库均不提交到 Git。下载后请将以下文件放入 `data/raw/`：

```text
olist_customers_dataset.csv
olist_geolocation_dataset.csv
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
product_category_name_translation.csv
```

随后运行：

```bash
python scripts/00_setup_database.py
```

脚本会在 `data/processed/olist.duckdb` 创建本地数据库，并自动建立项目使用的分析视图。

如果已经配置 Kaggle API，也可以在仓库根目录运行：

```bash
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip
```
