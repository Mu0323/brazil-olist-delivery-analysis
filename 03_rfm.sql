-- ============================================
-- 03_rfm.sql
-- Olist RFM 用户分层分析
-- ============================================

-- 1. 计算每个用户的 RFM 原始值
-- 参考时间点：数据集最后一天 + 1天（2018-10-18）
CREATE OR REPLACE VIEW v_rfm_raw AS
SELECT 
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    DATEDIFF('day', MAX(o.order_purchase_timestamp), '2018-10-18') as recency,
    COUNT(DISTINCT o.order_id) as frequency,
    ROUND(SUM(oi.price), 2) as monetary
FROM v_unique_customers c
JOIN v_valid_orders o ON c.customer_id = o.customer_id
LEFT JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY c.customer_unique_id, c.customer_city, c.customer_state;

-- 2. R/F/M 各分5档（基于百分位数）
CREATE OR REPLACE VIEW v_rfm_scored AS
SELECT 
    *,
    CASE 
        WHEN recency <= (SELECT PERCENTILE_CONT(0.2) WITHIN GROUP (ORDER BY recency) FROM v_rfm_raw) THEN 5
        WHEN recency <= (SELECT PERCENTILE_CONT(0.4) WITHIN GROUP (ORDER BY recency) FROM v_rfm_raw) THEN 4
        WHEN recency <= (SELECT PERCENTILE_CONT(0.6) WITHIN GROUP (ORDER BY recency) FROM v_rfm_raw) THEN 3
        WHEN recency <= (SELECT PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY recency) FROM v_rfm_raw) THEN 2
        ELSE 1
    END as r_score,
    CASE 
        WHEN frequency >= (SELECT PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY frequency) FROM v_rfm_raw) THEN 5
        WHEN frequency >= (SELECT PERCENTILE_CONT(0.6) WITHIN GROUP (ORDER BY frequency) FROM v_rfm_raw) THEN 4
        WHEN frequency >= (SELECT PERCENTILE_CONT(0.4) WITHIN GROUP (ORDER BY frequency) FROM v_rfm_raw) THEN 3
        WHEN frequency >= (SELECT PERCENTILE_CONT(0.2) WITHIN GROUP (ORDER BY frequency) FROM v_rfm_raw) THEN 2
        ELSE 1
    END as f_score,
    CASE 
        WHEN monetary >= (SELECT PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY monetary) FROM v_rfm_raw) THEN 5
        WHEN monetary >= (SELECT PERCENTILE_CONT(0.6) WITHIN GROUP (ORDER BY monetary) FROM v_rfm_raw) THEN 4
        WHEN monetary >= (SELECT PERCENTILE_CONT(0.4) WITHIN GROUP (ORDER BY monetary) FROM v_rfm_raw) THEN 3
        WHEN monetary >= (SELECT PERCENTILE_CONT(0.2) WITHIN GROUP (ORDER BY monetary) FROM v_rfm_raw) THEN 2
        ELSE 1
    END as m_score
FROM v_rfm_raw;

-- 3. 用户分层：按 RFM 总分分群
CREATE OR REPLACE VIEW v_rfm_segments AS
SELECT 
    *,
    (r_score + f_score + m_score) as rfm_total,
    CASE 
        WHEN (r_score >= 4 AND f_score >= 4 AND m_score >= 4) THEN '🌟 重要价值用户'
        WHEN (r_score >= 4 AND f_score >= 4) THEN '⭐ 重要发展用户'
        WHEN (r_score >= 4 AND m_score >= 4) THEN '💰 重要保持用户'
        WHEN (f_score >= 4 AND m_score >= 4) THEN '📈 重要挽留用户'
        WHEN (r_score >= 3) THEN '🟢 一般价值用户'
        WHEN (f_score >= 3) THEN '🟡 一般发展用户'
        WHEN (m_score >= 3) THEN '🔶 一般保持用户'
        ELSE '🔴 流失风险用户'
    END as segment
FROM v_rfm_scored;

-- 4. 各分群的用户数和消费占比
SELECT 
    segment,
    COUNT(*) as customer_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as customer_pct,
    ROUND(AVG(monetary), 2) as avg_spend,
    ROUND(AVG(recency), 1) as avg_recency_days,
    ROUND(SUM(monetary), 2) as total_spend,
    ROUND(SUM(monetary) * 100.0 / SUM(SUM(monetary)) OVER(), 2) as spend_pct
FROM v_rfm_segments
GROUP BY segment
ORDER BY total_spend DESC;

-- 5. 各州 RFM 均值对比
SELECT 
    customer_state,
    COUNT(*) as customer_count,
    ROUND(AVG(recency), 1) as avg_recency,
    ROUND(AVG(frequency), 2) as avg_frequency,
    ROUND(AVG(monetary), 2) as avg_spend,
    ROUND(AVG(r_score), 2) as avg_r,
    ROUND(AVG(f_score), 2) as avg_f,
    ROUND(AVG(m_score), 2) as avg_m,
    ROUND(AVG(rfm_total), 2) as avg_rfm
FROM v_rfm_segments
GROUP BY customer_state
HAVING COUNT(*) > 100
ORDER BY avg_rfm DESC;
