# Factor Semantics Contract

> 版本: 1.0 | 创建: 2026-07-11 | 阶段: Phase 47

## 1. Purpose

本文档固定 shadow-only bars 因子的语义规则，确保日报、decision_summary、evaluation report 和自动化流程不会误读因子含义。

所有下游消费方（报告生成、候选筛选、复盘脚本）必须遵守本 contract。

## 2. Global Rules

1. **shadow-only 因子不得改变正式排序** — final_score / v2_score / selection_score / selection_score_adjusted 不受 bars 因子影响。
2. **profile_only 不得作为触发或过滤条件** — 仅用于展示和上下文。
3. **structure_candidate 不等于买入触发** — 仅标记结构位置，不产生交易动作。
4. **repair_context 不等于风险恶化** — deep pullback 可能是修复机会，非自动负面信号。
5. **soft_warning 不等于自动剔除** — 仅提示需关注，不改变 selection_bucket。
6. **不得从任何因子直接生成买入点** — 买入点必须有独立 setup/entry 模块。
7. **所有候选仍为 watch_only** — action_state 恒定为 watch_only。

## 3. Bars Factor Semantics

### 3.1 breakout_distance_20

| 属性 | 值 |
|------|-----|
| raw meaning | 当前价格距离近20日高点的百分比距离 |
| score meaning | 预计算结构位置评分 (100=贴近高点, 0=远离) |
| profile state | breakout_structure |
| allowed states | near (raw≤3) / neutral (3<raw≤10) / far (raw>10) / unknown |
| allowed policy | structure_candidate / profile_only / calibration_needed |

**forbidden interpretation:**
- 不得解释为突破触发
- 不得解释为买入信号
- 不得默认认为 near 优于 neutral/far（历史复盘显示 near 组不一定优于 far 组）

### 3.2 drawdown_depth_20

| 属性 | 值 |
|------|-----|
| raw meaning | 当前价格相对近20日高点的回撤百分比 |
| note | raw 与 breakout_distance_20 当前数值相同 |
| score meaning | 预计算回撤状态评分 |
| profile state | drawdown_state |
| extra context | drawdown_context |
| allowed states | healthy (raw≤5) / normal (5<raw≤15) / deep (raw>15) / unknown |
| drawdown_context mapping | healthy→shallow_pullback, normal→normal_pullback, deep→repair_opportunity_possible |
| allowed policy | repair_context / profile_only / calibration_needed |

**forbidden interpretation:**
- deep 不得自动解释为坏信号
- deep 不得自动 hard_block
- 不得和 breakout_distance_20 重复计权

### 3.3 chasing_risk_score

| 属性 | 值 |
|------|-----|
| raw/score meaning | 0-100 的追高/过热风险评分 (score = raw_value) |
| profile state | overheat_state |
| allowed states | high (≥70) / watch (60≤x<70) / normal (<60) / unknown |
| allowed policy | soft_warning / display_only / profile_only |

**allowed interpretation:**
- high 可作为 shadow 风险提示

**forbidden interpretation:**
- 不得自动剔除
- 不得直接生成交易动作

### 3.4 liquidity_score

| 属性 | 值 |
|------|-----|
| meaning | 成交额流动性画像 |
| profile state | liquidity_state |
| allowed states | strong (≥75) / normal (40≤x<75) / weak (<40) / unknown |
| allowed policy | profile_only |

**forbidden interpretation:**
- weak 样本不足，不得自动过滤
- strong 不得自动加分到正式排序

## 4. Reason Code Contract

### 4.1 Current Reason Codes (Phase 46+)

| reason_code | 来源因子 | 含义 |
|-------------|---------|------|
| structure_near_high_position | breakout_distance_20 | 距20日高点近，结构位置标签 |
| structure_neutral_position | breakout_distance_20 | 距20日高点中等距离 |
| structure_far_from_high | breakout_distance_20 | 距20日高点较远 |
| shallow_pullback_state | drawdown_depth_20 | 浅回撤状态 |
| normal_pullback_state | drawdown_depth_20 | 正常回撤状态 |
| deep_pullback_repair_context | drawdown_depth_20 | 深回撤修复上下文 |
| overheat_risk_high | chasing_risk_score | 过热风险高 |
| overheat_risk_watch | chasing_risk_score | 过热风险关注 |
| overheat_risk_normal | chasing_risk_score | 过热风险正常 |
| liquidity_strong | liquidity_score | 流动性好 |
| liquidity_normal | liquidity_score | 流动性一般 |
| liquidity_weak | liquidity_score | 流动性弱 |

### 4.2 Forbidden Legacy Semantics

以下旧 reason_code 不得在生产输出中出现：

| 旧 code | 问题 |
|---------|------|
| near_breakout_structure | 暗含突破触发语义 |
| breakout_structure_watch | 旧语义 |
| far_from_breakout | 旧语义 |
| healthy_drawdown | 旧语义 |
| normal_drawdown | 旧语义 |
| deep_drawdown_risk | 暗含自动负面结论 |
| drawdown_too_deep | 暗含自动剔除 |

## 5. Report Wording Contract

### 5.1 Allowed Words

日报和 compact report 中允许使用：

- 结构位置
- 回撤状态
- 修复上下文
- 过热风险
- 流动性
- 观察
- 复核
- watch_only
- shadow-only

### 5.2 Forbidden Trade Words

以下词汇不得出现在任何生产报告输出中：

- 买入
- 卖出
- 持有
- 推荐
- 建仓
- 加仓
- 减仓
- 止盈
- 止损
- 目标价
- 交易触发
- 突破触发
- 自动剔除
- 自动纳入

## 6. Evaluation Recommendation Contract

| 场景 | forbidden | allowed |
|------|-----------|---------|
| breakout near | keep_trigger_candidate | keep_structure_candidate / structure_position_only |
| drawdown deep | keep_soft_warning (除非历史明确为负面) | keep_repair_context / repair_context |
| overheat high | — | keep_soft_warning |
| liquidity weak | — | insufficient_sample |

## 7. Future Extension Rules

1. 若未来进入买入点阶段，必须新增独立 setup/entry 模块。
2. 不得复用 profile-only 因子直接生成买入点。
3. 买入点必须有单独回测和无效条件。
4. 任何新因子必须先通过 shadow-only 验证，再考虑纳入正式逻辑。
