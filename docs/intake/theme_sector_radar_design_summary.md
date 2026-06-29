# Theme Sector Radar 设计摘要

## 项目目标

A 股短线行业板块与概念板块雷达，服务于盘后复盘与次日观察池构建，关注热点、题材轮动、资金流和板块共振。

## 明确边界

### 第一阶段必须做
- 独立 CLI 运行
- 拉取行业/概念板块数据
- 计算市场短线温度
- 行业 Top N、概念 Top N 评分
- 过热/分歧/数据可靠性风险识别
- 行业+概念共振检测
- JSON + Markdown 报告输出

### 第一阶段禁止做
- 不接入 LangGraph 主工作流
- 不修改 ai-hedge-fund 原项目任何文件
- 不输出个股推荐
- 不输出 buy/sell/hold 建议
- 不接入自动交易
- 不做盘中实时判断

## MVP 范围

1. 独立包结构 theme_sector_radar
2. 离线 fixture 数据支持
3. 行业板块评分 (100分)
4. 概念板块评分 (100分)
5. 风险扣分 risk_penalty
6. 关注等级 focus_level
7. 共振逻辑 resonance_score
8. JSON/Markdown 报告输出

## 暂缓范围

- 主 LangGraph 接入
- 个股推荐
- 自动交易
- 盘中实时判断
- 新闻催化剂自动评分
- LLM 解释

## 数据契约

### 核心数据模型
- RadarContext: 运行上下文
- AgentOutput: Agent 输出
- SectorSnapshot: 板块快照
- ConstituentSnapshot: 成分股快照
- SectorScore: 板块评分
- ResonanceResult: 共振结果
- RadarReport: 最终报告

### 数据质量要求
每层关键输出必须保留:
- data_sources: 数据来源
- updated_at: 更新时间
- data_quality_score: 数据质量分
- warnings: 警告信息

## CLI 设计

```bash
python -m theme_sector_radar.cli \
  --as-of 2026-06-28 \
  --top-n 10 \
  --output reports/theme_sector_radar/2026-06-28 \
  --offline-fixture
```

参数:
- --as-of: 分析日期
- --top-n: Top N 数量
- --output: 报告输出目录
- --offline-fixture: 使用本地 fixture 数据

## 测试要求

1. 默认 pytest 不依赖网络
2. 网络测试标记为 @pytest.mark.network
3. 关键负面测试必须覆盖:
   - 数据质量低时不能输出 focus
   - 高强度但高风险时输出 core_only
   - JSON 中不得出现 buy/sell/hold 个股建议
   - Markdown 中必须包含"不构成个股推荐、买卖建议或自动交易指令"

## 禁止事项

1. 不允许输出个股推荐
2. 不允许输出 buy/sell/hold
3. 不允许输出买入、卖出、持有建议
4. 不允许接入自动交易
5. 不允许盘中实时交易判断
6. 不允许修改 ai-hedge-fund 原项目文件
7. 不允许把 theme_sector_radar 注册进主 LangGraph 工作流
