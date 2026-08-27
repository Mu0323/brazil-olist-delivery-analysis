-- 履约漏斗与评价覆盖率。“评价”不属于严格的履约下一环。

-- 1. 创建 → 付款批准 → 发货 → 实际送达
WITH 漏斗 AS (
    SELECT COUNT(*) AS 创建订单数, SUM(is_approved) AS 已批准付款订单数,
           SUM(is_shipped) AS 已发货订单数, SUM(is_delivered) AS 已送达订单数
    FROM v_order_delivery
)
SELECT *, ROUND(已批准付款订单数 * 100.0 / 创建订单数, 2) AS 付款批准率百分比,
       ROUND(已发货订单数 * 100.0 / 已批准付款订单数, 2) AS 批准后发货率百分比,
       ROUND(已送达订单数 * 100.0 / 已批准付款订单数, 2) AS 批准后送达率百分比
FROM 漏斗;

-- 2. 已送达订单评价覆盖率
SELECT COUNT(*) AS 有实际送达日期的订单数,
       SUM(CASE WHEN review_score IS NOT NULL THEN 1 ELSE 0 END) AS 有评价的已送达订单数,
       ROUND(AVG(CASE WHEN review_score IS NOT NULL THEN 1 ELSE 0 END) * 100, 2)
           AS 已送达订单评价覆盖率百分比
FROM v_order_delay;

-- 3. 分月履约情况
SELECT STRFTIME(order_purchase_timestamp, '%Y-%m') AS 下单月份, COUNT(*) AS 创建订单数,
       ROUND(AVG(is_approved) * 100, 2) AS 付款批准率百分比,
       ROUND(AVG(is_shipped) * 100, 2) AS 发货率百分比,
       ROUND(AVG(is_delivered) * 100, 2) AS 送达率百分比
FROM v_order_delivery GROUP BY 下单月份 ORDER BY 下单月份;
