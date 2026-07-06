# Phase 26A.2: Agent 计数校准与 preset 边界修复 验收报告

**日期**: 2026-07-05  
**项目**: ai-hedge-fund + theme-sector-radar-dev

---

## 1. 修改文件清单

| 文件 | 改动 |
|------|------|
| `ai-hedge-fund/scripts/run_stock_agent_bridge.py` | +`--list-agents`, `--limit`; 修复 core preset (移除 risk_manager); 修复统计逻辑; +`per_agent_status`; 去重 agent 列表 |

## 2. Preset Agent 名单

```
core (7 agents):
   1. technical_analyst
   2. fundamentals_analyst
   3. valuation_analyst
   4. sentiment_analyst
   5. china_youzi
   6. industry_rotation
   7. growth_analyst

full (24 agents):
   1-13: aswath_damodaran, ben_graham, bill_ackman, cathie_wood,
         charlie_munger, michael_burry, mohnish_pabrai, nassim_taleb,
         peter_lynch, phil_fisher, rakesh_jhunjhunwala,
         stanley_druckenmiller, warren_buffett
   14-24: technical_analyst, fundamentals_analyst, growth_analyst,
          news_sentiment_analyst, sentiment_analyst, valuation_analyst,
          china_youzi, northbound_flow, policy_analyst,
          china_sentiment, industry_rotation
```

**风险模块** (不计入 analyst):
- `risk_manager` — 已从 core preset 移除，不参与投票
- `portfolio_manager` — 不在任何 preset 中

## 3. 多出来的第 25 个组件

**根因**: core preset 包含 `risk_manager`，但它不在 `MODULE_IMPORTS` (只包含 ANALYST_CONFIG 中的 24 个 analyst)。

**修复**: 从 core preset 移除 `risk_manager`，替换为 `growth_analyst`。core preset 现在也是 ANALYST_CONFIG 的子集。

## 4. 统计校准

### core preset (7 agents, 2 stocks)

```
agent_count: 7
succeeded: 4 (technical, fundamentals, valuation, sentiment)
failed: 0
fallback: 3 (china_youzi, industry_rotation, growth_analyst)
Sum: 4 + 0 + 3 = 7 ✓

per_agent_status:
  technical_analyst:   S=2 F=0 B=0 (2/2 succeeded)
  fundamentals_analyst: S=2 F=0 B=0 (2/2 succeeded)
  valuation_analyst:  S=2 F=0 B=0 (2/2 succeeded)
  sentiment_analyst:  S=1 F=0 B=1 (mixed)
  china_youzi:        S=0 F=0 B=2 (2/2 fallback)
  industry_rotation:  S=0 F=0 B=2 (2/2 fallback)
  growth_analyst:     S=0 F=0 B=2 (2/2 fallback)
```

### full preset (24 agents, 2 stocks)

```
agent_count: 24
succeeded: 8
failed: 0
fallback: 16
Sum: 8 + 0 + 16 = 24 ✓
```

## 5. 2026-07-03 Bridge 运行摘要

### core preset

```
1. TCL科技     score=54.9 B2/H3/S1 risk=high
2. 派林生物     score=53.4 B2/H2/S2 risk=low
3. 深科技       score=53.2 B2/H2/S2 risk=high
```

### full preset

```
1. 600030 中信证券  score=50.4 B1/H23/S0
2. 601211 国泰君安  score=50.4 B1/H23/S0
```

## 6. 测试结果

| 命令 | 结果 |
|------|------|
| `pytest tests/theme_sector_radar/ -q` | **988 passed, 3 skipped** |
| `--list-agents` | ✅ 4 presets, correct counts |
| core preset | ✅ 7 agents, 4 succeeded |
| full preset | ✅ 24 agents, 8 succeeded |

## 7. 验收标准

| 标准 | 状态 |
|------|------|
| full preset agent_count=24 | ✅ |
| succeeded + failed + fallback = agent_count | ✅ (7/7, 24/24) |
| per_agent_status 数量 = agent_count | ✅ |
| risk_manager 不在 preset 中 | ✅ (已移除) |
| portfolio_manager 不运行 | ✅ |
| core preset 差异化评分 | ✅ |
| full preset LLM 成功 | ✅ (8/24 succeeded) |
| 测试不回归 | ✅ 988 passed |
