# Phase 42: Sparse High-Precision Agent Handling

## 本阶段目标

让系统正确理解不同 Agent 有不同的信号特征。

## 核心问题

PersistenceStrengthAgent 是高精度、低覆盖的信号（positive 6 样本，+7.38%，100%正确率），但 reliability dashboard 用覆盖率评价它，导致被标记为 low_reliability。

## 解决方案

1. 新增 `agent_signal_profile` 分类
2. 为每个 Agent 分配 signal profile
3. 更新 reliability dashboard 支持不同 profile 的展示
4. 不改变任何 Agent 的 vote 规则

## Signal Profiles

- broad_signal: 高覆盖普通信号（short_term_heat, rotation_analysis 等）
- sparse_high_precision: 低覆盖高命中信号（persistence_strength）
- low_information: 低信息 Agent（narrative）
- defensive_filter: 防守过滤 Agent（risk_control, data_quality）
