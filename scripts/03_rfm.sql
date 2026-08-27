-- 客户购买行为探索。96% 以上客户仅购买一次，RFM 的 Frequency 区分度不足，不作主线结论。

-- 1. 用户级 R/F/M 原始值（真实客户粒度）
CREATE OR REPLACE VIEW v_customer_rfm_raw AS
SELECT customer_unique_id AS 真实客户ID, MAX(order_purchase_timestamp) AS 最近一次下单时间,
       COUNT(*) AS 购买频次, ROUND(SUM(订单含运费金额), 2) AS 累计消费金额
FROM v_order_facts
WHERE order_status NOT IN ('canceled', 'unavailable')
  AND customer_unique_id IS NOT NULL AND 订单含运费金额 IS NOT NULL
GROUP BY customer_unique_id;

-- 2. 购买频次分布：判断 RFM 是否适用
SELECT 购买频次, COUNT(*) AS 客户数,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS 客户占比百分比
FROM v_customer_rfm_raw GROUP BY 购买频次 ORDER BY 购买频次;

-- 3. 适合本数据的简化客户分层：频次 × 消费金额前 20%
WITH 消费阈值 AS (
    SELECT PERCENTILE_CONT(0.8) WITHIN GROUP (ORDER BY 累计消费金额) AS 高消费阈值
    FROM v_customer_rfm_raw
), 客户分层 AS (
    SELECT 客户.*,
           CASE
             WHEN 购买频次 = 1 AND 累计消费金额 < 阈值.高消费阈值 THEN '单次购买、普通消费'
             WHEN 购买频次 = 1 THEN '单次购买、高消费'
             WHEN 累计消费金额 < 阈值.高消费阈值 THEN '复购、普通消费'
             ELSE '复购、高消费'
           END AS 客户类型
    FROM v_customer_rfm_raw 客户 CROSS JOIN 消费阈值 阈值
)
SELECT 客户类型, COUNT(*) AS 客户数,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS 客户占比百分比,
       ROUND(AVG(购买频次), 2) AS 平均购买频次,
       ROUND(AVG(累计消费金额), 2) AS 平均累计消费金额
FROM 客户分层 GROUP BY 客户类型 ORDER BY 客户数 DESC;
