# Phase 1 MVP Implementation Plan

## 目录结构

```
theme-sector-radar-dev/
├── README.md
├── requirements.txt
├── setup.py
├── docs/
│   ├── intake/
│   │   └── theme_sector_radar_design_summary.md
│   └── plans/
│       └── phase1_mvp_implementation_plan.md
├── theme_sector_radar/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── pipeline.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── providers.py
│   │   ├── cache.py
│   │   ├── snapshots.py
│   │   ├── fixture_provider.py
│   │   └── akshare_provider.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── data/
│   │   │   ├── __init__.py
│   │   │   ├── sector_data_agent.py
│   │   │   ├── sector_normalizer_agent.py
│   │   │   ├── constituent_coverage_agent.py
│   │   │   └── data_reliability_agent.py
│   │   ├── positive_scoring/
│   │   │   ├── __init__.py
│   │   │   ├── market_temperature_agent.py
│   │   │   ├── industry_flow_agent.py
│   │   │   ├── concept_heat_agent.py
│   │   │   └── concept_phase_agent.py
│   │   ├── defense_risk/
│   │   │   ├── __init__.py
│   │   │   ├── sector_risk_agent.py
│   │   │   ├── sector_overheat_agent.py
│   │   │   ├── sector_divergence_agent.py
│   │   │   └── sector_avoidance_agent.py
│   │   └── ranking_report/
│   │       ├── __init__.py
│   │       ├── industry_concept_overlap_agent.py
│   │       ├── sector_ranking_agent.py
│   │       └── sector_report_agent.py
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── industry_score.py
│   │   ├── concept_score.py
│   │   ├── risk_score.py
│   │   └── focus_level.py
│   └── reports/
│       ├── __init__.py
│       ├── json_report.py
│       └── markdown_report.py
├── tests/
│   └── theme_sector_radar/
│       ├── __init__.py
│       ├── test_models.py
│       ├── test_normalizer.py
│       ├── test_industry_score.py
│       ├── test_concept_score.py
│       ├── test_risk_score.py
│       ├── test_overlap.py
│       ├── test_ranking.py
│       ├── test_report_contract.py
│       └── test_cli_offline_fixture.py
└── reports/
    └── theme_sector_radar/
```

## 模块职责

### 核心模块
- **cli.py**: 命令行入口，解析参数，协调 pipeline
- **config.py**: 配置管理，Top N 默认值，阈值参数
- **models.py**: Pydantic 数据模型定义
- **pipeline.py**: 主流程编排，串联各 Agent

### data 模块
- **providers.py**: 数据提供者抽象接口
- **fixture_provider.py**: 离线 fixture 数据提供者
- **akshare_provider.py**: AkShare 真实数据提供者
- **cache.py**: 数据缓存管理
- **snapshots.py**: 快照数据处理

### agents 模块
- **data 组**: 数据拉取、标准化、覆盖率、可靠性评估
- **positive_scoring 组**: 市场温度、行业流向、概念热度、概念阶段
- **defense_risk 组**: 风险识别、过热检测、分歧检测、降级解释
- **ranking_report 组**: 共振检测、排名生成、报告输出

### scoring 模块
- **industry_score.py**: 行业板块评分逻辑 (100分)
- **concept_score.py**: 概念板块评分逻辑 (100分)
- **risk_score.py**: 风险扣分逻辑
- **focus_level.py**: 关注等级计算

### reports 模块
- **json_report.py**: JSON 报告生成
- **markdown_report.py**: Markdown 报告生成

## 数据模型

### RadarContext
```python
class RadarContext:
    as_of_date: str
    config: dict
    raw_data: dict
    normalized_data: dict
    agent_outputs: dict
    warnings: List[str]
    data_sources: List[str]
    updated_at: str
    data_quality_score: float
```

### AgentOutput
```python
class AgentOutput:
    agent_id: str
    status: str  # ok | degraded | failed
    data: dict
    warnings: List[str]
    data_sources: List[str]
    updated_at: str
    data_quality_score: float
```

### SectorSnapshot
```python
class SectorSnapshot:
    sector_id: str
    name: str
    type: str  # industry | concept
    price_change_pct: float
    turnover: float
    main_net_inflow: float
    constituents: List[ConstituentSnapshot]
    data_sources: List[str]
    updated_at: str
    data_quality_score: float
```

### ConstituentSnapshot
```python
class ConstituentSnapshot:
    code: str
    name: str
    change_pct: float
    turnover: float
    is_core: bool
```

### SectorScore
```python
class SectorScore:
    sector_id: str
    name: str
    type: str
    score: float
    positive_score: float
    risk_penalty: float
    focus_level: str
    phase: str
    risk_level: str
    risk_flags: List[str]
    reasons: List[str]
    downgrade_reasons: List[str]
```

### ResonanceResult
```python
class ResonanceResult:
    industry: str
    concept: str
    resonance_score: float
    overlap_constituent_count: int
    common_core_count: int
    flow_alignment: str
    both_top_n: bool
    focus_level: str
    constituents: List[ConstituentSnapshot]
```

### RadarReport
```python
class RadarReport:
    report_type: str
    version: str
    as_of_date: str
    updated_at: str
    data_sources: List[str]
    data_quality_score: float
    market_temperature: dict
    industry_top: List[SectorScore]
    concept_top: List[SectorScore]
    overlap: List[ResonanceResult]
    risk_summary: dict
    data_quality: dict
    disclaimer: str
```

## 离线 Fixture 设计

### fixture_provider.py
提供本地 JSON 测试数据，模拟 AkShare 返回格式:
- industry_sectors.json: 行业板块列表
- concept_sectors.json: 概念板块列表
- sector_flows.json: 资金流向
- constituents.json: 成分股数据
- market_overview.json: 市场概览

### 数据特征
- 固定日期: 2026-06-28
- 包含正常数据和边界情况
- 覆盖各种风险场景

## Scoring 设计

### 行业板块评分 (100分)
- 趋势强度: 25分
- 资金流: 25分
- 板块宽度: 20分
- 持续性: 15分
- 市场适配: 10分
- 数据质量: 5分

### 概念板块评分 (100分)
- 热度爆发: 25分
- 资金确认: 20分
- 成分股联动: 20分
- 阶段判断: 20分
- 催化剂: 10分
- 数据质量: 5分

### 风险扣分 risk_penalty
- 过热检测: -5 ~ -20分
- 分歧检测: -5 ~ -15分
- 数据质量降级: -5 ~ -10分
- 风险等级 high 时强制 core_only

### 关注等级 focus_level
```python
raw_score = positive_score - risk_penalty

if raw_score >= 80 and risk_level != "high":
    focus_level = "focus"
elif 65 <= raw_score < 80:
    focus_level = "watch"
elif positive_score >= 80 and risk_level == "high":
    focus_level = "core_only"
elif 45 <= raw_score < 65:
    focus_level = "caution"
else:
    focus_level = "avoid"
```

## Risk 设计

### 过热检测 (sector_overheat_agent)
- 短期涨幅过大
- 乖离率过高
- 成交额异常放大
- 连续高排名但风险累积

### 分歧检测 (sector_divergence_agent)
- 板块指数上涨但上涨家数不足
- 少数核心股硬拉
- 资金流与价格背离
- 放量滞涨

### 数据质量降级 (data_reliability_agent)
- 数据源数量不足
- 更新时间过期
- 字段完整度低
- 成分股覆盖率低

## Overlap 共振逻辑

### 共振评分 (resonance_score)
```python
resonance_score = (
    constituent_overlap_score * 0.3 +
    dual_top_n_score * 0.25 +
    flow_alignment_score * 0.25 +
    common_core_count_score * 0.2
)
```

### 共振证据
1. 成分股重合: 行业与概念成分股交集比例
2. 双强确认: 行业和概念同时进入 Top N
3. 资金流一致: 行业与概念主力净流入方向一致
4. 共同核心成分股数量: 交集里高贡献成分股数量

## JSON/Markdown 报告契约

### JSON 报告必含字段
- report_type: "theme_sector_radar"
- version: "0.1.0"
- as_of_date: 分析日期
- updated_at: 更新时间
- data_sources: 数据来源列表
- data_quality_score: 数据质量分
- market_temperature: 市场温度
- industry_top: 行业 Top N
- concept_top: 概念 Top N
- overlap: 共振列表
- risk_summary: 风险摘要
- data_quality: 数据质量详情
- disclaimer: 声明

### Markdown 报告必含内容
- 市场短线温度
- 行业 Top N 表格
- 概念 Top N 表格
- 行业+概念共振表格
- 高分板块成分股
- 风险提示
- 数据质量
- 声明: "本报告仅用于板块强弱筛选和研究复盘，不构成个股推荐、买卖建议或自动交易指令"

## CLI 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| --as-of | 当前日期 | 分析日期 |
| --top-n | 10 | Top N 数量 |
| --output | reports/theme_sector_radar/{date} | 输出目录 |
| --use-cache | False | 优先使用缓存 |
| --refresh | False | 强制刷新数据 |
| --offline-fixture | False | 使用离线 fixture |

## 测试清单

1. test_models.py: 模型契约测试
2. test_normalizer.py: 标准化测试
3. test_industry_score.py: 行业评分测试
4. test_concept_score.py: 概念评分测试
5. test_risk_score.py: 风险评分测试
6. test_overlap.py: 共振逻辑测试
7. test_ranking.py: 排名逻辑测试
8. test_report_contract.py: 报告契约测试
9. test_cli_offline_fixture.py: CLI 离线测试

### 关键负面测试
- 数据质量低时不能输出 focus
- 高强度但高风险时输出 core_only
- JSON 中不得出现 buy/sell/hold
- Markdown 必须包含声明

## 验收命令

```bash
# 运行测试
python -m pytest tests/theme_sector_radar/ -v

# 运行 CLI
python -m theme_sector_radar.cli --as-of 2026-06-28 --top-n 10 --output reports/theme_sector_radar/2026-06-28 --offline-fixture

# 验证输出文件
ls reports/theme_sector_radar/2026-06-28/
```
