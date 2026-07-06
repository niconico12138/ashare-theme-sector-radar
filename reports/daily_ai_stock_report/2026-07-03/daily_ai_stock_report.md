# 每日 AI 板块与个股观察报告

**日期**: 2026-07-03
**生成时间**: 2026-07-05 18:08:20

> **免责声明**: 本报告仅供研究观察，不构成投资建议。

## 1. 运行摘要

- **日期**: 2026-07-03
- **Preset**: selected
- **Agent 数量**: 7
- **LLM 状态**: configured=?, available=?, model=?
- **免责声明**: 本报告仅供研究观察，不构成投资建议。

## 2. 板块主线摘要

### 行业板块 Top10

    排名 行业         Agent标签                           排序分      机会分      置信度
  ────────────────────────────────────────────────────────────────────────
     1 化学制药       trend_confirmed                  0.80     0.55     0.90
     2 电子化学品      trend_confirmed                  0.78     0.51     0.70
     3 物流         trend_confirmed                  0.72     0.49     0.90
     4 养殖业        trend_confirmed                  0.71     0.47     0.90
     5 纺织制造       trend_confirmed                  0.71     0.46     0.90
     6 化学制品       trend_confirmed                  0.69     0.43     0.90
     7 化学原料       trend_confirmed                  0.69     0.43     0.90
     8 游戏         trend_confirmed_but_strength_limited     0.57     0.40     0.80
     9 造纸         trend_confirmed_but_strength_limited     0.57     0.39     0.90
    10 美容护理       trend_confirmed_but_strength_limited     0.57     0.39     0.90

### 概念板块 Top10

    排名 概念                    综合分      趋势分      短线分 Agent标签         
  ────────────────────────────────────────────────────────────
     1 氟化工概念               67.53    66.20    48.80 trend_confirmed 
     2 动物疫苗                63.81    59.00    45.80 trend_confirmed 
     3 丙烯酸                 63.51    55.00    45.80 trend_confirmed 
     4 光刻胶                 61.92    62.45    30.30 trend_confirmed 
     5 芬太尼                 50.66    40.00    55.80 oversold_rebound_candidate
     6 环氧丙烷                50.51    53.00    55.80 conflicted      
     7 海南自贸区               49.66    34.00    58.80 trend_confirmed_but_strength_limited
     8 辅助生殖                48.93    42.20    45.80 trend_confirmed_but_strength_limited
     9 仿制药一致性评价            48.88    45.20    58.80 conflicted      
    10 合成生物                47.71    47.00    45.80 conflicted      

## 3. 候选池摘要

- 趋势池: 5 只
- 短线池: 5 只
- 合并去重: 15 只
- rank_hidden: true (无原始排名)
- ST 过滤: 已执行
- 主板过滤: 已执行

  来源板块分布:
    光刻胶: 4 只
    海南自贸区: 4 只
    芬太尼: 3 只
    氟化工概念: 2 只
    动物疫苗: 1 只

## 4. 个股 Agent 排名 Top10

    排名 代码       名称         来源池    来源板块            趋势分    短线分 Agent分   风险调整 IR
  ──────────────────────────────────────────────────────────────────────────────────────────────────
     1 000536   华映科技       trend  光刻胶            62.5   30.3   55.7   55.7  -
     2 000062   深圳华强       trend  光刻胶            62.5   30.3   53.8   53.8  -
     3 000504   南华生物       both   芬太尼            45.2   58.8   53.8   53.8  -
     4 000501   武商集团       burst  海南自贸区          34.0   58.8   53.6   53.6  -
     5 000565   渝三峡A       both   氟化工概念          66.2   55.8   53.2   53.2  -
     6 000153   丰原药业       both   芬太尼            45.2   58.8   53.2   53.2  -
     7 000564   供销大集       burst  海南自贸区          34.0   58.8   53.1   53.1  -
     8 000553   安道麦A       both   氟化工概念          66.2   55.8   52.6   52.6  -
     9 000798   中水渔业       trend  动物疫苗           59.0   45.8   52.6   52.6  -
    10 000411   英特集团       both   芬太尼            45.2   58.8   52.6   52.6  -

## 5. 个股分析明细 Top10

### 1. 000536 华映科技
- **来源池**: trend
- **来源板块**: 光刻胶
- **板块上下文**: 未匹配
- **Agent分**: 55.7  **风险调整分**: 55.7
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 2. 000062 深圳华强
- **来源池**: trend
- **来源板块**: 光刻胶
- **板块上下文**: 未匹配
- **Agent分**: 53.8  **风险调整分**: 53.8
- **投票**: 看多 2 / 中性 2 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: technical_analyst, sentiment_analyst, industry_rotation

### 3. 000504 南华生物
- **来源池**: both
- **来源板块**: 芬太尼
- **板块上下文**: 未匹配
- **Agent分**: 53.8  **风险调整分**: 53.8
- **投票**: 看多 2 / 中性 2 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: technical_analyst, sentiment_analyst, industry_rotation

### 4. 000501 武商集团
- **来源池**: burst
- **来源板块**: 海南自贸区
- **板块上下文**: 未匹配
- **Agent分**: 53.6  **风险调整分**: 53.6
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 5. 000565 渝三峡A
- **来源池**: both
- **来源板块**: 氟化工概念
- **板块上下文**: 未匹配
- **Agent分**: 53.2  **风险调整分**: 53.2
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 6. 000153 丰原药业
- **来源池**: both
- **来源板块**: 芬太尼
- **板块上下文**: 未匹配
- **Agent分**: 53.2  **风险调整分**: 53.2
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 7. 000564 供销大集
- **来源池**: burst
- **来源板块**: 海南自贸区
- **板块上下文**: 未匹配
- **Agent分**: 53.1  **风险调整分**: 53.1
- **投票**: 看多 2 / 中性 2 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: valuation_analyst, sentiment_analyst, industry_rotation

### 8. 000553 安道麦A
- **来源池**: both
- **来源板块**: 氟化工概念
- **板块上下文**: 未匹配
- **Agent分**: 52.6  **风险调整分**: 52.6
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 9. 000798 中水渔业
- **来源池**: trend
- **来源板块**: 动物疫苗
- **板块上下文**: 未匹配
- **Agent分**: 52.6  **风险调整分**: 52.6
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 10. 000411 英特集团
- **来源池**: both
- **来源板块**: 芬太尼
- **板块上下文**: 未匹配
- **Agent分**: 52.6  **风险调整分**: 52.6
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

## 6. Agent 运行统计

  Agent                         调用     成功     降级     失败
  ───────────────────────────────────────────────────────
  technical_analyst             15     13      2      0
  fundamentals_analyst          15     15      0      0
  valuation_analyst             15     14      1      0
  sentiment_analyst             15      2     13      0
  china_youzi                   15     15      0      0
  industry_rotation             15      0     15      0
  news_sentiment_analyst        15     15      0      0

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
