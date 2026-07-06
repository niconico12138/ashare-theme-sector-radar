# Theme Sector Radar — 项目全景与优化方案

> 供 Codex 协作讨论。最后更新：2026-07-04

---

## 一、项目定位

独立 CLI 盘后分析系统，回答一个核心问题：**今天哪些行业/概念板块最强、哪些最弱、板块轮动了没有？**

| 项目 | 说明 |
|------|------|
| 版本 | v0.1.0 |
| 测试 | 219 passed |
| 语言 | Python 3.11+ |
| 框架 | 纯 Python + Pydantic，不依赖 LLM |
| 数据源 | AkShare（同花顺THS）/ 腾讯API / 新浪财经 |
| 运行方式 | CLI（`python -m theme_sector_radar.cli`） |
| 依赖 | `ai-hedge-fund` 的 venv（共享） |

**明确边界：**

- ✅ 输出板块强弱排名（行业 + 概念 Top N）
- ✅ 输出板块轮动变化（今日 vs 历史）
- ✅ 输出 JSON + Markdown 报告
- ❌ 不输出个股推荐
- ❌ 不做买卖建议
- ❌ 不接入自动交易

---

## 二、三层架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 板块评分（核心，已完成）                             │
│  theme_sector_radar CLI → 双评分 + 7 Agent 研判              │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 板块→个股桥接（已实现，覆盖不足）                    │
│  sector_stock_bridge.py → 成分股查询 + 三维度关联度           │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 联合选股（已实现，个股量化降级）                     │
│  unified_pipeline.py → 综合评分 + 趋势/短线 Top10            │
└─────────────────────────────────────────────────────────────┘
```

### 关键文件

| 文件 | 说明 | 代码量 |
|------|------|--------|
| `theme_sector_radar/cli.py` | CLI 入口，20+ 运行模式 | ~500 行 |
| `theme_sector_radar/pipeline.py` | 13 阶段主流程编排 | ~1025 行 |
| `theme_sector_radar/models.py` | Pydantic 数据模型 | ~216 行 |
| `theme_sector_radar/scoring/sector_composite_score.py` | 趋势持续评分 | ~748 行 |
| `theme_sector_radar/scoring/short_term_burst_score.py` | 短线爆发评分 | ~539 行 |
| `theme_sector_radar/agents/sector_research/` | 7+ 研判 Agent | ~20 个文件 |
| `sector_stock_bridge.py` | 板块→个股桥接层 | ~1006 行 |
| `unified_pipeline.py` | 联合选股管线 | ~509 行 |

---

## 三、双评分系统

### 3.1 趋势持续分（Sector Composite Score）

满分 100，评估板块**中长期趋势质量**。

| 组件 | 满分 | 计算逻辑 |
|------|------|----------|
| `radar_score_component` | 25 | 当日雷达评分归一化 |
| `momentum_component` | 20 | 近期收益率加权平均（近期权重更高） |
| `relative_strength_component` | 15 | 板块收益 vs 行业中位数 / 市场基准 |
| `persistence_component` | 15 | 上涨天数占比（≥80%→满分，<20%→0） |
| `drawdown_component` | 10 | 最大回撤越小越好（≤2%→满分，>15%→0） |
| `volatility_component` | 5 | 波动率越低越好 |
| `data_quality_component` | 10 | 数据完整性 × 历史天数 × 涨跌幅可用性 |
| `risk_penalty` | 0~20 | 扣减项（回撤大/波动高/下跌多） |

**等级：** strong_watch(≥80) → watch(≥65) → neutral(≥50) → cooling(≥35) → avoid(<35)

**两套权重 Profile：**

| Profile | radar | momentum | relative | persistence | drawdown | volatility | data_quality |
|---------|-------|----------|----------|-------------|----------|------------|--------------|
| baseline | 25 | 20 | 15 | 15 | 10 | 5 | 10 |
| trend_confirmation | 15 | 25 | 20 | 20 | 8 | 4 | 8 |

### 3.2 短线爆发分（Short Term Burst Score）

满分 100，评估板块**短线爆发力**。

| 组件 | 满分 | 计算逻辑 |
|------|------|----------|
| `radar_today_component` | 30 | 当天雷达评分归一化 |
| `one_day_change_component` | 20 | 单日涨幅（≥5%→满分） |
| `three_day_momentum_component` | 15 | 近 3 天平均收益 |
| `volume_or_heat_component` | 10 | 成交额（5 分）+ 主力净流入（5 分） |
| `rank_jump_component` | 10 | 排名变化（≥10 名→满分） |
| `data_quality_component` | 10 | 数据质量 |
| `burst_risk_penalty` | 0~20 | 单日暴涨>8% 扣 8 分 / 持续性差扣 5 分 |

**等级：** burst_hot(≥80) → burst_watch(≥65) → burst_neutral(≥50) → burst_fading(≥35) → burst_avoid(<35)

### 3.3 双评分交叉矩阵

| 趋势分 | 短线分 | Profile | 解读 |
|--------|--------|---------|------|
| ≥65 | ≥65 | `trend_and_burst_aligned` | 🔥 双重确认，最值得关注 |
| ≥65 | <50 | `trend_only` | 📈 趋势型，中长期观察价值高 |
| <50 | ≥65 | `burst_without_trend_confirmation` | ⚠️ 短线脉冲，需谨慎 |
| <50 | <50 | `weak_or_cooling` | 🚫 回避 |
| 其他 | 其他 | `neutral` | 等待确认信号 |

---

## 四、13 阶段 Pipeline

```
Phase 1:  数据获取（AkShare / 缓存 / sector_history fallback）
Phase 2:  数据标准化
Phase 3:  覆盖率和数据质量评估
Phase 4:  市场温度计算
Phase 5:  资金流关联
Phase 6:  正向评分（行业流向 + 概念热度）
Phase 7:  风险评估
Phase 8:  排名和关注等级
Phase 9:  成分股补充
Phase 10: 回避解释
Phase 11: 共振检测（行业 + 概念交集）
Phase 12: 轮动追踪（对比历史快照）
Phase 13: 生成报告（JSON + Markdown）
```

---

## 五、Agent 体系

### 5.1 评分 Agent（agents/sector_scoring/）

| Agent | 职责 |
|-------|------|
| `sector_scoring_agent` | 板块综合评分编排 |

### 5.2 研判 Agent（agents/sector_research/，共 20 个文件）

| Agent | 职责 |
|-------|------|
| `technical_trend_agent` | 技术趋势分析 |
| `short_term_heat_agent` | 短线热度分析 |
| `capital_volume_agent` | 资金量分析 |
| `catalyst_event_agent` | 催化剂事件分析 |
| `market_context_agent` | 市场环境分析 |
| `persistence_strength_agent` | 持续强度分析 |
| `risk_control_agent` | 风险控制分析 |
| `evidence_extraction_agent` | 证据提取 |
| `narrative_agent` | 叙事分析 |
| `data_quality_agent` | 数据质量评估 |
| `signal_normalization_agent` | 信号标准化 |
| `confidence_calibration_agent` | 置信度校准 |
| `conflict_detection_agent` | 冲突检测 |
| `veto_rule_agent` | 否决规则（一票否决） |
| `consensus_decision_agent` | 共识决策 |
| `coordinator` | 研判协调器 |
| `opinion` | Agent 意见数据模型 |

### 5.3 轮动 Agent（agents/sector_rotation/）

| Agent | 职责 |
|-------|------|
| `sector_rotation_agent` | 板块轮动检测 |

### 5.4 多窗口共识 Agent（agents/multi_window_consensus/）

| Agent | 职责 |
|-------|------|
| `multi_window_consensus_agent` | 5天/10天/20天窗口对比共识 |

### 5.5 辅助 Agent

| Agent | 职责 |
|-------|------|
| `data` (agents/data/) | 数据标准化、覆盖率、可靠性 |
| `defense_risk` (agents/defense_risk/) | 回避解释、风险评估 |
| `positive_scoring` (agents/positive_scoring/) | 行业流向、概念热度、市场温度 |
| `ranking_report` (agents/ranking_report/) | 排名生成、共振检测 |
| `sector_diagnosis` (agents/sector_diagnosis/) | 板块诊断 |

---

## 六、数据层

### 6.1 数据源

| 类型 | 来源 | 状态 |
|------|------|------|
| 行业板块日线 | AkShare 同花顺 THS | ⚠️ 受 Clash 代理干扰 |
| 概念板块日线 | AkShare 同花顺 THS | ⚠️ 受 Clash 代理干扰 |
| 板块成分股 | 东方财富 EM | ❌ 被封锁 |
| 个股行情 | 腾讯 API qt.gtimg.cn | ✅ 可用 |
| 指数数据 | 新浪财经 API | ✅ 可用 |
| 历史缓存 | `data_cache/` 目录 | ✅ |
| 测试数据 | `data/fixtures/` | ✅ |

### 6.2 缓存与 Fallback 机制

```
实时接口 → sector_history cache → raw_snapshot cache → Fixture
   ↓              ↓                      ↓               ↓
  首选         行业数据不足时          概念数据不足时     最终降级
```

- `data_cache/sector_history/`：按日期的板块历史数据
- `data_cache/raw_snapshot/`：原始快照缓存
- `data_cache/catalyst_events/`：催化剂事件缓存
- `data_cache/sector_stocks/`：成分股缓存

### 6.3 网络限制

Clash Verge 代理 (127.0.0.1:7897) 封锁东方财富所有 API：
- `push2.eastmoney.com` → 连接重置
- `push2ex.eastmoney.com` → 连接重置
- `nufm.dfcfw.com` → 连接重置
- 即使清除代理环境变量也无效（DNS 劫持级别）

**可用替代：** 腾讯 API、新浪财经 API

---

## 七、板块→个股桥接

### 7.1 关联度公式

```python
relevance_score = weight_score × 0.2 + rank_score × 0.4 + flow_alignment × 0.4
```

- **weight_score**：成分股权重归一化
- **rank_score**：个股涨幅在板块内的排名归一化
- **flow_alignment**：个股资金流与板块资金流的对齐度

### 7.2 内置板块映射（仅 20 个）

```python
SECTOR_STOCK_MAPPING = {
    "证券": [...],       # 中信证券、国泰君安、招商证券等
    "保险": [...],
    "化学制药": [...],
    "医疗服务": [...],
    "养殖业": [...],
    "教育": [...],
    "农产品加工": [...],
    "多元金融": [...],
    "物流": [...],
    "生物制品": [...],
    "电子化学品": [...],
    "半导体": [...],
    "小金属": [...],
    "光学光电子": [...],
    "厨卫电器": [...],
    "中药": [...],
    "能源金属": [...],
    "贵金属": [...],
    "机场航运": [...],
    "非金属材料": [...],
}
```

**⚠️ 覆盖严重不足：** 板块评分可以评 100+ 个板块，但只有 20 个有成分股映射。Top5 板块经常不在映射中。

---

## 八、联合选股管线

```
Step 1: 读取板块评分报告（或新生成）
Step 2: 板块→成分股+关联度
Step 3: 个股量化评分（降级方案：涨幅30分 + 成交额30分 + 估值40分）
Step 4: 综合排序 = 量化分×0.6 + 关联度×0.4
Step 5: 输出趋势 Top10 + 短线 Top10 个股
```

**降级量化评分（`_compute_fallback_quant_score`）：**

| 因子 | 满分 | 逻辑 |
|------|------|------|
| 涨幅排名分 | 30 | 涨 5% 拿满分，跌 >3% 拿 0 |
| 成交额排名分 | 30 | 用 total_mv 作为流动性代理 |
| 估值适中分 | 40 | PE 在 10~50 区间拿满分 |

**预留 Qlib 接口：** 当前未接入，个股量化用降级方案。

---

## 九、回测系统

| 模块 | 用途 |
|------|------|
| `backtest/sector_research_backtest.py` | 板块研究回测 |
| `backtest/catalyst_event_backtest.py` | 催化剂事件回测 |
| `backtest/persistence_signal_research.py` | 持续性信号研究 |
| `backtest/market_regime_analysis.py` | 市场环境分析 |
| `backtest/opportunity_rebound_analysis.py` | 机会反弹分析 |
| `backtest/agent_reliability.py` | Agent 可靠性评估 |
| `backtest/agent_layer_backtest.py` | Agent 层回测 |
| `backtest/generate_research_range.py` | 研究范围生成 |
| `backtest/replay_daily_from_sector_history.py` | 从历史数据重放日报 |

---

## 十、报告系统

### 报告目录

```
reports/theme_sector_radar/
  └── YYYY-MM-DD/
      ├── theme_sector_radar.json    # 完整 JSON 报告
      ├── theme_sector_radar.md      # Markdown 报告
      ├── raw_snapshot.json          # 原始快照
      └── run_log.json               # 运行日志
```

### 报告生成模块（reports/）

| 模块 | 用途 |
|------|------|
| `json_report.py` | JSON 报告生成 |
| `markdown_report.py` | Markdown 报告生成 |
| `daily_health_check.py` | 每日健康检查 |
| `sector_score_report.py` | 板块评分报告 |
| `sector_score_batch_report.py` | 批量评分报告 |
| `sector_research_report.py` | 研判报告 |
| `sector_research_index.py` | 研判索引 |
| `multi_window_consensus_report.py` | 多窗口共识报告 |
| `market_regime_report.py` | 市场环境报告 |
| `index_report.py` | 指数报告 |
| `agent_reliability_report.py` | Agent 可靠性报告 |
| `agent_layer_backtest_report.py` | Agent 层回测报告 |
| `catalyst_event_backtest_report.py` | 催化剂回测报告 |
| `opportunity_rebound_report.py` | 机会反弹报告 |
| `persistence_signal_report.py` | 持续性信号报告 |

---

## 十一、已知问题

### P0 — 核心阻塞

| 问题 | 影响 | 现状 |
|------|------|------|
| **东方财富 API 被封锁** | 无法获取板块成分股实时数据 | 腾讯/新浪降级 |
| **板块映射只有 20 个** | Top5 板块经常无成分股数据 | 待扩展到 40+ |
| **无真实资金流数据** | 关联度计算用中性值 | 等 API 恢复或替代 |

### P1 — 功能缺失

| 问题 | 影响 |
|------|------|
| **概念板块支持不完整** | 当前主要做行业板块，概念板块数据不全 |
| **Qlib 未接入** | 个股量化用降级方案（涨幅+成交额+估值） |
| **无盘中实时模式** | 仅支持盘后分析 |
| **板块轮动信号粗糙** | 只做排名对比，未检测"短线→趋势"切换 |

### P2 — 体验问题

| 问题 | 影响 |
|------|------|
| **CLI 参数过多** | 新手难以上手 |
| **报告缺少可视化** | 纯文本，无图表 |
| **无定时任务集成** | 每天需手动运行 |

---

## 十二、优化方案

### Phase A：扩展板块映射（最高优先级）

**问题：** 20 个映射无法覆盖 Top5 板块。

**方案：**

1. 从 AkShare 获取全部行业板块成分股（`stock_board_industry_cons_em`），按板块名建立完整映射
2. 对于东方财富被封锁的情况，准备离线映射文件（JSON），覆盖 50+ 高频板块
3. 每个板块选 5~10 只龙头股（按市值排序取前 10）
4. 缓存到 `data_cache/sector_stocks/mapping.json`

**预期效果：** Top10 板块 100% 有成分股数据。

**涉及文件：**
- `sector_stock_bridge.py` → 扩展 `SECTOR_STOCK_MAPPING`
- 新建 `data_cache/sector_stocks/mapping.json` → 离线映射

---

### Phase B：接入 market_data_service

**问题：** 数据获取逻辑散落在多个文件中，重复代码多。

**方案：**

`market_data_service` 项目已有统一数据层：

```python
from market_data_service import MarketDataClient

client = MarketDataClient()
stocks = client.get_board_constituents("半导体", board_type="industry")
summary = client.get_industry_summary()
events = client.get_concept_events()
```

将 `sector_stock_bridge.py` 和 `unified_pipeline.py` 中的数据获取替换为 `MarketDataClient`。

**涉及文件：**
- `sector_stock_bridge.py` → 替换 AkShare 直接调用
- `unified_pipeline.py` → 替换降级量化数据获取

---

### Phase C：优化双评分权重

**问题：** 权重配比未经回测验证。

**方案：**

1. 用回测系统（`backtest/`）跑历史数据
2. 以"板块评分 Top N 未来 N 天涨幅"为指标
3. Optuna 调参找到最优权重配比
4. 至少测试 3 种 profile：`baseline`、`trend_confirmation`、`burst_focused`

**涉及文件：**
- `scoring/sector_composite_score.py` → 注册新 weight profile
- `scoring/short_term_burst_score.py` → 可选调整权重
- 新建回测调参脚本

---

### Phase D：概念板块完整支持

**问题：** 概念板块（AI、芯片、新能源等）对短线更重要，但当前支持不完整。

**方案：**

1. AkShare `stock_board_concept_cons_em` 获取概念板块成分股
2. 概念板块同样建立映射（覆盖 30+ 高频概念）
3. 概念板块的热度评分加入"概念阶段"（STARTUP → FERMENTATION → ACCELERATION → DIVERGENCE → RETREAT）

**涉及文件：**
- `sector_stock_bridge.py` → 增加概念板块映射
- `scoring/concept_score.py` → 加入概念阶段判断
- `models.py` → `ConceptPhase` 枚举已定义但未使用

---

### Phase E：板块轮动信号升级

**问题：** 当前轮动检测只是简单排名对比。

**方案：**

1. 检测"短线爆发→趋势持续"切换点（最有价值的信号）
2. 检测"趋势持续→冷却"预警信号
3. 加入轮动速度指标（排名变化速度）
4. 输出轮动事件列表（而非仅排名变化）

**涉及文件：**
- `agents/sector_rotation/sector_rotation_agent.py` → 升级轮动逻辑
- `history/rotation_tracker.py` → 增加轮动事件检测

---

### Phase F：接入 ai-hedge-fund 深度确认

**问题：** 纯规则评分无法判断"这个板块为什么强"。

**方案：**

用 ai-hedge-fund 的 5 个 A 股 Agent 做深度确认：

```python
# 对板块 Top N 中的龙头股运行 Agent 分析
from src.agents.china_youzi import china_youzi_agent
from src.agents.northbound_flow import northbound_flow_agent
from src.agents.policy_analyst import policy_analyst_agent
from src.agents.china_sentiment import china_sentiment_agent
from src.agents.industry_rotation import industry_rotation_agent
```

**涉及文件：**
- `unified_pipeline.py` → 增加 Agent 深度确认步骤
- 需要 ai-hedge-fund venv 环境

---

### Phase G：定时任务 + 通知

**问题：** 每天需手动运行。

**方案：**

1. Windows 任务计划程序：每个交易日 15:30 自动运行
2. 输出推送到 Telegram（复用 ai-hedge-fund 的 Telegram bot）
3. 或推送到 Hermes cron job

**涉及文件：**
- `docs/runbooks/windows_task_scheduler.md`（已有文档，未配置）
- 新建 `scripts/run_daily_scheduled.py`

---

## 十三、优先级排序

| 优先级 | Phase | 预估工作量 | 预期效果 |
|--------|-------|-----------|----------|
| **P0** | A：扩展板块映射 | 2~3h | Top10 板块 100% 有成分股 |
| **P0** | B：接入 market_data_service | 3~4h | 数据层统一，代码减半 |
| **P1** | C：优化双评分权重 | 4~6h | 评分准确性提升 |
| **P1** | D：概念板块支持 | 3~4h | 覆盖更多短线热点 |
| **P2** | E：轮动信号升级 | 4~5h | 输出更有价值的轮动信号 |
| **P2** | F：接入 ai-hedge-fund | 5~6h | 深度确认能力 |
| **P3** | G：定时任务 + 通知 | 2~3h | 自动化运行 |

**建议执行顺序：** A → B → D → C → E → F → G

---

## 十四、测试现状

219 个测试，覆盖：

| 类别 | 测试数 | 说明 |
|------|--------|------|
| 评分语义 | ~30 | 双评分等级、权重、边界 |
| Agent 投票/共识 | ~25 | Agent 输出契约、投票聚合 |
| 缓存/回放 | ~20 | 缓存 fallback、replay |
| 报告质量 | ~25 | JSON/Markdown 契约、可读性 |
| CLI 参数 | ~15 | daily/replay/fixture 模式 |
| 轮动追踪 | ~10 | 历史对比、轮动事件 |
| 桥接/联合 | ~23 | 关联度、成分股、联合评分 |
| 回测 | ~15 | Agent 层回测、可靠性 |
| 数据层 | ~20 | AkShare、fixture、数据质量 |
| 其他 | ~36 | Gitignore、runbook、release |

**注意：** 测试必须用完整 CLI 链路跑（`--score-sectors --top-n 100 → --multi-window-consensus → --research-agents`），不能手写简化评分。手写评分的公式与 `sector_composite_score.py` 不同，会导致标签分配错误。

---

## 十五、运行命令速查

```bash
# Fixture Smoke Test（离线测试）
python -m theme_sector_radar.cli \
  --daily --as-of 2026-07-02 \
  --offline-fixture --fixture-profile full \
  --lookback-days 5 --report-root reports/theme_sector_radar

# 真实 AkShare 日报
python -m theme_sector_radar.cli \
  --daily --as-of 2026-07-02 \
  --provider akshare --refresh \
  --lookback-days 5 --report-root reports/theme_sector_radar

# 板块评分（完整链路）
python -m theme_sector_radar.cli \
  --score-sectors --as-of 2026-07-02 --top-n 100

# 板块综合研判
python -m theme_sector_radar.cli \
  --research-agents --as-of 2026-07-02

# 多窗口共识
python -m theme_sector_radar.cli \
  --multi-window-consensus --as-of 2026-07-02

# 板块→个股桥接
python sector_stock_bridge.py --as-of 2026-07-02

# 联合选股
python unified_pipeline.py --as-of 2026-07-02 --mode quick

# 运行全部测试
python -m pytest tests/theme_sector_radar/ -v
```

---

*文档结束。供 Codex 讨论优化方向使用。*
