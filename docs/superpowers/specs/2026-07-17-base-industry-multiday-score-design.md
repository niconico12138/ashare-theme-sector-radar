# 行业基础分多日趋势正式替换

日期：2026-07-17

## 边界

- 保持数据层、Path A/B/C、板块到个股桥接架构不变。
- 只替换正式行业基础分中的 `trend_strength` 和 `persistence`。
- 概念基础分、风险扣分和候选股受保护评分字段不变。
- 仅限 paper/shadow research，不连接券商，不生成实盘指令。

## 趋势强度（25分）

```text
trend_strength =
    7 * percentile(compound_return_5d)
  + 7 * percentile(compound_return_10d)
  + 5 * percentile(compound_return_20d)
  + 3 * positive_log_wealth_trend_r2_20d
  + 3 * continuous_breakout_quality_20d
```

横截面百分位使用历史目录中当日可用的完整行业参照集，并列值使用平均秩。
窗口签名包含每个收益的起止日期；签名子组至少包含2个行业且覆盖同窗口
有日期参照集的80%，否则该相对强度组件不可用。
突破质量把当前累计净值相对先前20个端点高点的距离从 `-2%..+2%`
线性映射至 `0..1`。趋势拟合度仅在斜率为正时计分。

## 持续性（15分）

```text
persistence =
    4 * positive_day_ratio_10d
  + 3 * positive_day_ratio_20d
  + 3 * positive_log_wealth_trend_r2
  + drawdown_control_0_to_3
  + 2 * rolling_5d_top_quartile_residence_ratio_10d
```

20日最大回撤不超过 `2%/5%/8%` 时分别得 `3/2/1` 分，超过8%得0分。
排名驻留率按最近10个端点的滚动5日复合收益横截面百分位计算，进入前25%才计驻留。

## 历史成熟度

- 少于5个完成收益：趋势与持续性均不计分，`insufficient_history`。
- 5至9个完成收益：只启用5日相对强度，`partial_history`。
- 10至19个完成收益：启用5日、10日相对强度和已成熟持续性组件，`partial_history`。
- 至少20个完成收益：启用全部组件，`ok`。
- 21个收盘价才构成20个完成收益；`change_pct` 不覆盖相邻收盘价计算。
- 日期必须是规范 `YYYY-MM-DD`；未来日期、重复日期、错期末端、非有限值和非正收盘价不得进入评分。

报告持久化 `trend_history_days`、`trend_history_coverage_ratio` 和
`trend_history_status`，历史不足不再回退为“当日上涨+高成交额”的中性高分。
Pipeline 另持久化名称匹配、5日、10日和20日成熟覆盖；5日成熟覆盖不足时
正式报告至少为 `degraded`，原因同时进入返回对象、JSON和Markdown。

## 一致性

日常 Pipeline Phase 8 和 PIT 历史回放都在基础排名前构造同一组多日特征。
PIT 每个评分日只截取截至该日的记录；标签和未来收益生成逻辑不变。
