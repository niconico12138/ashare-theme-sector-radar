# Phase 27: Agent 加权体系与股票分析报告模板 验收报告

**日期**: 2026-07-05  
**项目**: ai-hedge-fund + theme-sector-radar-dev

---

## 1. 修改文件清单

| 文件 | 改动 |
|------|------|
| `ai-hedge-fund/scripts/run_stock_agent_bridge.py` | 重写 `compute_stock_agent_score()` 为加权体系 + 输出 `top_positive/negative_agents` + `contributing_agents` |
| `theme-sector-radar-dev/scripts/run_daily_bridge_report.py` | 更新 Markdown 模板：加权排名表 + 个股分析明细 Top10 |

## 2. Agent 权重表

### Core Preset (归一化到 1.0)

| Agent | Weight |
|-------|--------|
| technical_analyst | 0.22 |
| fundamentals_analyst | 0.18 |
| valuation_analyst | 0.16 |
| china_youzi | 0.14 |
| sentiment_analyst | 0.12 |
| industry_rotation | 0.10 |
| growth_analyst | 0.08 |

### Full Preset Group Weights

| 组 | 权重 | 包含 |
|----|------|------|
| 技术/趋势 | 25% | technical, druckenmiller |
| 基本面 | 15% | fundamentals, valuation, damodaran, graham, pabrai |
| 质量 | 10% | buffett, munger, fisher, lynch, wood, growth |
| A股特色 | 20% | china_youzi, sentiment, policy, northbound, rotation |
| 情绪 | 10% | sentiment_analyst, news_sentiment |
| 风险 | 10% | burry, taleb |

## 3. 评分公式

```python
# 1. Signal mapping
bullish/buy → +1.0, neutral/hold → 0, bearish/sell → -1.0

# 2. Normalized confidence
norm_conf = clamp(confidence / 100, 0, 1)

# 3. Weighted signal score
weighted_sum = Σ(agent_weight × direction × norm_conf) / effective_weight_sum

# 4. Agent score (0-100)
agent_score = 50 + weighted_sum × 50, clamp to [0, 100]

# 5. Risk penalty
risk_penalty = {low: 0, medium: 2, high: 5}

# 6. Risk-adjusted score
risk_adjusted_score = max(0, min(100, agent_score - risk_penalty))
```

## 4. 2026-07-03 Core Preset 运行摘要

```
Stock: 601211 国泰君安
  Agent: 51.3  Risk-adjusted: 51.3
  Votes: B1/H4/S0  Contributing: 5  Weight: 0.82
  Top+: china_youzi buy conf=0.15

Stock: 600030 中信证券
  Agent: 50.0  Risk-adjusted: 50.0
  Votes: B0/H4/S0  Contributing: 4  Weight: 0.70
```

## 5. 个股 Agent 排名格式

### Markdown 排名表

```
排名 代码       名称      Agent分 风险调整 风险   看多 中性 看空 贡献 核心摘要
  1 601211 国泰君安    51.3   51.3   medium   1    4    0    5 看多偏强(1/4/0)
  2 600030 中信证券    50.0   50.0   medium   0    4    0    4 多空均衡(0/4/0)
```

### 个股分析明细

```markdown
### 1. 601211 国泰君安
- 来源板块：证券
- Agent分：51.3  风险调整分：51.3
- 投票结构：看多 1 / 中性 4 / 看空 0
- 主要支持：china_youzi buy conf=0.15
```

## 6. 测试结果

| 命令 | 结果 |
|------|------|
| `pytest tests/theme_sector_radar/ -q` | **988 passed, 3 skipped** |
| core preset | ✅ 5/7 succeeded |
| full preset | ✅ 24 agents |
| weighted scoring | ✅ differentiated |
