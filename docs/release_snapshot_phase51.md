# Phase 51: Release Snapshot

**日期**: 2026-07-01
**版本**: 0.1.0
**状态**: Phase 51 - Release Snapshot & Operator Guide

---

## 1. 当前能力地图

### 1.1 核心流水线

| 模块 | 能力 | 状态 |
|------|------|------|
| Daily Radar (`--daily`) | 行业/概念板块 Top N 筛选 | ✅ 生产就绪 |
| Sector Score (`--score-sectors`) | 双评分(趋势持续分+综合选择分) | ✅ 生产就绪 |
| Multi-Window Consensus (`--multi-window-consensus`) | 5/10/20 日窗口趋势共识 | ✅ 生产就绪 |
| Sector Research (`--research-agents`) | L1-L4 分层 Agent 综合研判 | ✅ 生产就绪 |
| Research Index (`--build-research-index`) | 多日研究索引构建 | ✅ 生产就绪 |
| Daily Health Check (`--daily-health-check`) | 每日流程完整性检查 | ✅ 生产就绪 |

### 1.2 Agent 层

| 层级 | Agent | 角色 | 是否参与决策 |
|------|-------|------|-------------|
| L1 数据证据 | EvidenceExtractionAgent | 证据提取 | ✅ 决策层 |
| L1 数据证据 | SignalNormalizationAgent | 信号标准化 | ✅ 决策层 |
| L2 专项分析 | TechnicalTrendAgent | 技术趋势 | ✅ 决策层 |
| L2 专项分析 | ShortTermHeatAgent | 短线热度 | ✅ 决策层 |
| L2 专项分析 | RotationAnalysisAgent | 轮动分析 | ✅ 决策层 |
| L2 专项分析 | CapitalVolumeAgent | 资金量能 | ✅ 决策层 |
| L2 专项分析 | RiskControlAgent | 风险控制 | ✅ 决策层 |
| L2 专项分析 | DataQualityAgent | 数据质量 | ✅ 决策层 |
| L2 专项分析 | MarketContextAgent | 市场环境 | ✅ 决策层 |
| L2 专项分析 | PersistenceStrengthAgent | 持续性强度 | ✅ 决策层 |
| L2 专项分析 | NarrativeAgent | 叙事总结 | ✅ 决策层 |
| L2 专项分析 | **CatalystEventAgent** | 催化事件 | ❌ **report-only** |
| L3 冲突一致 | AgentVoteAggregator | 投票聚合 | ✅ 决策层 |
| L3 冲突一致 | ConflictDetectionAgent | 冲突检测 | ✅ 决策层 |
| L3 冲突一致 | VetoRuleAgent | 否决规则 | ✅ 决策层 |
| L3 冲突一致 | ConfidenceCalibrationAgent | 置信度校准 | ✅ 决策层 |
| L4 最终决策 | ConsensusDecisionAgent | 共识决策 | ✅ 决策层 |
| 解释层 | **MarketRegimeContext** | 市场状态解释 | ❌ **report-only** |

### 1.3 数据模式

| 模式 | 命令 | 数据来源 | 用途 |
|------|------|----------|------|
| **real** | `--daily --provider akshare --refresh` | AkShare/THS 实时接口 | 每日盘后生产 |
| **fixture** | `--daily --offline-fixture` | 本地模拟数据 | 开发测试 |
| **replay** | `--replay-cache` / `--replay-daily-from-sector-history` | 缓存/历史数据回放 | 回测验证 |

### 1.4 报告体系

| 报告类型 | 路径 | 内容 |
|----------|------|------|
| Daily Radar | `reports/theme_sector_radar/YYYY-MM-DD/` | 板块筛选+轮动 |
| Sector Score | `reports/sector_scores/YYYY-MM-DD/` | 综合评分 |
| Multi-Window Consensus | `reports/sector_consensus/YYYY-MM-DD/` | 多窗口共识 |
| Sector Research | `reports/sector_research/YYYY-MM-DD/` | Agent 综合研判 |
| Research Index | `reports/sector_research/index/` | 多日索引 |
| Daily Health | `reports/daily_health/YYYY-MM-DD/` | 健康检查 |
| Catalyst Events | `data_cache/catalyst_events/YYYY-MM-DD/` | 催化事件缓存 |

---

## 2. Catalyst 当前状态

| 维度 | 状态 | 说明 |
|------|------|------|
| Cache | ✅ 已实现 | `CatalystEventCache` 持久化 events.json |
| Mapping Quality | ✅ 80% | Phase 48 增强后映射率从 20% 提升至 80% |
| report-only | ⚠️ 保持 | 不参与 vote/veto/scoring 决策 |
| 真实样本 | ❌ 0 个 | 所有 145 个事件均为 fixture，尚无真实网络事件验证 |
| 覆盖率 | 100% (fixture) | Phase 49 重建后 cache 覆盖率达 100% |

**结论**: Catalyst 当前仅用于复盘解释，不参与决策。需要 Phase 52 真实网络验证后才考虑是否启用 vote。

---

## 3. Market Regime 当前状态

| 维度 | 状态 | 说明 |
|------|------|------|
| 计算 | ✅ 已实现 | `MarketRegimeContext` 基于 benchmark 数据 |
| 解释层 | ✅ 已集成 | 为 sector_research 提供 regime 解释 |
| report-only | ⚠️ 保持 | 不参与 vote/veto/scoring 决策 |
| 分层回测 | ✅ 已完成 | Phase 31-34 完成 regime 分层分析 |

---

## 4. 已知限制

1. **Catalyst 无真实样本**: 所有催化事件均为 fixture，无法验证信号有效性
2. **Market Regime 为 report-only**: 仅提供解释，不参与决策
3. **AkShare 网络依赖**: real 模式依赖东方财富接口，网络失败时 fallback 到缓存
4. **历史数据覆盖**: sector_history 下载范围有限，部分板块历史数据不完整
5. **Benchmark 数据**: hs300/zz500 等基准数据需单独下载

---

## 5. 测试状态

- **总测试数**: ~219+ (pytest)
- **状态**: 全量通过
- **Doc contract tests**: `test_readme_contract.py`, `test_release_readiness.py`, `test_runbook_docs.py`

---

## 6. 项目边界确认

| 边界 | 状态 |
|------|------|
| 不修改 ai-hedge-fund | ✅ 未修改 |
| 不接入 LangGraph | ✅ 未接入 |
| 不输出 buy/sell/hold | ✅ 未输出 |
| 不输出个股推荐 | ✅ 未输出 |
| 不自动创建 Windows 任务计划 | ✅ 未创建 |

---

*本快照由 Phase 51 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
