(() => {
  "use strict";

  const data = window.OLIST_DASHBOARD_DATA;
  if (!data) {
    document.body.insertAdjacentHTML("afterbegin", '<div class="data-error">数据未加载，请确认 data/olist-dashboard-data.js 文件存在。</div>');
    return;
  }

  const colors = {
    ink: "#2e3b37",
    muted: "#73807b",
    line: "#dedbd3",
    rose: "#d75a7c",
    roseDark: "#b63f63",
    roseSoft: "#f3dce3",
    mint: "#67b7a5",
    mintDark: "#3d8878",
    mintSoft: "#dcefe9",
    amber: "#dca454",
    deep: "#263632"
  };

  const integer = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 });
  const compactMoney = value => `R$ ${(value / 1000000).toFixed(2)}M`;
  const tooltipBase = {
    backgroundColor: "rgba(38,54,50,.96)",
    borderWidth: 0,
    padding: [11, 14],
    textStyle: { color: "#fff", fontFamily: "Microsoft YaHei, sans-serif", fontSize: 12 },
    extraCssText: "border-radius:10px;box-shadow:0 12px 30px rgba(0,0,0,.18)"
  };

  document.querySelectorAll("[data-bind]").forEach(node => {
    const key = node.dataset.bind;
    const value = data.summary[key];
    if (value === undefined) return;
    node.textContent = node.dataset.format === "integer" ? integer.format(value) : value;
  });

  const revealObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach(element => revealObserver.observe(element));

  const countObserver = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const node = entry.target;
      const target = Number(node.dataset.count);
      const decimals = Number(node.dataset.decimals || 0);
      const start = performance.now();
      const duration = 1050;
      const tick = now => {
        const progress = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - progress, 3);
        node.textContent = (target * eased).toFixed(decimals);
        if (progress < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
      countObserver.unobserve(node);
    });
  }, { threshold: 0.7 });
  document.querySelectorAll("[data-count]").forEach(element => countObserver.observe(element));

  const progressBar = document.querySelector(".scroll-progress span");
  const updateProgress = () => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    progressBar.style.width = `${max > 0 ? (window.scrollY / max) * 100 : 0}%`;
  };
  window.addEventListener("scroll", updateProgress, { passive: true });
  updateProgress();

  if (!window.echarts) return;
  const charts = [];
  const createChart = id => {
    const chart = echarts.init(document.getElementById(id), null, { renderer: "canvas" });
    charts.push(chart);
    return chart;
  };

  const funnel = createChart("funnel-chart");
  const funnelCounts = [data.funnel.created, data.funnel.approved, data.funnel.shipped, data.funnel.delivered];
  const funnelStages = ["创建", "批准", "发货", "送达"];
  const funnelLosses = [0, data.funnel.created - data.funnel.approved, data.funnel.approved - data.funnel.shipped, data.funnel.shipped - data.funnel.delivered];
  const funnelRetention = funnelCounts.map(value => Number((value / data.funnel.created * 100).toFixed(2)));
  funnel.setOption({
    animationDuration: 950,
    animationEasing: "cubicOut",
    tooltip: {
      ...tooltipBase,
      trigger: "item",
      formatter: p => {
        const index = p.dataIndex;
        const loss = index === 0 ? "分析基准" : `较上一环节减少 ${integer.format(funnelLosses[index])} 笔`;
        return `<b>${funnelStages[index]}</b><br>${integer.format(funnelCounts[index])} 笔订单<br>保留率 ${funnelRetention[index]}%<br>${loss}`;
      }
    },
    grid: { left: 126, right: 34, top: 20, bottom: 18 },
    xAxis: { type: "value", min: 0, max: 100, show: false },
    yAxis: {
      type: "category",
      inverse: true,
      data: funnelStages,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        margin: 18,
        formatter: (value, index) => index === 0
          ? `{stage|${value}}\n{base|分析基准}`
          : `{stage|${value}}\n{loss|较上环节 -${integer.format(funnelLosses[index])}}`,
        rich: {
          stage: { color: colors.ink, fontSize: 13, fontWeight: 700, lineHeight: 21 },
          base: { color: colors.muted, fontSize: 10 },
          loss: { color: colors.roseDark, fontSize: 10 }
        }
      }
    },
    series: [{
      type: "bar",
      barWidth: 42,
      showBackground: true,
      backgroundStyle: { color: "#edf0ed", borderRadius: 8 },
      data: funnelRetention.map((value, index) => ({
        value,
        itemStyle: {
          color: ["#c8e2dc", "#afd7cd", "#90c7ba", "#d9829a"][index],
          borderRadius: 8
        }
      })),
      label: {
        show: true,
        position: "insideRight",
        distance: 14,
        color: colors.ink,
        fontWeight: 700,
        formatter: p => `${integer.format(funnelCounts[p.dataIndex])}  ·  ${funnelRetention[p.dataIndex]}%`
      },
      emphasis: { focus: "series" }
    }]
  });

  const comparison = createChart("comparison-chart");
  comparison.setOption({
    animationDuration: 1000,
    tooltip: { ...tooltipBase, trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { top: 8, right: 0, itemWidth: 10, itemHeight: 10, textStyle: { color: colors.muted } },
    grid: { left: 58, right: 60, top: 58, bottom: 42 },
    xAxis: { type: "category", data: ["未延误", "延误"], axisTick: { show: false }, axisLine: { lineStyle: { color: colors.line } }, axisLabel: { color: colors.ink, fontWeight: 700 } },
    yAxis: [
      { type: "value", name: "平均评分", max: 5, interval: 1, nameTextStyle: { color: colors.muted }, axisLabel: { color: colors.muted }, splitLine: { lineStyle: { color: "#ebe8e2" } } },
      { type: "value", name: "差评率", max: 100, axisLabel: { color: colors.muted, formatter: "{value}%" }, nameTextStyle: { color: colors.muted }, splitLine: { show: false } }
    ],
    series: [
      { name: "平均评分", type: "bar", barWidth: 54, data: data.delayComparison.map(item => item.score), itemStyle: { color: colors.mint, borderRadius: [8, 8, 0, 0] }, label: { show: true, position: "top", color: colors.mintDark, fontWeight: 700 } },
      { name: "差评率", type: "line", yAxisIndex: 1, symbolSize: 13, lineStyle: { width: 4, color: colors.rose }, itemStyle: { color: colors.rose, borderColor: "#fff", borderWidth: 3 }, data: data.delayComparison.map(item => item.badRate), label: { show: true, formatter: "{c}%", position: "top", color: colors.roseDark, fontWeight: 700 } }
    ]
  });

  const tolerance = createChart("tolerance-chart");
  tolerance.setOption({
    animationDuration: 1200,
    tooltip: { ...tooltipBase, trigger: "axis", formatter: params => {
      const item = data.delayBuckets[params[0].dataIndex];
      return `${item.bucket}<br>差评率：<b>${item.badRate}%</b><br>平均评分：${item.score}<br>评价订单：${integer.format(item.orders)}`;
    } },
    grid: { left: 58, right: 34, top: 35, bottom: 74 },
    xAxis: { type: "category", boundaryGap: false, data: data.delayBuckets.map(item => item.bucket), axisTick: { show: false }, axisLine: { lineStyle: { color: colors.line } }, axisLabel: { color: colors.muted, interval: 0, formatter: value => value.replace("延误", "延误\n") } },
    yAxis: { type: "value", max: 90, name: "差评率", axisLabel: { color: colors.muted, formatter: "{value}%" }, nameTextStyle: { color: colors.muted }, splitLine: { lineStyle: { color: "#ece9e3" } } },
    series: [{
      type: "line",
      smooth: .28,
      symbolSize: 12,
      data: data.delayBuckets.map(item => item.badRate),
      lineStyle: { width: 4, color: colors.rose },
      itemStyle: { color: colors.rose, borderColor: "#fff", borderWidth: 3 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: "rgba(215,90,124,.28)" }, { offset: 1, color: "rgba(215,90,124,.015)" }]) },
      label: { show: true, position: "top", formatter: "{c}%", color: colors.roseDark, fontWeight: 700 },
      markArea: { silent: true, itemStyle: { color: "rgba(220,164,84,.09)" }, data: [[{ xAxis: "延误3-5天" }, { xAxis: "延误11天及以上" }]] }
    }]
  });

  const priority = createChart("priority-chart");
  priority.setOption({
    animationDuration: 1200,
    tooltip: { ...tooltipBase, trigger: "item", formatter: p => {
      const item = p.data.raw;
      return `<b>${item.category}</b><br>商品 GMV：${compactMoney(item.gmv)}<br>延误订单：${integer.format(item.delayedOrders)}<br>差评率上升：${item.badRateLift} pp<br>预计额外差评风险：${integer.format(item.risk)}`;
    } },
    grid: { left: 68, right: 30, top: 35, bottom: 55 },
    xAxis: { type: "value", name: "商品 GMV", nameLocation: "middle", nameGap: 34, axisLabel: { color: "rgba(255,255,255,.45)", formatter: value => `${(value / 1000000).toFixed(1)}M` }, nameTextStyle: { color: "rgba(255,255,255,.48)" }, axisLine: { lineStyle: { color: "rgba(255,255,255,.18)" } }, splitLine: { lineStyle: { color: "rgba(255,255,255,.08)" } } },
    yAxis: { type: "value", name: "风险", axisLabel: { color: "rgba(255,255,255,.45)" }, nameTextStyle: { color: "rgba(255,255,255,.48)" }, axisLine: { lineStyle: { color: "rgba(255,255,255,.18)" } }, splitLine: { lineStyle: { color: "rgba(255,255,255,.08)" } } },
    series: [{
      type: "scatter",
      data: data.priority.map((item, index) => ({
        value: [item.gmv, item.risk, item.delayedOrders],
        raw: item,
        label: { show: index < 3, formatter: item.category, position: "top", color: "#fff", fontSize: 10 }
      })),
      symbolSize: value => Math.max(13, Math.sqrt(value[2]) * 2.15),
      itemStyle: { color: colors.rose, opacity: .78, borderColor: "rgba(255,255,255,.65)", borderWidth: 1 },
      emphasis: { scale: 1.35, itemStyle: { opacity: 1 } }
    }]
  });

  const priorityList = document.getElementById("priority-list");
  data.priority.slice(0, 3).forEach(item => {
    priorityList.insertAdjacentHTML("beforeend", `<li><div><b>${item.category}</b><span>${integer.format(item.delayedOrders)} 笔延误 · 风险 ${integer.format(item.risk)}</span></div></li>`);
  });

  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => charts.forEach(chart => chart.resize()), 120);
  });
})();
