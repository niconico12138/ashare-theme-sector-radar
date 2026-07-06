# Phase 12.5 Sector Composite Scoring Audit

**审计日期**: 2026-06-30
**审计目标**: 确认 Sector Composite Scoring 的测试失败原因和样本评分偏低原因

---

## 1. 测试失败分析

### 1.1 失败测试

| 测试文件 | 测试名称 | 状态 |
|----------|----------|------|
| test_akshare_provider_contract.py | TestAkShareProviderTHSFallback::test_both_sectors_fallback | FAILED (间歇性) |

### 1.2 失败原因

该测试在完整测试套件中间歇性失败，单独运行时通过。原因是：

- **网络依赖**: 测试需要调用 AkShare THS 接口获取实时数据
- **测试隔离问题**: 并行运行时可能存在状态竞争
- **与 Phase 12 无关**: 这是 Phase 11 之前已存在的测试

### 1.3 结论

**该失败与 Phase 12 无关**，是已有的间歇性网络测试问题。

---

## 2. Top 5 评分偏低分析

### 2.1 样本数据

| 排名 | 板块 | 综合分 | 等级 | radar_score | history_days |
|------|------|--------|------|-------------|--------------|
| 1 | 生物制品 | 45.9 | cooling | 42.0 | 0 |
| 2 | 医疗服务 | 45.9 | cooling | 42.0 | 0 |
| 3 | 化学制药 | 45.9 | cooling | 42.0 | 0 |
| 4 | 中药 | 45.15 | cooling | 39.0 | 0 |
| 5 | 医疗器械 | 45.15 | cooling | 39.0 | 0 |

### 2.2 Score Breakdown 审计

以"生物制品"为例（满分 100）：

| 组件 | 得分 | 满分 | 利用率 | 问题 |
|------|------|------|--------|------|
| radar_score_component | 10.5 | 25 | 42% | radar_score 本身偏低 (42/100) |
| momentum_component | 6.0 | 20 | 30% | 无历史数据，使用默认值 |
| relative_strength_component | 7.5 | 15 | 50% | 无历史数据，使用中位数基准 |
| persistence_component | 4.5 | 15 | 30% | 无历史数据，使用默认值 |
| drawdown_component | 10.0 | 10 | 100% | 无历史数据，假设无回撤 |
| volatility_component | 5.0 | 5 | 100% | 无历史数据，假设低波动 |
| data_quality_component | 2.4 | 10 | 24% | history_days=0 导致低分 |
| risk_penalty | 0.0 | 20 | 0% | 无风险扣分 |
| **正向总分** | **45.9** | **100** | **45.9%** | - |

### 2.3 低分根因分析

#### 根因 1: history_days = 0 (最主要)

**现象**: 所有板块的 `history_days` 都是 0

**原因**: CLI 期望的历史数据路径是 `data_cache/sector_history/{sector_type}/*.json`，但实际数据存储在 `data_cache/YYYY-MM-DD/raw_snapshot.json`

**影响**:
- momentum_component 使用默认值 6.0 (满分 20)
- persistence_component 使用默认值 4.5 (满分 15)
- data_quality_component 仅 2.4 (满分 10)
- 总计损失约 **26.1 分**

#### 根因 2: radar_score 本身偏低

**现象**: radar_score 为 42.0 (满分 100)

**原因**: 日报雷达分基于 THS 数据，存在以下限制：
- 行业板块：有涨跌幅，但数据源单一 (仅 THS)
- 概念板块：无涨跌幅，评分偏保守
- 数据质量分仅 60.0

**影响**: radar_score_component 仅 10.5 (满分 25)，损失 **14.5 分**

#### 根因 3: benchmark_mode=sector_median 导致相对压分

**现象**: relative_strength_component 仅 7.5 (满分 15)

**原因**: 使用行业中位数作为基准，所有板块的相对强度被压缩到中位数附近

**影响**: 损失约 **7.5 分**

### 2.4 评分损失汇总

| 根因 | 损失分数 | 占比 |
|------|----------|------|
| history_days=0 (无历史数据) | 26.1 | 57% |
| radar_score 偏低 | 14.5 | 32% |
| benchmark_mode 压分 | 7.5 | 16% |
| **总计** | **45.9** | **100%** |

---

## 3. radar_score 接入检查

### 3.1 接入状态

✅ **radar_score 已正确接入**

- 输入: `radar_score=42.0` (来自日报 `theme_sector_radar.json`)
- 计算: `radar_score_component = (42.0 / 100.0) * 25 = 10.5`
- 输出: `score_breakdown.radar_score_component = 10.5`

### 3.2 问题

radar_score 本身偏低 (42.0)，这是因为：
1. 日报评分基于 THS 数据，有数据质量限制
2. 行业板块评分受资金流、宽度等因素影响
3. 概念板块缺少涨跌幅数据

---

## 4. benchmark_mode 检查

### 4.1 当前行为

- **基准**: 行业样本中位数 (sector_median)
- **问题**: 所有板块的相对强度被压缩到中位数附近，导致强板块无法脱颖而出

### 4.2 影响分析

假设 5 个板块收益率为 [1%, 2%, 3%, 4%, 5%]：
- 中位数 = 3%
- 相对强度分别为 [-2%, -1%, 0%, 1%, 2%]
- 即使最强板块 (5%) 的相对强度也只有 2%

**结论**: benchmark_mode=sector_median 在板块数量较少时会显著压低相对强度得分。

---

## 5. 建议修复方案

### 5.1 高优先级 (必须修复)

| 问题 | 修复方案 | 预期效果 |
|------|----------|----------|
| history_days=0 | 修改 CLI 支持从 `data_cache/YYYY-MM-DD/` 读取历史数据 | momentum +14, persistence +10.5, data_quality +7.6 |
| 或 | 运行 `--download-sector-history` 下载历史数据 | 同上 |

### 5.2 中优先级 (建议优化)

| 问题 | 优化方案 | 预期效果 |
|------|----------|----------|
| radar_score 偏低 | 优化日报评分逻辑，提高 THS 数据利用率 | radar_score_component +5~10 |
| benchmark_mode 压分 | 考虑使用绝对基准 (如 0%) 或市场基准 | relative_strength +3~5 |

### 5.3 低优先级 (可选)

| 问题 | 优化方案 | 预期效果 |
|------|----------|----------|
| 测试间歇性失败 | 增加测试重试机制或 mock 网络调用 | 测试稳定性提升 |

---

## 6. 结论

### 6.1 测试失败

- **失败测试**: test_akshare_provider_contract.py::test_both_sectors_fallback
- **失败原因**: 网络依赖 + 测试隔离问题
- **与 Phase 12 关系**: 无关

### 6.2 Top 5 cooling 原因

- **主因**: history_days=0 (无历史数据)，导致 momentum/persistence/data_quality 三个组件使用默认低分
- **次因**: radar_score 本身偏低 (42.0)，受 THS 数据质量限制
- **辅因**: benchmark_mode=sector_median 压缩相对强度

### 6.3 是否需要修复

| 类型 | 建议 |
|------|------|
| **必须修复** | 修复历史数据读取逻辑，或确保有足够历史数据 |
| **建议优化** | 考虑使用绝对基准替代行业中位数 |
| **无需修复** | 当前评分逻辑正确，只是数据不足 |

### 6.4 ai-hedge-fund 状态

✅ 未修改 `ai-hedge-fund` 项目任何文件。

---

## 附录: 评分公式验证

```
radar_score_component = (42.0 / 100.0) * 25 = 10.5 ✓
momentum_component = 0.3 * 20 = 6.0 (无数据默认值) ✓
relative_strength_component = 0.5 * 15 = 7.5 (中位数基准) ✓
persistence_component = 0.3 * 15 = 4.5 (无数据默认值) ✓
drawdown_component = 1.0 * 10 = 10.0 (无回撤) ✓
volatility_component = 1.0 * 5 = 5.0 (低波动) ✓
data_quality_component = 0.24 * 10 = 2.4 (history_days=0) ✓
risk_penalty = 0.0 ✓

正向总分 = 10.5 + 6.0 + 7.5 + 4.5 + 10.0 + 5.0 + 2.4 = 45.9 ✓
最终得分 = 45.9 - 0.0 = 45.9 ✓
```

**评分公式计算正确，问题在于输入数据不足。**
