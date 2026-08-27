-- 物流延误与客户体验。延误 = 实际送达时间严格晚于承诺送达时间。

-- 1. 延误概览
SELECT COUNT(*) AS 已送达订单数, SUM(is_delayed) AS 延误订单数,
       ROUND(AVG(is_delayed) * 100, 2) AS 延误率百分比,
       ROUND(AVG(CASE WHEN is_delayed = 1 THEN delay_days END), 2) AS 延误订单平均延误天数
FROM v_order_delay;

-- 2. 延误与未延误订单的体验对比
SELECT is_delayed AS 是否延误, COUNT(*) AS 有评价订单数,
       ROUND(AVG(review_score), 2) AS 平均评分,
       ROUND(AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) * 100, 2) AS 差评率百分比
FROM v_order_delay WHERE review_score IS NOT NULL
GROUP BY 是否延误 ORDER BY 是否延误;

-- 3. 延误时长分箱：先判断是否延误，避免把“晚几小时但不足一天”归为按时。
SELECT CASE
         WHEN is_delayed = 0 THEN '按时或提前'
         WHEN delay_days = 0 THEN '延误不足1天'
         WHEN delay_days <= 2 THEN '延误1–2天'
         WHEN delay_days <= 5 THEN '延误3–5天'
         WHEN delay_days <= 10 THEN '延误6–10天'
         ELSE '延误11天及以上'
       END AS 延误分组,
       COUNT(*) AS 有评价订单数, ROUND(AVG(review_score), 2) AS 平均评分,
       ROUND(AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) * 100, 2) AS 差评率百分比
FROM v_order_delay WHERE review_score IS NOT NULL
GROUP BY 延误分组
ORDER BY MIN(CASE WHEN is_delayed = 0 THEN -1 ELSE delay_days END);

-- 4. 同品类分层：每笔订单在每个品类只保留一次
WITH 品类订单体验 AS (
    SELECT 品类.品类, 延误.is_delayed, 延误.review_score
    FROM v_order_category 品类 JOIN v_order_delay 延误 ON 品类.order_id = 延误.order_id
    WHERE 延误.review_score IS NOT NULL
), 品类汇总 AS (
    SELECT 品类,
           SUM(CASE WHEN is_delayed = 0 THEN 1 ELSE 0 END) AS 未延误订单数,
           SUM(CASE WHEN is_delayed = 1 THEN 1 ELSE 0 END) AS 延误订单数,
           AVG(CASE WHEN is_delayed = 0 THEN review_score END) AS 未延误平均评分,
           AVG(CASE WHEN is_delayed = 1 THEN review_score END) AS 延误平均评分,
           AVG(CASE WHEN is_delayed = 0 AND review_score <= 2 THEN 1 WHEN is_delayed = 0 THEN 0 END) AS 未延误差评率,
           AVG(CASE WHEN is_delayed = 1 AND review_score <= 2 THEN 1 WHEN is_delayed = 1 THEN 0 END) AS 延误差评率
    FROM 品类订单体验 GROUP BY 品类
)
SELECT 品类, 未延误订单数, 延误订单数,
       ROUND(未延误平均评分, 2) AS 未延误平均评分,
       ROUND(延误平均评分, 2) AS 延误平均评分,
       ROUND(未延误平均评分 - 延误平均评分, 2) AS 评分下降,
       ROUND((延误差评率 - 未延误差评率) * 100, 2) AS 差评率上升百分点,
       ROUND(延误订单数 * (延误差评率 - 未延误差评率), 0) AS 预计额外差评风险
FROM 品类汇总
WHERE 未延误订单数 >= 30 AND 延误订单数 >= 30
ORDER BY 预计额外差评风险 DESC LIMIT 15;
