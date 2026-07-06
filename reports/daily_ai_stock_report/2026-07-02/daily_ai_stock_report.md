# 每日 AI 板块与个股观察报告

**日期**: 2026-07-02
**生成时间**: 2026-07-05 17:54:44

> **免责声明**: 本报告仅供研究观察，不构成投资建议。

## 1. 运行摘要

- **日期**: 2026-07-02
- **Preset**: selected
- **Agent 数量**: 7
- **LLM 状态**: configured=?, available=?, model=?
- **免责声明**: 本报告仅供研究观察，不构成投资建议。

## 2. 板块主线摘要

### 行业板块 Top10

    排名 行业         Agent标签                           排序分      机会分      置信度
  ────────────────────────────────────────────────────────────────────────
     1 化学制药       trend_confirmed                  0.80     0.56     0.90
     2 电子化学品      trend_confirmed                  0.79     0.53     0.70
     3 化学制品       trend_confirmed                  0.69     0.43     0.90
     4 物流         trend_confirmed_but_strength_limited     0.57     0.41     0.90
     5 游戏         trend_confirmed_but_strength_limited     0.57     0.40     0.80
     6 养殖业        trend_confirmed_but_strength_limited     0.57     0.40     0.90
     7 医疗服务       trend_confirmed_but_strength_limited     0.57     0.39     0.80
     8 纺织制造       trend_confirmed_but_strength_limited     0.57     0.39     0.90
     9 中药         trend_confirmed_but_strength_limited     0.56     0.37     0.90
    10 美容护理       trend_confirmed_but_strength_limited     0.55     0.36     0.90

### 概念板块 Top10

    排名 概念                    综合分      趋势分      短线分 Agent标签         
  ────────────────────────────────────────────────────────────
     1 氟化工概念               67.53    66.20    48.80 trend_confirmed 
     2 动物疫苗                64.96    62.00    45.80 trend_confirmed 
     3 丙烯酸                 63.51    55.00    45.80 trend_confirmed 
     4 光刻胶                 61.92    62.45    30.30 trend_confirmed 
     5 合成生物                60.26    50.00    45.80 trend_confirmed 
     6 环氧丙烷                51.66    56.00    55.80 conflicted      
     7 仿制药一致性评价            50.03    48.20    58.80 conflicted      
     8 海南自贸区               49.66    34.00    58.80 trend_confirmed_but_strength_limited
     9 肝炎概念                49.03    42.20    45.80 trend_confirmed_but_strength_limited
    10 芬太尼                 48.76    48.00    55.80 conflicted      

## 3. 候选池摘要

- 趋势池: 6 只
- 短线池: 2 只
- 合并去重: 8 只
- rank_hidden: true (无原始排名)
- ST 过滤: 已执行
- 主板过滤: 已执行

  来源板块分布:
    电子化学品: 3 只
    证券: 2 只
    生物制品: 2 只
    小金属: 1 只

## 4. 个股 Agent 排名 Top8

    排名 代码       名称         Agent分   风险调整 板块           IR
  ─────────────────────────────────────────────────────────────────
     1 002294   信立泰          57.1   55.1 -             -
     2 600360   华微电子         55.7   55.7 -             -
     3 601108   财通证券         54.0   54.0 -             -
     4 002841   视源股份         53.6   53.6 -             -
     5 002635   安洁科技         53.3   53.3 -             -
     6 603087   甘李药业         53.2   51.2 -             -
     7 601881   中国银河         52.6   52.6 -             -
     8 601069   西部黄金         52.4   52.4 -             -

## 5. 个股分析明细 Top8

### 1. 002294 信立泰
- **来源池**: burst
- **来源板块**: 生物制品
- **板块上下文**: 未匹配
- **Agent分**: 57.1  **风险调整分**: 55.1
- **投票**: 看多 2 / 中性 2 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: technical_analyst, sentiment_analyst, industry_rotation

### 2. 600360 华微电子
- **来源池**: trend
- **来源板块**: 电子化学品
- **板块上下文**: 未匹配
- **Agent分**: 55.7  **风险调整分**: 55.7
- **投票**: 看多 2 / 中性 2 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: technical_analyst, sentiment_analyst, industry_rotation

### 3. 601108 财通证券
- **来源池**: trend
- **来源板块**: 证券
- **板块上下文**: 未匹配
- **Agent分**: 54.0  **风险调整分**: 54.0
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 4. 002841 视源股份
- **来源池**: trend
- **来源板块**: 电子化学品
- **板块上下文**: 未匹配
- **Agent分**: 53.6  **风险调整分**: 53.6
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 5. 002635 安洁科技
- **来源池**: trend
- **来源板块**: 电子化学品
- **板块上下文**: 未匹配
- **Agent分**: 53.3  **风险调整分**: 53.3
- **投票**: 看多 2 / 中性 4 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: industry_rotation

### 6. 603087 甘李药业
- **来源池**: burst
- **来源板块**: 生物制品
- **板块上下文**: 未匹配
- **Agent分**: 53.2  **风险调整分**: 51.2
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: technical_analyst, industry_rotation

### 7. 601881 中国银河
- **来源池**: trend
- **来源板块**: 证券
- **板块上下文**: 未匹配
- **Agent分**: 52.6  **风险调整分**: 52.6
- **投票**: 看多 2 / 中性 3 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: sentiment_analyst, industry_rotation

### 8. 601069 西部黄金
- **来源池**: trend
- **来源板块**: 小金属
- **板块上下文**: 未匹配
- **Agent分**: 52.4  **风险调整分**: 52.4
- **投票**: 看多 2 / 中性 4 / 看空 0
- **主要支持**: china_youzi(buy), news_sentiment_analyst(buy)
- **Fallback**: industry_rotation

## 6. Agent 运行统计

  Agent                         调用     成功     降级     失败
  ───────────────────────────────────────────────────────
  technical_analyst              8      5      3      0
  fundamentals_analyst           8      8      0      0
  valuation_analyst              8      8      0      0
  sentiment_analyst              8      3      5      0
  china_youzi                    8      8      0      0
  industry_rotation              8      0      8      0
  news_sentiment_analyst         8      8      0      0

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
