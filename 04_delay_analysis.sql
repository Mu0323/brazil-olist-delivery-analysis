-- ============================================
-- 04_delay_analysis.sql
-- 物流延误对客户评价/体验的影响
-- 口径：延误率、差评率等订单级指标一律用 v_order_delay（按 order_id 去重）
-- 品类对比用「订单×品类」去重，避免支付/评价一对多膨胀
-- ============================================

-- 1. 延误率概览（订单级）
SELECT 
    ROUND(100.0 * SUM(is_delayed) / COUNT(*), 2) as delay_rate,
    ROUND(AVG(CASE WHEN is_delayed = 1 THEN delay_days END), 1) as avg_delay_days,
    MAX(delay_days) as max_delay,
    COUNT(*) as total_orders
FROM v_order_delay;

-- 2. 延误 vs 准点 评分对比（订单级）
SELECT 
    is_delayed,
    COUNT(*) as order_count,
    ROUND(AVG(review_score), 2) as avg_score,
    ROUND(100.0 * SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) as bad_review_rate
FROM v_order_delay
WHERE review_score IS NOT NULL
GROUP BY is_delayed;

-- 3. 延误天数分箱 —— 容忍度阈值（订单级）
SELECT 
    CASE 
        WHEN delay_days <= 0 THEN '准时/提前'
        WHEN delay_days BETWEEN 1 AND 3 THEN '1-3天'
        WHEN delay_days BETWEEN 4 AND 7 THEN '4-7天'
        WHEN delay_days BETWEEN 8 AND 15 THEN '8-15天'
        ELSE '16天以上'
    END as delay_range,
    COUNT(*) as order_count,
    ROUND(AVG(review_score), 2) as avg_score,
    ROUND(100.0 * SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) as bad_rate,
    ROUND(100.0 * SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END) / COUNT(*), 2) as good_rate
FROM v_order_delay
WHERE review_score IS NOT NULL
GROUP BY delay_range
ORDER BY MIN(delay_days);

-- 4. 同品类分层对比（控制混淆变量）
-- 先按 order_id + category 去重，避免支付/评价 JOIN 膨胀
WITH order_category AS (
    SELECT DISTINCT
        order_id,
        product_category_name_english AS category,
        is_delayed,
        review_score
    FROM v_analysis_base
    WHERE review_score IS NOT NULL
      AND product_category_name_english IS NOT NULL
      AND delay_days IS NOT NULL
)
SELECT 
    category,
    COUNT(*) as order_count,
    ROUND(AVG(CASE WHEN is_delayed = 1 THEN review_score END), 2) as delayed_avg,
    ROUND(AVG(CASE WHEN is_delayed = 0 THEN review_score END), 2) as ontime_avg,
    ROUND(AVG(CASE WHEN is_delayed = 1 THEN review_score END) 
        - AVG(CASE WHEN is_delayed = 0 THEN review_score END), 2) as score_diff
FROM order_category
GROUP BY category
HAVING COUNT(*) >= 200
ORDER BY score_diff ASC
LIMIT 15;

-- 5. 各品类延误率排名（订单×品类去重）
WITH order_category AS (
    SELECT DISTINCT
        order_id,
        product_category_name_english AS category,
        is_delayed,
        delay_days
    FROM v_analysis_base
    WHERE product_category_name_english IS NOT NULL
      AND delay_days IS NOT NULL
)
SELECT 
    category,
    COUNT(*) as total,
    ROUND(100.0 * SUM(is_delayed) / COUNT(*), 2) as delay_rate,
    ROUND(AVG(CASE WHEN is_delayed = 1 THEN delay_days END), 1) as avg_delay_when_late
FROM order_category
GROUP BY category
HAVING COUNT(*) >= 200
ORDER BY delay_rate DESC
LIMIT 15;
