-- ============================================
-- 02_funnel.sql
-- Olist 电商漏斗分析
-- ============================================

-- 1. 整体漏斗：下单 → 审批 → 发货 → 送达 → 评价
SELECT 
    '下单' as stage,
    COUNT(*) as cnt,
    100.0 as pct
FROM orders
UNION ALL
SELECT 
    '审批通过',
    COUNT(*),
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders), 2)
FROM orders WHERE order_approved_at IS NOT NULL
UNION ALL
SELECT 
    '已发货',
    COUNT(*),
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders), 2)
FROM orders WHERE order_delivered_carrier_date IS NOT NULL
UNION ALL
SELECT 
    '已送达',
    COUNT(*),
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders), 2)
FROM orders WHERE order_delivered_customer_date IS NOT NULL
UNION ALL
SELECT 
    '已评价',
    COUNT(DISTINCT order_id),
    ROUND(COUNT(DISTINCT order_id) * 100.0 / (SELECT COUNT(*) FROM orders), 2)
FROM order_reviews;

-- 2. 分月漏斗转化率
WITH monthly_funnel AS (
    SELECT 
        STRFTIME(order_purchase_timestamp, '%Y-%m') as month,
        COUNT(*) as total_orders,
        SUM(CASE WHEN order_approved_at IS NOT NULL THEN 1 ELSE 0 END) as approved,
        SUM(CASE WHEN order_delivered_carrier_date IS NOT NULL THEN 1 ELSE 0 END) as shipped,
        SUM(CASE WHEN order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END) as delivered
    FROM orders
    GROUP BY month
)
SELECT 
    month,
    total_orders,
    approved,
    ROUND(approved * 100.0 / total_orders, 1) as approval_rate,
    shipped,
    ROUND(shipped * 100.0 / total_orders, 1) as ship_rate,
    delivered,
    ROUND(delivered * 100.0 / total_orders, 1) as delivery_rate
FROM monthly_funnel
ORDER BY month;

-- 3. 差评订单的漏斗表现（评分1-2 vs 4-5）
SELECT 
    CASE 
        WHEN r.review_score >= 4 THEN '好评(4-5)'
        WHEN r.review_score <= 2 THEN '差评(1-2)'
        ELSE '中评(3)'
    END as review_group,
    COUNT(DISTINCT o.order_id) as order_count,
    ROUND(AVG(r.review_score), 2) as avg_score,
    ROUND(AVG(DATEDIFF('day', o.order_purchase_timestamp, o.order_delivered_customer_date)), 1) as avg_delivery_days,
    ROUND(AVG(oi.price), 2) as avg_price,
    ROUND(SUM(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END) 
        * 100.0 / COUNT(DISTINCT o.order_id), 1) as late_delivery_pct
FROM orders o
JOIN order_reviews r ON o.order_id = r.order_id
LEFT JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY review_group;
