# Phase 57: Trend Scoring Semantic Repair Validation

## 1. 修复前问题复盘

### 问题 1: 收益率单位（max_drawdown 乘 100 问题）

- `calculate_drawdown_component`: `abs(max_drawdown) * 100` 将 -8.68% 误当成 -868%
- `calculate_risk_penalty`: 同样的 `* 100` 问题
- 结果：回撤扣分严重失真

### 问题 2: 动量加权方向

- `recent_returns[i] * (n - i)` 在日期升序数据中，早期收益权重更高
- 近期转强的板块被低估

### 问题 3: Benchmark 窗口不一致

- `sector_scoring_agent.py` 始终使用 `benchmark_returns.get("5d")`
- trend_window=20 时，板块用 20 日窗口但 benchmark 用 5 日

### 问题 4: 缺历史数据处理

- `insufficient_history` 的板块没有降权，可能排到趋势榜前面

## 2. 修改文件列表

| 文件 | 修改内容 |
|------|----------|
| `theme_sector_radar/scoring/sector_composite_score.py` | 修复 drawdown/risk_penalty 单位、动量方向、新增 insufficient_history cap |
| `theme_sector_radar/agents/sector_scoring/sector_scoring_agent.py` | 修复 benchmark 窗口选择、应用 insufficient_history cap |
| `theme_sector_radar/data/benchmark_provider.py` | 新增 10d/20d benchmark returns |
| `tests/theme_sector_radar/test_sector_composite_score.py` | 更新测试使用正确单位 |
| `tests/theme_sector_radar/test_trend_window.py` | 更新测试使用正确单位 |
| `docs/plans/phase57_trend_scoring_semantic_repair_plan.md` | 计划文档 |

## 3. 收益率单位最终约定

- `max_drawdown`: 百分数点，如 -8.68 表示 -8.68%
- `recent_returns`: 百分数点，如 2.5 表示 +2.5%
- `total_return`: 百分数点
- `volatility`: 百分数点标准差
- 阈值按百分数点解释：2 表示 2%，5 表示 5%，10 表示 10%

## 4. 动量加权方向说明

- `recent_returns[i] * (i + 1)`: 近期（日期升序中靠后的）权重更高
- 验证：`returns_a = [-2, -1, 0, 2, 3]`（近期转强）vs `returns_b = [3, 2, 0, -1, -2]`（早期转强），a 的 momentum 高于 b

## 5. benchmark 窗口选择规则

- trend_window=5 → 使用 5d benchmark
- trend_window=10 → 使用 10d benchmark
- trend_window=20 → 使用 20d benchmark
- 如果对应窗口不可用，fallback 到 5d 并记录警告

## 6. insufficient_history 降权规则

- `trend_window_status == "insufficient_history"` 或 `history_coverage_ratio < 0.5` 时
- 趋势分上限设为 34.9（cooling 区间上限）
- 缺历史数据板块不会因为无回撤扣分排到趋势榜前面

## 7. 2026-07-01 修复前后趋势 Top5 对比

| 排名 | 板块 | 趋势分 | 等级 |
|------|------|--------|------|
| 1 | 证券 | 34.9 | 偏弱（受 insufficient_history cap 限制） |
| 2 | 化学制药 | 29.3 | 偏弱 |
| 3 | 通信 | 28.3 | 偏弱 |
| 4 | 医疗器械 | 27.9 | 偏弱 |
| 5 | 种植业 | 26.1 | 偏弱 |

**观察**：修复后，缺历史数据的板块被正确 cap 到 cooling 区间上限（34.9），不再因无回撤扣分而排到趋势榜前面。

## 8. 测试结果

- `test_sector_composite_score.py`: 37 passed
- `test_trend_window.py`: 11 passed
- `test_sector_scoring_benchmark.py`: 8 passed
- `test_cli_sector_scoring.py`: 9 passed

**专项测试：65 passed**

## 9. 是否修改 ai-hedge-fund：否

本阶段所有修改仅限于 `theme-sector-radar-dev` 项目，未修改 `ai-hedge-fund`。
