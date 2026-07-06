# Phase 51 后路线图

**日期**: 2026-07-01
**当前阶段**: Phase 51 - Release Snapshot & Operator Guide

---

## 已完成阶段总览

| Phase | 名称 | 状态 |
|-------|------|------|
| 1-7.5 | 离线 MVP → 发布前验收 | ✅ 完成 |
| 8-9 | 权重实验 + 真实数据验证 | ✅ 完成 |
| 10 | Sector History 下载器 | ✅ 完成 |
| 12-15.5 | 评分语义校准 | ✅ 完成 |
| 19-22 | Agent 分层架构 | ✅ 完成 |
| 24-25.5 | Agent 标签校准 | ✅ 完成 |
| 27-28 | 一个月回测验证 | ✅ 完成 |
| 29 | Agent 信号校准 | ✅ 完成 |
| 30 | Opportunity Rebound 验证 | ✅ 完成 |
| 31-34 | Market Regime 分层 | ✅ 完成 |
| 35 | 研究报告可用性 | ✅ 完成 |
| 36 | Daily Research Index | ✅ 完成 |
| 37 | Agent 可靠性仪表板 | ✅ 完成 |
| 38 | 低分离度 Agent 校准 | ✅ 完成 |
| 39-41 | 持续性信号研究 | ✅ 完成 |
| 42 | 稀疏高精度 Agent 处理 | ✅ 完成 |
| 43-49 | Catalyst 事件体系 | ✅ 完成 |
| 50 | Daily Production Readiness | ✅ 完成 |
| **51** | **Release Snapshot & Operator Guide** | **✅ 当前** |

---

## 后续路线

### Phase 52: Real Catalyst Network Validation

**目标**: 使用真实网络数据验证 CatalystEventAgent 信号有效性

**前置条件**:
- 网络环境可用 (AkShare/THS 接口)
- 真实催化事件样本积累

**执行内容**:
1. 运行 `--download-catalyst-events --network` 获取真实事件
2. 比较 fixture vs real 事件的映射率差异
3. 验证 `catalyst_observed` 标签在真实数据下的信号表现
4. 产出 Phase 49 (fixture) vs Phase 52 (real) 对比报告

**决策点**: 如果真实样本中 `catalyst_observed` 信号有效 (5日正收益率 > 55%)，考虑启用 vote；否则继续保持 report-only。

### Phase 53: Multi-Day Real Daily Observation

**目标**: 连续多日运行 real daily，观察系统稳定性

**前置条件**:
- Phase 52 完成
- 连续 5+ 个交易日网络可用

**执行内容**:
1. 连续运行 real daily 流程 (Step 1-7)
2. 观察 health check 连续 ok 天数
3. 记录 fallback 发生频率和原因
4. 验证 sector_research 连续性和一致性
5. 产出多日运行稳定性报告

**决策点**: 如果连续 5 天 health check = ok 且无 fallback，确认系统生产就绪。

### Phase 54: Catalyst Vote Calibration (仅当 real 样本充足)

**目标**: 基于真实样本校准 CatalystEventAgent 的 vote 权重

**前置条件**:
- Phase 52 完成且 `catalyst_observed` 样本 ≥ 30 个
- Phase 53 完成且系统稳定

**执行内容**:
1. 分析 `catalyst_observed` vs `no_catalyst_observed` 在真实数据下的表现差异
2. 如果信号有效，计算 vote 权重
3. 产出校准报告
4. **仅在证据充分时**修改 CatalystEventAgent 的 vote 逻辑

**决策点**: 如果真实样本不足 30 个或信号无统计显著性，继续保持 report-only。

---

## 长期愿景

| 方向 | 说明 |
|------|------|
| 盘中实时 | 当前仅盘后分析，未来可考虑盘中轻量级监控 |
| 个股关联 | 当前仅输出板块，未来可考虑板块-个股关联分析 |
| 自动化调度 | Windows 任务计划自动运行 (需用户手动配置) |
| 多数据源 | 接入更多数据源 (同花顺 iFinD 等) |

---

## 关键约束 (持续有效)

1. **不修改 ai-hedge-fund**: 始终保持独立
2. **不输出交易建议**: 只输出观察、复盘、验证、风险提示、候选、信号
3. **real/fixture/replay 严格分离**: 健康检查自动检测
4. **决策逻辑谨慎修改**: 只有证据充分时才调整 Agent vote

---

*本路线图由 Phase 51 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
