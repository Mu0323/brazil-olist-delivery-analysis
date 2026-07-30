-- ============================================
-- 01_core_metrics.sql
-- Olist 电商核心指标计算
-- 基于清洗后的 v_analysis_base 视图
-- ============================================

-- 1. GMV 月度趋势
-- 说明：按月统计总销售额（price+freight），去掉 canceled 和 unavailable 订单
SELECT 
    order_month,
    COUNT(DISTINCT order_id) as order_count,
    ROUND(SUM(total_item_value), 2) as gmv,
    ROUND(AVG(total_item_value), 2) as avg_order_value,
    ROUND(SUM(total_item_value) / COUNT(DISTINCT order_id), 2) as aov_by_order
FROM v_analysis_base
GROUP BY order_month
ORDER BY order_month;

-- 2. 各州销售额排名
SELECT 
    customer_state,
    COUNT(DISTINCT order_id) as order_count,
    ROUND(SUM(total_item_value), 2) as total_sales,
    ROUND(AVG(total_item_value), 2) as avg_order_value,
    ROUND(SUM(total_item_value) * 100.0 / SUM(SUM(total_item_value)) OVER(), 2) as sales_pct
FROM v_analysis_base
GROUP BY customer_state
ORDER BY total_sales DESC;

-- 3. 支付方式分布
SELECT 
    payment_type,
    COUNT(*) as transaction_count,
    ROUND(SUM(payment_value), 2) as total_amount,
    ROUND(AVG(payment_value), 2) as avg_amount,
    ROUND(AVG(payment_installments), 1) as avg_installments
FROM v_analysis_base
WHERE payment_type IS NOT NULL
GROUP BY payment_type
ORDER BY transaction_count DESC;

-- 4. 商品类别销售额 Top15
SELECT 
    product_category_name_english,
    COUNT(DISTINCT order_id) as order_count,
    ROUND(SUM(price), 2) as total_sales,
    ROUND(AVG(price), 2) as avg_price,
    ROUND(SUM(price) * 100.0 / SUM(SUM(price)) OVER(), 2) as sales_pct
FROM v_analysis_base
WHERE product_category_name_english IS NOT NULL
GROUP BY product_category_name_english
ORDER BY total_sales DESC
LIMIT 15;

-- 5. 评分分布
SELECT 
    review_score,
    COUNT(*) as review_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as pct
FROM v_analysis_base
WHERE review_score IS NOT NULL
GROUP BY review_score
ORDER BY review_score;

-- 6. 月 GMV 变化率（环比）
WITH monthly_gmv AS (
    SELECT 
        order_month,
        ROUND(SUM(total_item_value), 2) as gmv
    FROM v_analysis_base
    GROUP BY order_month
)
SELECT 
    order_month,
    gmv,
    LAG(gmv) OVER (ORDER BY order_month) as prev_month_gmv,
    ROUND((gmv - LAG(gmv) OVER (ORDER BY order_month)) / LAG(gmv) OVER (ORDER BY order_month) * 100, 2) as mom_change_pct
FROM monthly_gmv
ORDER BY order_month;
