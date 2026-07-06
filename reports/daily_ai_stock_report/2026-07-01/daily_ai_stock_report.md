# 每日 AI 板块与个股观察报告

**日期**: 2026-07-01
**生成时间**: 2026-07-05 21:25:16

> **免责声明**: 本报告仅供研究观察，不构成投资建议。

## 1. 运行摘要

- **日期**: 2026-07-01
- **Preset**: selected
- **Agent 数量**: 7
- **LLM 状态**: configured=?, available=?, model=?
- **免责声明**: 本报告仅供研究观察，不构成投资建议。

## 2. 板块主线摘要

### 行业板块 Top10

    排名 行业         Agent标签                           排序分      机会分      置信度
  ────────────────────────────────────────────────────────────────────────
     1 电子化学品      strong_consensus                 0.84     0.65     0.80
     2 半导体        trend_confirmed                  0.80     0.56     0.80
     3 证券         trend_confirmed                  0.78     0.50     0.90
     4 医疗服务       defensive_watch                  0.61     0.48     0.70
     5 化学制药       trend_confirmed_but_strength_limited     0.58     0.43     0.90
     6 游戏         trend_confirmed_but_strength_limited     0.58     0.43     0.90
     7 生物制品       trend_confirmed_but_strength_limited     0.58     0.42     0.90
     8 养殖业        oversold_rebound_candidate       0.57     0.40     0.80
     9 教育         oversold_rebound_candidate       0.57     0.40     0.90
    10 保险         defensive_watch                  0.57     0.39     0.60

### 概念板块 Top10

    排名 概念                    综合分      趋势分      短线分 Agent标签         
  ────────────────────────────────────────────────────────────
     1 氟化工概念               74.63    70.20    69.80 trend_confirmed 
     2 光刻胶                 74.43    74.20    58.80 strong_consensus
     3 光刻机                 67.93    66.20    45.80 trend_confirmed 
     4 存储芯片                67.23    62.20    48.80 trend_confirmed 
     5 硅能源                 66.01    65.00    58.80 trend_confirmed 
     6 华为海思概念股             63.83    50.20    55.80 trend_confirmed 
     7 超级电容                62.73    50.20    55.80 trend_confirmed 
     8 国家大基金持股             62.14    55.65    40.30 trend_confirmed 
     9 第三代半导体              61.72    56.45    37.30 trend_confirmed 
    10 电子纸                 60.33    50.20    45.80 trend_confirmed 

## 3. 候选池摘要

- 趋势池: 5 只
- 短线池: 6 只
- 合并去重: 13 只
- rank_hidden: true (无原始排名)
- ST 过滤: 已执行
- 主板过滤: 已执行

  来源板块分布:
    光刻胶: 4 只
    创新药: 3 只
    氟化工概念: 2 只
    猴痘概念: 2 只
    光刻机: 1 只

## 4. 个股 Agent 排名 Top10

    排名 代码       名称         来源池    来源板块            趋势分    短线分 Agent分   风险调整 IR
  ──────────────────────────────────────────────────────────────────────────────────────────────────
     1 000100   TCL科技      trend  光刻胶            74.2   58.8   54.5   54.5  -
     2 000021   深科技        trend  光刻胶            74.2   58.8   54.1   54.1  -
     3 000536   华映科技       trend  光刻胶            74.2   58.8   54.0   54.0  -
     4 600196   复星医药       burst  猴痘概念           38.5   72.3   52.9   52.9  -
     5 002399   海普瑞        burst  猴痘概念           38.5   72.3   52.2   52.2  -
     6 000153   丰原药业       burst  创新药            40.2   69.8   52.2   52.2  -
     7 000504   南华生物       burst  创新药            40.2   69.8   50.9   50.9  -
     8 603160   汇顶科技       trend  光刻机            66.2   45.8   50.8   50.8  -
     9 000565   渝三峡A       both   氟化工概念          70.2   69.8   50.6   50.6  -
    10 000411   英特集团       burst  创新药            40.2   69.8   50.6   50.6  -

## 5. 个股分析明细 Top10

### 1. 000100 TCL科技
- **来源池**: trend
- **来源板块**: 光刻胶
- **板块上下文**: 未匹配
- **Agent分**: 54.5  **风险调整分**: 54.5
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 2. 000021 深科技
- **来源池**: trend
- **来源板块**: 光刻胶
- **板块上下文**: 未匹配
- **Agent分**: 54.1  **风险调整分**: 54.1
- **投票**: 看多 2 / 中性 4 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: industry_rotation

### 3. 000536 华映科技
- **来源池**: trend
- **来源板块**: 光刻胶
- **板块上下文**: 未匹配
- **Agent分**: 54.0  **风险调整分**: 54.0
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 4. 600196 复星医药
- **来源池**: burst
- **来源板块**: 猴痘概念
- **板块上下文**: 未匹配
- **Agent分**: 52.9  **风险调整分**: 52.9
- **投票**: 看多 2 / 中性 4 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: industry_rotation

### 5. 002399 海普瑞
- **来源池**: burst
- **来源板块**: 猴痘概念
- **板块上下文**: 未匹配
- **Agent分**: 52.2  **风险调整分**: 52.2
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 6. 000153 丰原药业
- **来源池**: burst
- **来源板块**: 创新药
- **板块上下文**: 未匹配
- **Agent分**: 52.2  **风险调整分**: 52.2
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 7. 000504 南华生物
- **来源池**: burst
- **来源板块**: 创新药
- **板块上下文**: 未匹配
- **Agent分**: 50.9  **风险调整分**: 50.9
- **投票**: 看多 1 / 中性 3 / 看空 0
- **主要支持**: news_sentiment_analyst(buy)
- **Fallback**: technical_analyst, sentiment_analyst, industry_rotation

### 8. 603160 汇顶科技
- **来源池**: trend
- **来源板块**: 光刻机
- **板块上下文**: 未匹配
- **Agent分**: 50.8  **风险调整分**: 50.8
- **投票**: 看多 1 / 中性 4 / 看空 0
- **主要支持**: news_sentiment_analyst(buy)
- **Fallback**: technical_analyst, industry_rotation

### 9. 000565 渝三峡A
- **来源池**: both
- **来源板块**: 氟化工概念
- **板块上下文**: 未匹配
- **Agent分**: 50.6  **风险调整分**: 50.6
- **投票**: 看多 1 / 中性 4 / 看空 0
- **主要支持**: news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 10. 000411 英特集团
- **来源池**: burst
- **来源板块**: 创新药
- **板块上下文**: 未匹配
- **Agent分**: 50.6  **风险调整分**: 50.6
- **投票**: 看多 1 / 中性 4 / 看空 0
- **主要支持**: news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

## 6. Agent 运行统计

  Agent                         调用     成功     降级     失败
  ───────────────────────────────────────────────────────
  technical_analyst             13     10      3      0
  fundamentals_analyst          13     13      0      0
  valuation_analyst             13     13      0      0
  sentiment_analyst             13      3     10      0
  china_youzi                   13     13      0      0
  industry_rotation             13      0     13      0
  news_sentiment_analyst        13     13      0      0

## 7. 数据源与风险

- **StockDB**: ✅ 可用
- **market_data_service**: ✅ 可用
- **板块评分**: ✅
- **概念排名**: ✅

## 8. 趋势与说明

- Agent 分数由加权投票生成，高分表示多 Agent 共振偏多
- industry_rotation 贡献取决于板块上下文匹配
- fallback Agent 数据不足时自动降级，不计入排名
- 本报告仅供研究观察，不构成投资建议
