# Phase 26B: Rule-based Agent 差异化增强 验收报告

**日期**: 2026-07-05  
**项目**: ai-hedge-fund + theme-sector-radar-dev

---

## 1. 修改文件清单

| 文件 | 改动 |
|------|------|
| `ai-hedge-fund/src/agents/china_youzi.py` | +`_rule_based_fallback()`, LLM 失败时使用规则分析 |
| `ai-hedge-fund/src/agents/industry_rotation.py` | +`_rule_based_fallback()`, 修复 `risk_level` 字段缺失 |
| `ai-hedge-fund/src/agents/sentiment.py` | LLM 失败时使用规则信号 (confidence clamp) |
| `ai-hedge-fund/src/agents/northbound_flow.py` | +`_rule_based_fallback()` |
| `ai-hedge-fund/src/agents/policy_analyst.py` | +`_rule_based_fallback()` |

## 2. 增加了 Rule-based Fallback 的 Agent

| Agent | 原因 | rule-based 逻辑 |
|-------|------|----------------|
| china_youzi ✅ | LLM 返回 validation error | 5日涨幅 + 量比 + 涨停事件 |
| industry_rotation ⚠️ | LLM 返回 risk_level 缺失 | 子分析聚合 (sub_analyses) |
| sentiment_analyst | LLM 失败时已有规则，clamp confidence | 情绪信号聚合 |
| northbound_flow | LLM 失败时已有规则，clamp confidence | 财务质量指标 |
| policy_analyst | LLM 失败时已有规则 | 子分析聚合 |
| growth_analyst ⚠️ | 财务数据不足 (1期 vs 需4期) | 已有规则但数据不够 |

## 3. 仍需依赖 LLM 或真实数据的 Agent

| Agent | 原因 |
|-------|------|
| technical_analyst | 已通过 LLM (mimo) 成功 |
| fundamentals_analyst | 已通过 LLM (mimo) 成功 |
| valuation_analyst | 已通过 LLM (mimo) 成功 |

## 4. core preset (7 agents) 最终统计

```
agent_count: 7
succeeded: 5 (technical, fundamentals, valuation, sentiment, china_youzi)
failed: 0
fallback: 2 (industry_rotation, growth_analyst)

per-agent status:
  china_youzi:           S=2 F=0 B=0 (rule-based fallback)
  fundamentals_analyst:  S=2 F=0 B=0 (LLM succeeded)
  valuation_analyst:     S=2 F=0 B=0 (LLM succeeded)
  sentiment_analyst:     S=1 F=0 B=1 (mixed)
  technical_analyst:     S=2 F=0 B=0 (LLM succeeded)
  industry_rotation:     S=0 F=0 B=2 (数据不足: sub_analyses < 2)
  growth_analyst:        S=0 F=0 B=2 (数据不足: 财务指标仅 1 期)
```

## 5. 2026-07-03 Top 股票 (core, 2 stocks)

```
1. 601211 国泰君安  score=50.7 B2/H5/S0
   china_youzi: buy conf=15.0 ok  ← rule-based
   technical_analyst: hold conf=1.5 ok

2. 600030 中信证券  score=50.0 B1/H6/S0
   china_youzi: hold conf=6.0 ok  ← rule-based
   technical_analyst: hold conf=24.8 ok
```

**vs Phase 26A.2 (所有 fallback)**: 现在 china_youzi 能产生差异化信号 (buy/hold)，不再是全部 hold/confidence=0。

## 6. rule_based_contributors 统计

| Stock | rule-based contributors |
|-------|------------------------|
| 601211 国泰君安 | china_youzi (15.0), sentiment_analyst (50.0) |
| 600030 中信证券 | china_youzi (6.0) |

## 7. 测试结果

| 命令 | 结果 |
|------|------|
| `pytest tests/theme_sector_radar/ -q` | **988 passed, 3 skipped** |
| core preset | ✅ 5/7 succeeded, 2 fallback (data limitation) |
| rule-based differentiation | ✅ china_youzi now produces non-neutral signals |
