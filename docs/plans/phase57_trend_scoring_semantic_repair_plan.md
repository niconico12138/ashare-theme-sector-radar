# Phase 57: Trend Scoring Semantic Repair Plan

## 问题审计结果

### 问题 1: 收益率单位（max_drawdown 乘 100 问题）

**位置**: `sector_composite_score.py` 第 271 行和第 380 行

- `calculate_drawdown_component`: `drawdown_pct = abs(max_drawdown) * 100` — max_drawdown 已经是百分数点（如 -8.68 表示 -8.68%），再乘 100 导致 -868% 级别惩罚。
- `calculate_risk_penalty`: 同样的问题，`drawdown_pct = abs(max_drawdown) * 100`。

**修复**: 移除 `* 100`，因为 max_drawdown 已经是百分数点。

### 问题 2: 动量加权方向

**位置**: `sector_composite_score.py` 第 145 行

- 当前: `recent_returns[i] * (n - i)` — 日期升序数据中，早期（i=0）权重最高（n），近期权重最低（1）。
- 应为: `recent_returns[i] * (i + 1)` — 近期权重最高。

### 问题 3: Benchmark 窗口不一致

**位置**: `sector_scoring_agent.py` 第 158 行

- 当前: `actual_benchmark_return = benchmark_returns.get("5d", 0.0)` — 无论 trend_window 是 5/10/20 都用 5d。
- 应为: 根据 trend_window 选择对应的 benchmark returns。

**位置**: `benchmark_provider.py` 第 220-259 行
- `calculate_benchmark_returns` 只返回 1d/3d/5d，缺少 10d/20d。

### 问题 4: 缺历史数据处理

**位置**: `sector_scoring_agent.py` 第 143 行
- `trend_window_status = "insufficient_history"` 时，趋势分没有降权，板块仍可能排到趋势榜前面。

### 问题 5: 趋势分语义

- 当前趋势分更像"趋势质量分"，报告和字段解释需要更清楚。

## 修复方案

### 1. 统一收益率单位
- 移除 `calculate_drawdown_component` 中的 `* 100`
- 移除 `calculate_risk_penalty` 中的 `* 100`
- 阈值按百分数点解释：2 表示 2%，5 表示 5%，10 表示 10%

### 2. 修复动量加权方向
- `recent_returns[i] * (i + 1)` 替代 `recent_returns[i] * (n - i)`

### 3. 修复 benchmark 窗口
- `benchmark_provider.py`: 增加 10d 和 20d 计算
- `sector_scoring_agent.py`: 根据 trend_window 选择对应 benchmark

### 4. insufficient_history 降权
- `trend_window_status == "insufficient_history"` 或 `history_coverage_ratio < 0.5` 时，趋势分上限设为 34.9（cooling 区间上限）

### 5. 保持短线评分独立
- 不修改 short_term_burst_score 公式
