# Phase 31: 精选 Agent 默认组与 LLM 调用透明化技术方案

## 1. 背景

当前 `theme-sector-radar-dev` 已经可以把板块分析结果桥接到 `ai-hedge-fund`，由 AIHF 对候选个股进行 Agent 分析。但最近 2026-07-03 的运行暴露出两个问题：

1. `run_meta.llm_enabled=false`，但 `llm_configured=true`、`llm_available=true`。说明 LLM key 和模型可用，但外层 runner 没有把 `--llm-enabled` 透传到底层 AIHF bridge。
2. 默认跑满 24 个 Agent 成本高、耗时长、fallback 多，且部分大师 Agent 对 A 股日常短中线观察的边际价值不高。

因此本阶段不建议默认跑 full 24 Agent，而是新增一个 A 股精选 Agent 组 `selected`，作为日报默认 preset；同时补齐 LLM 开关、Agent 调用审计、fallback 原因和报告展示。

## 2. 目标

Phase 31 的目标是：

- 新增 `selected` preset，默认用于每日 AI 个股报告。
- `selected` 只包含对 A 股日常观察最有价值的 Agent。
- 外层 daily runner 支持并透传 `--llm-enabled`、`--llm-smoke`、`--llm-model`。
- 报告中明确展示 LLM 是否被请求、是否配置、是否可用、是否 smoke 成功、是否真实生效。
- 报告中明确展示每个 Agent 的调用数、成功数、LLM 调研数、规则调研数、fallback 数、失败数和主要 fallback 原因。
- 保留 `core`、`ashare`、`master`、`full`，其中 `full` 只作为深度复核模式，不作为默认日报模式。

## 3. 非目标

本阶段不做以下事情：

- 不强制所有 Agent 都必须调用 LLM。
- 不默认跑满 24 个 Agent。
- 不运行 `portfolio_manager`。
- 不把 `risk_manager` 混入 24 个 analyst。
- 不输出买卖建议。
- 不泄露 API key。
- 不改变 theme-sector-radar 的板块评分逻辑。
- 不改变候选池生成规则：趋势池 15 + 短线池 15，合并去重，过滤 ST / 非主板 / 无效代码。

## 4. 推荐默认 Agent 组

新增 preset：`selected`。

```python
AGENT_PRESETS["selected"] = [
    "technical_analyst",
    "fundamentals_analyst",
    "valuation_analyst",
    "sentiment_analyst",
    "china_youzi",
    "industry_rotation",
    "growth_analyst",
    "northbound_flow",
    "policy_analyst",
    "china_sentiment",
    "news_sentiment_analyst",
]
```

选择理由：

| Agent | 默认纳入原因 |
|---|---|
| `technical_analyst` | 技术面、趋势、动量、均线、波动，是短中线排序核心。 |
| `fundamentals_analyst` | 基本面质量过滤，避免纯题材漂移。 |
| `valuation_analyst` | 估值约束，避免极端高估。 |
| `sentiment_analyst` | 情绪面辅助判断。 |
| `china_youzi` | A 股短线、游资、涨停、量比特征，最贴近短线池。 |
| `industry_rotation` | 与 theme-sector-radar 板块轮动结果最相关。 |
| `growth_analyst` | 成长性补充，适合科技、医药、新能源。 |
| `northbound_flow` | 外资/北向资金偏好，作为趋势确认。 |
| `policy_analyst` | A 股政策驱动重要。 |
| `china_sentiment` | 本土市场情绪/题材语义。 |
| `news_sentiment_analyst` | 新闻情绪补充，数据可用时提供额外信息。 |

## 5. 不默认纳入的 Agent

以下 Agent 保留在 `master` 或 `full`，不进入默认 `selected`：

| Agent | 不默认原因 |
|---|---|
| `warren_buffett` | 长期护城河框架，与日报短中线观察弱相关。 |
| `charlie_munger` | 与 Buffett 高重叠。 |
| `ben_graham` | 深度价值框架，对 A 股短线池解释力弱。 |
| `mohnish_pabrai` | 与 Graham/Buffett 重叠。 |
| `phil_fisher` | 成长股有参考价值，但与 `growth_analyst` 重叠。 |
| `peter_lynch` | 适合深度复核，不适合默认日报。 |
| `cathie_wood` | 创新成长风格波动大，适合专题复核。 |
| `aswath_damodaran` | 估值大师，但默认已有 `valuation_analyst`。 |
| `michael_burry` | 偏风险/逆向，适合深度复核。 |
| `nassim_taleb` | 偏尾部风险，不适合作为默认排序主因子。 |
| `bill_ackman` | 激进基本面/事件驱动，A 股适配一般。 |
| `rakesh_jhunjhunwala` | 风格参考价值有，但默认优先级不高。 |
| `stanley_druckenmiller` | 趋势宏观风格可选，但先不纳入默认组，避免 selected 过重。 |

## 6. selected 权重建议

新增 `SELECTED_WEIGHTS`：

```python
SELECTED_WEIGHTS = {
    "technical_analyst": 0.18,
    "china_youzi": 0.16,
    "industry_rotation": 0.14,
    "fundamentals_analyst": 0.12,
    "valuation_analyst": 0.10,
    "sentiment_analyst": 0.09,
    "china_sentiment": 0.08,
    "policy_analyst": 0.06,
    "northbound_flow": 0.04,
    "growth_analyst": 0.02,
    "news_sentiment_analyst": 0.01,
}
```

权重逻辑：

- 技术 + 游资 + 板块轮动是 A 股短中线主线。
- 基本面 + 估值作为质量约束。
- 情绪 + 政策 + 北向作为辅助确认。
- 成长/新闻作为小权重增强。

权重只在 Agent 有效时参与归一化。fallback 或 error Agent 不参与有效权重。

## 7. 技术路线

### 7.1 AIHF bridge 层

修改文件：

- `E:\liaohua\01_projects\ai-hedge-fund\scripts\run_stock_agent_bridge.py`

改动：

1. 在 `AGENT_PRESETS` 中新增 `selected`。
2. CLI `--agent-preset` choices 增加 `selected`。
3. 新增 `SELECTED_WEIGHTS`。
4. `_get_agent_weight(agent_id, preset)` 支持 `selected`。
5. run_meta 增加 `llm_status`：

```json
"llm_status": {
  "requested": true,
  "configured": true,
  "available": true,
  "smoke_status": "ok",
  "effective": true,
  "model": "mimo-v2.5-pro",
  "provider": "OPENAI",
  "base_url_present": true
}
```

6. run_meta 增加 `agent_execution`：

```json
"agent_execution": {
  "requested_agents": [],
  "agent_count": 11,
  "effective_agents": [],
  "fallback_agents": [],
  "failed_agents": [],
  "per_agent_status": {
    "technical_analyst": {
      "called": 15,
      "succeeded": 13,
      "llm_used": 0,
      "rule_based_used": 13,
      "fallback": 2,
      "failed": 0,
      "top_fallback_reason": "data_insufficient"
    }
  }
}
```

7. 保留旧字段 `llm_enabled`、`per_agent_status`、`succeeded_agents`、`fallback_agents`，避免破坏旧报告和测试。

### 7.2 theme bridge 层

修改文件：

- `E:\liaohua\01_projects\theme-sector-radar-dev\scripts\run_daily_bridge_report.py`

改动：

1. CLI `--agent-preset` choices 增加 `selected`。
2. 新增参数：
   - `--llm-enabled`
   - `--llm-smoke`
   - `--llm-model`
3. 调用 AIHF bridge 时透传：
   - `--llm-enabled`
   - `--llm-smoke`
   - `--llm-model <value>`
4. `data_sources` 中不要硬编码 `llm_enabled=True`，改为读取 ranking 的 run_meta。
5. Markdown 增加 Agent 调研状态小节。

### 7.3 daily runner 层

修改文件：

- `E:\liaohua\01_projects\theme-sector-radar-dev\scripts\run_daily_ai_stock_report.py`

改动：

1. 默认 `--agent-preset` 从 `core` 改为 `selected`。
2. CLI choices 增加 `selected`。
3. 新增参数：
   - `--llm-enabled`
   - `--llm-smoke`
   - `--llm-model`，默认空，由 AIHF bridge 兜底到 env 或 `mimo-v2.5-pro`。
4. 调用 `run_daily_bridge_report.py` 时透传以上参数。
5. JSON 输出中的 `stock_agent_summary.run_meta` 保留完整 run_meta。
6. Markdown 中显示：
   - LLM requested/configured/available/effective
   - Agent count/effective/fallback/failed
   - 每个 Agent 的 called/succeeded/llm_used/rule_based_used/fallback/failed

## 8. Agent 状态分类标准

每个 Agent 每只股票的执行结果应归入以下状态之一：

| 状态 | 含义 |
|---|---|
| `ok_llm` | Agent 成功，并实际调用 LLM。 |
| `ok_rule_based` | Agent 成功，但使用规则逻辑。 |
| `fallback_data_insufficient` | 数据不足，无法形成有效分析。 |
| `fallback_llm_unavailable` | LLM 不可用，且没有有效规则兜底。 |
| `error` | 代码异常。 |

如果短期内无法准确识别 `ok_llm`，可以先通过 `data_sources` 或 `reasoning` 中是否包含 LLM 标记做保守统计；识别不到时不要假装调用了 LLM，应计入 `rule_based_used` 或 `unknown_execution_mode`。

## 9. 报告模板要求

日报 Markdown 应新增：

```markdown
## Agent 调研状态

| Agent | 调用股票数 | 成功 | LLM调研 | 规则调研 | Fallback | 失败 | 主要原因 |
|---|---:|---:|---:|---:|---:|---:|---|
| technical_analyst | 15 | 13 | 0 | 13 | 2 | 0 | data_insufficient |
| china_youzi | 15 | 15 | 0 | 15 | 0 | 0 | - |
```

个股明细中增加：

```markdown
主要支持 Agent:
- china_youzi: buy, confidence=0.375, reason=5日涨幅/量比/涨停

主要反对 Agent:
- 无

Fallback Agent:
- industry_rotation: data_insufficient
- growth_analyst: financial_history_insufficient
```

## 10. 默认运行命令

日常日报：

```powershell
cd E:\liaohua\01_projects\theme-sector-radar-dev
python scripts/run_daily_ai_stock_report.py --as-of 2026-07-03 --agent-preset selected --agent-mode real --llm-enabled --llm-smoke --refresh-cache
```

深度复核：

```powershell
cd E:\liaohua\01_projects\theme-sector-radar-dev
python scripts/run_daily_ai_stock_report.py --as-of 2026-07-03 --agent-preset full --agent-mode real --llm-enabled --llm-smoke --full-limit 5 --refresh-cache
```

列出 Agent：

```powershell
cd E:\liaohua\01_projects\ai-hedge-fund
python scripts/run_stock_agent_bridge.py --list-agents
```

## 11. 检验标准

### 11.1 单元测试

必须通过：

```powershell
cd E:\liaohua\01_projects\theme-sector-radar-dev
python -m pytest tests/theme_sector_radar/ -q
```

预期：

- 不新增失败。
- 已有 skipped 集成测试可继续 skipped。

如果 AIHF 项目有测试，也运行：

```powershell
cd E:\liaohua\01_projects\ai-hedge-fund
python -m pytest tests -q
```

若 AIHF 没有稳定测试集，至少运行 selected/full smoke。

### 11.2 selected smoke

运行：

```powershell
cd E:\liaohua\01_projects\theme-sector-radar-dev
python scripts/run_daily_ai_stock_report.py --as-of 2026-07-03 --agent-preset selected --agent-mode real --llm-enabled --llm-smoke --refresh-cache
```

必须满足：

| 检查项 | 通过标准 |
|---|---|
| exit code | 0 |
| preset | selected |
| agent_count | 11 |
| requested_agents | 与 selected 列表一致 |
| `llm_status.requested` | true |
| `llm_status.configured` | true |
| `llm_status.available` | true |
| `llm_status.model` | `mimo-v2.5-pro` 或显式传入模型 |
| `llm_status.effective` | smoke ok 时为 true |
| ranking_top10 | 非空 |
| trend_score/burst_score | 不应全部为 0 |
| non-main-board | 不应出现在候选池 |
| ST | 不应出现在候选池 |
| API key | 不应出现在 JSON/Markdown/终端输出 |

### 11.3 full smoke

运行：

```powershell
cd E:\liaohua\01_projects\theme-sector-radar-dev
python scripts/run_daily_ai_stock_report.py --as-of 2026-07-03 --agent-preset full --agent-mode real --llm-enabled --llm-smoke --full-limit 5 --refresh-cache
```

必须满足：

| 检查项 | 通过标准 |
|---|---|
| exit code | 0 |
| preset | full |
| agent_count | 24 |
| requested_agents | 24 个 analyst |
| `risk_manager` | 不运行 |
| `portfolio_manager` | 不运行 |
| per_agent_status | 24 个 Agent 都有状态 |
| failed_agents | 允许少量，但必须记录原因 |
| fallback_agents | 必须记录主要原因 |

### 11.4 报告验收

检查文件：

- `reports/daily_ai_stock_report/2026-07-03/daily_ai_stock_report.json`
- `reports/daily_ai_stock_report/2026-07-03/daily_ai_stock_report.md`
- `reports/agent_bridge/2026-07-03/aihf_stock_ranking.json`

必须包含：

- 行业 Top10。
- 概念 Top10。
- 个股 Agent Top10。
- 每只股票的趋势分、短线分、Agent 分、风险调整分。
- Agent 调研状态表。
- LLM 状态表。
- fallback 原因。
- 免责声明。

## 12. 回归风险

| 风险 | 缓解 |
|---|---|
| selected 默认改变报告排序 | 文档说明 selected 是新的默认；保留 core/full 手动可选。 |
| LLM smoke 增加运行时间 | `--llm-smoke` 只做一次短调用，不对每只股票重复。 |
| Agent 状态识别不准 | 先保守统计，识别不到不标记为 LLM 调研。 |
| full 模式耗时长 | full 保留为深度模式，可用 `--full-limit` 限制。 |
| 旧测试依赖 choices | 更新测试中的 allowed choices。 |

## 13. ClaudeCode 执行提示词

请在 ClaudeCode 中粘贴以下提示词：

```text
你现在要在两个项目中实现 Phase 31：精选 Agent 默认组与 LLM 调用透明化。

项目路径：
- theme-sector-radar-dev: E:\liaohua\01_projects\theme-sector-radar-dev
- ai-hedge-fund: E:\liaohua\01_projects\ai-hedge-fund

请先阅读技术文档：
E:\liaohua\01_projects\theme-sector-radar-dev\docs\phase31_selected_agents_llm_transparency_plan.md

目标：
1. 在 ai-hedge-fund/scripts/run_stock_agent_bridge.py 新增 selected preset，包含 11 个 Agent：
   technical_analyst, fundamentals_analyst, valuation_analyst, sentiment_analyst,
   china_youzi, industry_rotation, growth_analyst, northbound_flow,
   policy_analyst, china_sentiment, news_sentiment_analyst。
2. selected preset 使用 SELECTED_WEIGHTS：
   technical=0.18, china_youzi=0.16, industry_rotation=0.14,
   fundamentals=0.12, valuation=0.10, sentiment=0.09,
   china_sentiment=0.08, policy=0.06, northbound=0.04,
   growth=0.02, news_sentiment=0.01。
3. run_stock_agent_bridge.py 的 --agent-preset choices 支持 selected。
4. run_daily_bridge_report.py 和 run_daily_ai_stock_report.py 支持并透传：
   --llm-enabled, --llm-smoke, --llm-model。
5. run_daily_ai_stock_report.py 默认 agent-preset 从 core 改为 selected。
6. run_meta 新增 llm_status 和 agent_execution；保留旧字段，避免破坏兼容。
7. Markdown 报告增加 Agent 调研状态和 LLM 状态；个股明细中显示主要支持/反对/fallback Agent。
8. 不运行 portfolio_manager；risk_manager 不混入 24 analyst。
9. 不泄露 API key，不输出买卖建议。
10. 不改变候选池逻辑：趋势池15 + 短线池15，合并去重，过滤 ST/非主板/无效代码。

请按测试驱动方式工作：
- 先补测试或最小 smoke 验证。
- 再改实现。
- 最后跑验收命令。

验收命令：
cd E:\liaohua\01_projects\theme-sector-radar-dev
python -m pytest tests/theme_sector_radar/ -q
python scripts/run_daily_ai_stock_report.py --as-of 2026-07-03 --agent-preset selected --agent-mode real --llm-enabled --llm-smoke --refresh-cache
python scripts/run_daily_ai_stock_report.py --as-of 2026-07-03 --agent-preset full --agent-mode real --llm-enabled --llm-smoke --full-limit 5 --refresh-cache

cd E:\liaohua\01_projects\ai-hedge-fund
python scripts/run_stock_agent_bridge.py --list-agents

验收标准：
- selected agent_count=11。
- full agent_count=24。
- selected/full 的 requested_agents 与 preset 完全一致。
- llm_status.requested=true。
- llm_status.configured=true。
- llm_status.available=true。
- llm_status.effective 在 smoke ok 时为 true。
- per_agent_status 或 agent_execution 中每个 Agent 都有 called/succeeded/llm_used/rule_based_used/fallback/failed。
- 报告中有行业Top10、概念Top10、个股Agent Top10、趋势分、短线分、Agent分、风险调整分、Agent调研状态、LLM状态、fallback原因。
- 不泄露 API key。
- 不新增测试失败。

完成后请输出：
1. 修改文件清单。
2. selected/full smoke 摘要。
3. 测试结果。
4. 仍然 fallback 的 Agent 及原因。
5. 生成的 JSON/Markdown 报告路径。
```
