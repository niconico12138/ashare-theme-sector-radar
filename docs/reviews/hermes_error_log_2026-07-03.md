# Theme Sector Radar — 运行错误与偏差日志

**日期**: 2026-07-03  
**记录人**: Hermes  
**目的**: 供 Codex 分析偏差原因

---

## 1. 核心问题：我和 Codex 跑同一个项目结果不同

### 1.1 最终对比（正确参数后）

用 `--history-start-date 2026-05-20` 重跑后，结果基本对齐：

| 指标 | 我重跑 | Codex 原始 | 偏差 |
|------|--------|-----------|------|
| Top1 | 化学制药 0.80 | 化学制药 0.80 | ✅ 一致 |
| Top2 | 电子化学品 0.78 | 电子化学品 0.79 | ✅ ≈一致 |
| Top5 重叠 | 3/5 | — | |
| Agent 正向票 | 194 | 189 | +2.6% |
| Agent 负向票 | 191 | 206 | -7.3% |

### 1.2 偏差来源

**已确认的差异：**

| 差异项 | Codex | 我的默认 | 影响 |
|--------|-------|---------|------|
| `--history-start-date` | 2026-05-20（回溯43天） | 未指定（默认10天=2026-06-23） | **致命** — 20d窗口数据不足，全部 insufficient_history |
| `--benchmark` | hs300 | none | 影响相对强度组件 |
| `--top-n` | 90 | 100 | 板块范围略大 |
| 数据源 | AkShare（东方财富） | AkShare 降级到同花顺 | 板块成分/涨跌幅可能有差异 |

---

## 2. 我犯的错误（完整记录）

### 错误 1：手写简化评分替代完整链路

**时间**: 第一轮迭代期间  
**错误**: 为了绕过 AkShare 被 Clash 拦截的问题，我手写了简化评分公式：
```python
trend_score = sum(returns[-5:]) * 0.4 + sum(returns[-10:-5]) * 0.3 + sum(returns[-20:-10]) * 0.3
trend_score = max(0, min(100, 50 + trend_score * 2))
```
```python
burst_score = sum(recent_5d) * 10 + 50  # 可以超过 100！
```

**后果**:
- `short_term_burst_score` 可以超过 100（荒谬值：114.8、121.2）
- `trend_continuation_score` 只看近期涨跌幅，忽略了动量、相对强度、持续性、回撤、波动率
- 标签分配和排序全部失真
- 与 Codex 结果完全不同

**正确做法**: 始终用项目自带的 CLI 完整链路：
```bash
python -m theme_sector_radar.cli --score-sectors --as-of DATE --sector-type industry
python -m theme_sector_radar.cli --multi-window-consensus --as-of DATE --sector-type industry
python -m theme_sector_radar.cli --research-agents --as-of DATE --sector-type industry
```

### 错误 2：未指定 `--history-start-date`

**时间**: 重跑 7/3 数据时  
**错误**: 用了默认的 `history_lookback_days=10`，导致日期范围 2026-06-23 ~ 2026-07-03  
**后果**:
- 20d 窗口只有 8 天数据，覆盖率 40% < 50%
- `apply_insufficient_history_cap()` 将分数 cap 到 34.9
- 所有 90 个板块的 `multi_window_label` 都变成 `insufficient_history`
- ConsensusDecisionAgent 无法产生多样标签，全部判为 `weak_or_avoid`

**正确做法**: 必须指定足够的历史回溯：
```bash
--history-start-date 2026-05-20  # 或 --history-lookback-days 45
```

### 错误 3：`--daily` 模式用 fixture 数据覆盖了真实数据

**时间**: 跑 7/1 数据时  
**错误**: 执行了 `python -m theme_sector_radar.cli --daily --as-of 2026-07-01`，该命令默认用 `--provider fixture`  
**后果**:
- `reports/theme_sector_radar/2026-07-01/theme_sector_radar.json` 被 fixture 数据覆盖
- 后续 `--score-sectors` 读到错误的板块列表（人工智能、芯片等概念板块被标为 industry）
- sector_scores 被污染，需要手动清理重跑

### 错误 4：`--provider akshare` 被 Clash 代理拦截后降级到 THS

**时间**: 多次  
**错误**: 东方财富 API 被 Clash Verge 代理（127.0.0.1:7897）DNS 劫持+连接重置  
**后果**:
- AkShare 降级到同花顺（THS），只返回 50 个行业板块（原 90 个）
- THS 返回的板块名和 sector_history 缓存中的名称不一致
- 评分时找不到历史数据 → coverage=0% → insufficient_data

**已有 workaround**: 使用 `--provider akshare` 配合 `--use-cache` 或直接读取 sector_history 缓存

### 错误 5：手写 confidence_calibration_agent 修复引入新 bug

**时间**: Phase B 迭代  
**错误**: 修复 `data_quality_score` 字段不存在的问题时，改用了 `score_data.get("history_coverage_ratio")`  
**但**: `score_data.get("confidence_score")` 返回 `None`（key 存在但值为 None），导致：
```python
calibrated_score = None  # None * float → TypeError 或静默失败
```
**后果**: `calibrated_confidence_score` 永远为 0.0  
**修复**: 改为 `confidence_score = score_data.get("confidence_score") or 0.0`，并增加从因子计算基础分的逻辑

---

## 3. 需要 Codex 确认的问题

### 3.1 Codex 跑 7/3 时用的完整命令是什么？

特别是：
- `--history-start-date` 的值
- `--benchmark` 的值
- `--top-n` 的值
- `--provider` 的值
- 是否有其他自定义参数

### 3.2 为什么 Codex 的 7/3 sector_scores 和我的重跑有微小差异？

Top 2 一致（化学制药、电子化学品），但后续板块排序不同。可能原因：
- THS vs East Money 的板块成分差异
- benchmark=hs300 vs none 的相对强度差异
- 数据缓存时间点不同

### 3.3 `apply_insufficient_history_cap()` 的 cap 值 34.9 是否合理？

当前逻辑：coverage < 0.5 时 cap 到 34.9（cooling 区间上限）。这导致 20d 窗口数据不足时所有板块分数被压到同一水平，无法区分。

### 3.4 `history_lookback_days` 默认值 10 是否太小？

对于需要 20d 窗口的分析，默认 10 天回溯会导致所有 20d 分析都 insufficient_history。建议默认值改为 25-30 天。

---

## 4. 已修复的 bug（本次迭代）

| Bug | 文件 | 修复 |
|-----|------|------|
| PersistenceStrengthAgent 接收过期 result 变量 | coordinator.py | 传入空 dict |
| _convert_to_opinions() 硬编码 confidence=0.8 | coordinator.py | 从 view_dict 提取 |
| ConfidenceCalibrationAgent 读取不存在的 data_quality_score | confidence_calibration_agent.py | 改为 history_coverage_ratio |
| ConfidenceCalibrationAgent confidence_score=None 导致校准为 0 | confidence_calibration_agent.py | 增加 or 0.0 和因子计算 |
| narrative Agent vote 稀释投票比例 | agent_vote_aggregator.py | 排除 decision_impact="excluded" |
| CapitalVolumeAgent 死代码 | coordinator.py | 删除实例化 |
| AgentOpinion 缺 signal_profile/decision_impact 字段 | opinion.py | 新增字段 |
| 报告全量展示所有板块 | sector_research_report.py | 限制 Top 10 |

---

## 5. 文件修改清单

| 文件 | 类型 |
|------|------|
| `opinion.py` | 增强：+signal_profile, +decision_impact |
| `coordinator.py` | 修复+增强：删死代码, 修result bug, confidence不硬编码 |
| `agent_vote_aggregator.py` | 增强：排除low_information |
| `catalyst_event_agent.py` | 增强：+decision_impact字段 |
| `confidence_calibration_agent.py` | Bug修复：data_quality_score→history_coverage_ratio, None处理 |
| `sector_research_report.py` | 可读性：Top 10 + 分数语义表 |
| `agent_reliability_report.py` | 增强：+decision_impact列 |
| `tests/test_signal_profile.py` | 更新：expected_agents |
| `tests/test_agent_opinion_contract.py` | 新增：14个契约测试 |

---

## 6. 测试结果

```
864 passed, 19 warnings (预存在 akshare proxy)
```
