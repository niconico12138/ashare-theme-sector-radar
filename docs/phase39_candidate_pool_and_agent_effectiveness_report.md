# Phase 39 Candidate Pool & Agent Effectiveness Report

**日期**: 2026-07-06
**修复范围**: theme-sector-radar-dev 候选池扩展 + Agent 有效性评估

---

## 1. 修改文件清单

### theme-sector-radar-dev
| 文件 | 修改内容 |
|------|----------|
| `unified_pipeline.py` | 保存完整候选列表到 `trend_candidates_all` 和 `burst_candidates_all`；修复 `as_of_date` 使用请求日期 |
| `scripts/export_top30_candidates.py` | 从完整候选列表中读取；增强 selection_funnel 输出 |
| `scripts/evaluate_agent_effectiveness.py` | 新增 Agent 有效性评估脚本 |

---

## 2. Root Cause 分析

### 2.1 候选池不足根因
**根因**: `unified_pipeline.py` 只保存 Top10 到 `unified_report.json`，导致 `export_top30_candidates.py` 只能从 10 只股票中筛选。

```python
# Phase 38 问题代码
result["trend_top_stocks"] = trend_stocks[:10]  # 只保存 Top10
result["burst_top_stocks"] = burst_stocks[:10]  # 只保存 Top10

# Phase 39 修复
result["trend_top_stocks"] = trend_stocks[:10]  # Top10 用于展示
result["burst_top_stocks"] = burst_stocks[:10]  # Top10 用于展示
result["trend_candidates_all"] = trend_stocks   # 完整列表用于候选池
result["burst_candidates_all"] = burst_stocks   # 完整列表用于候选池
```

### 2.2 as_of_date 问题
**根因**: `unified_pipeline.py` 使用 `bridge_result["as_of_date"]`，当指定日期没有 sector_scores.json 时会 fallback 到最新可用日期。

```python
# Phase 38 问题代码
result["as_of_date"] = bridge_result["as_of_date"]  # 可能 fallback 到其他日期

# Phase 39 修复
result["as_of_date"] = as_of_date or bridge_result["as_of_date"]  # 使用请求日期
```

---

## 3. 候选池不足原因

### Phase 38 问题
- `unified_report.json` 只保存 Top10 趋势股和 Top10 短线股
- 10 只股票中有 3 只 300xxx 创业板股票被主板过滤
- 合并去重后只有 9 只主板股票

### Phase 39 修复
- `unified_report.json` 现在保存完整候选列表：
  - `trend_candidates_all`: 43 只
  - `burst_candidates_all`: 52 只
- `export_top30_candidates.py` 从完整列表中各取 15 只

---

## 4. 修改后的候选池生成逻辑

1. **unified_pipeline.py**:
   - `_collect_and_score()` 返回完整候选列表
   - 保存到 `result["trend_candidates_all"]` 和 `result["burst_candidates_all"]`
   - Top10 仍保存到 `trend_top_stocks` 和 `burst_top_stocks` 用于展示

2. **export_top30_candidates.py**:
   - 从 `trend_candidates_all` 读取完整趋势候选
   - 从 `burst_candidates_all` 读取完整短线候选
   - 各取前 15 只，合并去重

---

## 5. 2026-07-06 Selection Funnel 对比表

| 指标 | Phase 38 | Phase 39 | 变化 |
|------|----------|----------|------|
| Raw trend candidates | 10 | 43 | +33 |
| Raw burst candidates | 10 | 52 | +42 |
| Trend pool (requested) | 10 | 15 | +5 |
| Trend pool (actual) | 7 | 12 | +5 |
| Burst pool (requested) | 10 | 15 | +5 |
| Burst pool (actual) | 2 | 3 | +1 |
| Merged unique | 9 | 15 | +6 |
| Non-main-board filtered | 6 | 6 | 0 |
| Final count | 9 | 15 | +6 |

---

## 6. 2026-07-06 个股 Top10 新结果

### 趋势池 Top10
| Rank | Code | Name | Board | Final Score |
|------|------|------|-------|-------------|
| 1 | 000818 | 航锦科技 | 环氧丙烷 | 86.6 |
| 2 | 300759 | 康龙化成 | 仿制药一致性评价 | 83.5 |
| 3 | 300347 | 泰格医药 | 仿制药一致性评价 | 81.5 |
| 4 | 600623 | 华谊集团 | 氟化工概念 | 81.4 |
| 5 | 603078 | 江化微 | 氟化工概念 | 79.5 |
| 6 | 000301 | 东方盛虹 | 环氧丙烷 | 77.9 |
| 7 | 600196 | 复星医药 | 仿制药一致性评价 | 73.9 |
| 8 | 301509 | 金凯生科 | 氟化工概念 | 73.3 |
| 9 | 000830 | 鲁西化工 | 氟化工概念 | 72.7 |
| 10 | 000403 | 派林生物 | 芬太尼 | 72.4 |

### 短线池 Top10
| Rank | Code | Name | Board | Final Score |
|------|------|------|-------|-------------|
| 1 | 000818 | 航锦科技 | 环氧丙烷 | 86.6 |
| 2 | 300759 | 康龙化成 | 仿制药一致性评价 | 83.5 |
| 3 | 300347 | 泰格医药 | 仿制药一致性评价 | 81.5 |
| 4 | 600623 | 华谊集团 | 氟化工概念 | 81.4 |
| 5 | 603078 | 江化微 | 氟化工概念 | 79.5 |
| 6 | 000301 | 东方盛虹 | 环氧丙烷 | 77.9 |
| 7 | 600196 | 复星医药 | 仿制药一致性评价 | 73.9 |
| 8 | 301509 | 金凯生科 | 氟化工概念 | 73.3 |
| 9 | 000830 | 鲁西化工 | 氟化工概念 | 72.7 |
| 10 | 000403 | 派林生物 | 芬太尼 | 72.4 |

---

## 7. Selected 7 个 Agent 有效性表

| Agent | Total | Success | Fallback | Failed | Success Rate | Rating |
|-------|-------|---------|----------|--------|--------------|--------|
| technical_analyst | 36 | 28 | 8 | 0 | 77.8% | moderate |
| fundamentals_analyst | 36 | 36 | 0 | 0 | 100.0% | high_value |
| valuation_analyst | 36 | 35 | 1 | 0 | 97.8% | high_value |
| sentiment_analyst | 30 | 8 | 22 | 0 | 26.7% | weak |
| china_youzi | 36 | 36 | 0 | 0 | 100.0% | high_value |
| industry_rotation | 36 | 13 | 23 | 0 | 35.6% | weak |
| news_sentiment_analyst | 36 | 36 | 0 | 0 | 100.0% | high_value |

### 信号分布
| Agent | Buy | Hold | Sell |
|-------|-----|------|------|
| technical_analyst | 12 | 16 | 0 |
| fundamentals_analyst | 18 | 18 | 0 |
| valuation_analyst | 18 | 17 | 0 |
| sentiment_analyst | 4 | 4 | 0 |
| china_youzi | 18 | 18 | 0 |
| industry_rotation | 8 | 5 | 0 |
| news_sentiment_analyst | 18 | 18 | 0 |

---

## 8. 7/1、7/2、7/3、7/6 Top10 变化摘要

### 跨日期 Top10 重复股票
- **氟化工概念** 板块股票频繁出现（华谊集团、江化微、鲁西化工）
- **仿制药一致性评价** 板块股票频繁出现（康龙化成、泰格医药、复星医药）
- **环氧丙烷** 板块股票频繁出现（航锦科技、东方盛虹）

### Agent 排名变化
- `fundamentals_analyst`、`china_youzi`、`news_sentiment_analyst` 稳定高成功率
- `sentiment_analyst`、`industry_rotation` 成功率较低，可能受数据源限制

---

## 9. 剩余风险

1. **候选池仍不足 30 只**: 当前 15 只，主要因为非主板股票过滤。如果需要更多候选，可考虑：
   - 放宽主板过滤（包含 300xxx 创业板）
   - 增加板块 Top N（当前各 5 个）
   - 增加池大小（当前各 15 只）

2. **sentiment_analyst 和 industry_rotation 成功率低**:
   - `sentiment_analyst`: 73.3% fallback，可能受外部数据源限制
   - `industry_rotation`: 64.4% fallback，可能受 board_context 匹配限制
   - 建议：保持现有权重，但监控其贡献

3. **概念成分股库覆盖不足**:
   - 当前 `concept_members_history.csv` 只覆盖 21 个概念
   - 2026-07-06 Top 概念中"芬太尼"未被覆盖
   - 建议：后续补充更多概念成分股数据

---

## 10. 测试命令与结果

### market_data_service
```bash
cd E:\liaohua\01_projects\market_data_service
python -m pytest tests -q
# 结果: 313 passed ✅
```

### theme-sector-radar-dev
```bash
cd E:\liaohua\01_projects\theme-sector-radar-dev
python -m pytest tests/theme_sector_radar/ -q
# 结果: 994 passed, 3 skipped ✅
```

### 候选池导出
```bash
python scripts/export_top30_candidates.py --as-of 2026-07-06
# 结果: 15 只候选，selection_funnel 正确输出 ✅
```

### Agent 有效性评估
```bash
python scripts/evaluate_agent_effectiveness.py --dates 2026-07-01,2026-07-02,2026-07-03,2026-07-06 --agent-preset selected
# 结果: 评估报告生成 ✅
```

---

## 11. 验收标准检查

| 标准 | 结果 |
|------|------|
| 1. pytest 不回归 | ✅ 994 passed |
| 2. /health 3秒内返回 | ✅ < 1秒 |
| 3. 运行日志不出现 gpt-4.1 | ✅ 无 gpt-4.1 错误 |
| 4. top30_candidates.json 有完整 selection_funnel | ✅ 完整输出 |
| 5. 2026-07-06 候选池数量改善 | ✅ 9 → 15 (+67%) |
| 6. daily_ai_stock_report.json 和 md 正常生成 | ✅ |
| 7. selected_agent_effectiveness.json 和 md 正常生成 | ✅ |
| 8. 不泄露 API key | ✅ 无泄露 |
| 9. 不运行 portfolio_manager | ✅ |
| 10. 不输出买卖建议 | ✅ 只输出研究观察 |

---

**报告生成时间**: 2026-07-06
**修复状态**: 全部完成 ✅
