-- 核心经营指标：金额只在订单级事实表或商品明细表计算，避免一对多 JOIN 放大。

-- 1. 月度订单与销售趋势
SELECT 下单月份, COUNT(*) AS 订单数,
       ROUND(SUM(商品GMV), 2) AS 商品GMV,
       ROUND(SUM(订单含运费金额), 2) AS 含运费成交金额,
       ROUND(AVG(订单含运费金额), 2) AS 每单平均含运费金额
FROM v_order_facts
WHERE order_status NOT IN ('canceled', 'unavailable') AND 商品GMV IS NOT NULL
GROUP BY 下单月份 ORDER BY 下单月份;

-- 2. 品类销售结构：区分卖得多与卖得贵
SELECT 品类, COUNT(DISTINCT order_id) AS 订单数, COUNT(*) AS 商品件数,
       ROUND(SUM(price), 2) AS 商品GMV, ROUND(AVG(price), 2) AS 单件平均价格
FROM v_order_item_detail
WHERE order_status NOT IN ('canceled', 'unavailable') AND 品类 IS NOT NULL
GROUP BY 品类 ORDER BY 商品GMV DESC LIMIT 15;

-- 3. 客户州经营规模
SELECT customer_state AS 客户州, COUNT(*) AS 订单数,
       COUNT(DISTINCT customer_unique_id) AS 真实客户数,
       ROUND(SUM(商品GMV), 2) AS 商品GMV, ROUND(AVG(商品GMV), 2) AS 每单商品GMV
FROM v_order_facts
WHERE order_status NOT IN ('canceled', 'unavailable')
GROUP BY 客户州 ORDER BY 订单数 DESC;

-- 4. 支付方式（支付记录层级，不等于订单数）
SELECT payment_type AS 支付方式, COUNT(*) AS 支付记录数,
       COUNT(DISTINCT order_id) AS 使用该方式的订单数,
       ROUND(SUM(payment_value), 2) AS 支付金额,
       ROUND(AVG(payment_installments), 2) AS 平均分期数
FROM order_payments GROUP BY payment_type ORDER BY 支付金额 DESC;

-- 5. 评分分布（评价记录层级）
SELECT review_score AS 评分, COUNT(*) AS 评价记录数,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS 占比百分比
FROM order_reviews GROUP BY 评分 ORDER BY 评分;
