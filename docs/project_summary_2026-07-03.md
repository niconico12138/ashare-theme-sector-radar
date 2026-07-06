# Theme Sector Radar 项目总结（2026-07-03）

## 1. 项目定位

本项目位于：

E:\Workspace\ai-stock-projects\theme-sector-radar-dev

项目目标是构建一个 A 股行业板块与概念板块的研究型雷达系统，用于盘后复盘、板块强弱观察、趋势评分、短线热度判断、多 Agent 综合研判和后续回测验证。

当前项目已经从最初的行业/概念雷达，扩展为以下能力组合：

- 行业板块日报雷达
- 概念板块日报雷达
- 行业/概念历史数据下载
- 趋势持续评分
- 短线爆发评分
- 多窗口趋势共识
- 分层 Agent 综合研判
- 概念统一加权排名
- Agent 回测与可靠性分析
- Catalyst 外部事件缓存与 report-only 研判
- 市场状态解释层
- 健康检查与日报工作流

本项目输出内容仅用于研究、观察和复盘，不作为交易指令。

## 2. 当前核心目录

`	ext
theme_sector_radar/
  agents/
    sector_scoring/          # 板块评分 Agent
    sector_research/         # 分层综合研判 Agent 组
    multi_window_consensus/  # 5/10/20 日多窗口趋势共识
  backtest/                  # 回测、可靠性、市场状态、机会/反弹分析
  data/
    akshare_provider.py      # AkShare + THS fallback 数据源
    catalyst_events/         # 外部催化事件缓存、映射和下载
    benchmark_provider.py    # 沪深300等市场基准
  downloader/                # 行业/概念历史数据下载
  reports/                   # 报告生成模块
  scoring/                   # 趋势、短线、风险、综合评分公式
  cli.py                     # 统一 CLI 入口

data_cache/
  sector_history/
    industry/                # 行业板块历史数据
    concept/                 # 概念板块历史数据
  benchmarks/                # 市场基准缓存
  catalyst_events/           # 外部事件缓存

reports/
  theme_sector_radar/        # 日报雷达输出
  full90/                    # 90 行业全覆盖输出
  full_concept/              # 概念全覆盖输出
  sector_scores/             # 板块评分输出
  sector_research/           # Agent 研判输出
  backtests/                 # 回测分析输出
  daily_health/              # 每日健康检查
`

## 3. 数据源现状

### 3.1 实时/准实时数据

当前主要使用 AkShare，并带有东方财富 EM 与同花顺 THS 的降级策略。

- 东方财富 EM：在当前环境中经常因为代理、出口 IP 或反爬导致失败。
- 同花顺 THS：当前更稳定，已经用于行业、概念和历史数据补齐。
- 市场基准：使用缓存中的沪深300等指数数据。

### 3.2 历史数据

当前已经支持：

- 行业板块历史数据下载
- 概念板块历史数据下载
- 从 sector_history 回放生成日报
- 使用回放日报做 no-lookahead 回测

最近一次验证：

- 行业板块：90 个行业已全覆盖
- 概念板块：120 个概念已全覆盖
- 历史窗口：2026-05-20 到 2026-07-02
- 20 日趋势窗口覆盖：行业和概念均可正常计算

## 4. 评分体系

### 4.1 趋势持续评分

趋势持续评分用于判断板块是否形成持续趋势。

主要组成：

- 日报雷达分
- 多日动量
- 相对强度
- 持续性
- 最大回撤
- 波动率
- 数据质量
- 风险扣分

当前常用权重：	rend_confirmation

特点：更重视动量、相对强度和持续性，降低单日雷达分权重。

### 4.2 短线爆发评分

短线爆发评分用于判断板块是否处于短期活跃状态。

主要组成：

- 当日雷达强度
- 1 日涨幅
- 3 日动量
- 量能/热度
- 排名变化
- 数据质量
- 短线风险扣分

当前已经修复：

- 历史数据不足时，短线分会被上限约束
- 避免缺历史数据的板块被误判为短线强势

### 4.3 多窗口趋势共识

系统支持 5/10/20 三个窗口。

常见标签：

- multi_window_confirmed：多窗口确认
- short_mid_strong_long_weak：短中期强，长期弱
- short_active_only：短期活跃
- weak_all_windows：多窗口偏弱
- conflicted_windows：窗口分歧
- insufficient_history：历史不足

## 5. Agent 组架构

当前 Agent 组已经升级为分层结构。

### L1 数据与证据层

- EvidenceExtractionAgent
- SignalNormalizationAgent

职责：提取基础证据、统一信号格式。

### L2 专项分析层

- TechnicalTrendAgent：技术趋势
- ShortTermHeatAgent：短线热度
- RotationAnalysisAgent：轮动状态
- CapitalVolumeAgent：资金量能
- RiskControlAgent：风险控制
- DataQualityAgent：数据质量
- MarketContextAgent：市场环境
- NarrativeAgent：叙事信息，低信息权重
- PersistenceStrengthAgent：持续性信号
- CatalystEventAgent：外部催化事件，目前 report-only

### L3 冲突与一致性层

- AgentVoteAggregator：投票聚合
- ConflictDetectionAgent：冲突检测
- VetoRuleAgent：否决规则
- ConfidenceCalibrationAgent：置信度校准

### L4 最终研判层

- ConsensusDecisionAgent

职责：输出最终共识标签、ranking_score、opportunity_score、confidence_score 等。

## 6. 当前重要产物

### 6.1 行业全覆盖结果

最近一次行业全覆盖目录：

eports/full90/

关键输出：

`	ext
reports/full90/sector_consensus/2026-07-02/multi_window_consensus.json
reports/full90/sector_research/2026-07-02/sector_research.json
`

覆盖情况：

- 行业评分：90 条
- 多窗口共识：90 条
- Agent 综合研判：90 条
- 历史不足：0 条

### 6.2 概念全覆盖结果

最近一次概念全覆盖目录：

eports/full_concept/

关键输出：

`	ext
reports/full_concept/sector_scores/2026-07-02/sector_scores.json
reports/full_concept/sector_consensus/2026-07-02/multi_window_consensus.json
reports/full_concept/sector_research/2026-07-02/sector_research.json
reports/full_concept/unified_rank/2026-07-02/concept_unified_rank.json
reports/full_concept/unified_rank/2026-07-02/concept_unified_rank.csv
reports/full_concept/unified_rank/2026-07-02/concept_unified_rank.md
`

覆盖情况：

- 概念评分：120 条
- 5/10/20 窗口评分：每个窗口 120 条
- 多窗口共识：120 条
- Agent 综合研判：120 条
- 历史不足：0 条

## 7. 概念统一加权排名

用户已确认采用 稳健趋势型权重。

公式：

`	ext
综合分 =
趋势持续分 * 0.35
+ 短线爆发分 * 0.20
+ Agent排序分 * 100 * 0.30
+ Agent机会分 * 100 * 0.10
+ 风险可控分 * 100 * 0.05
`

表格字段：

- rank
- sector_name
- concept_final_rank_score
- trend_continuation_score
- trend_level_cn
- short_term_burst_score
- burst_level_cn
- agent_consensus_label
- agent_ranking_score
- agent_opportunity_score
- risk_control_score
- confidence_score
- evidence_score
- history_days
- actual_history_days
- trend_window_status

用户偏好：

- 日常回复只展示 Top 10
- 全量明细保存在本地 CSV/JSON/Markdown 中

## 8. 常用命令

### 8.1 下载行业历史数据

`powershell
python -m theme_sector_radar.cli --download-sector-history 
  --sector-type industry 
  --start-date 2026-05-20 
  --end-date 2026-07-02 
  --top-n 90 
  --refresh
`

### 8.2 下载概念历史数据

`powershell
python -m theme_sector_radar.cli --download-sector-history 
  --sector-type concept 
  --start-date 2026-05-20 
  --end-date 2026-07-02 
  --top-n 120 
  --refresh
`

### 8.3 从历史数据生成行业 replay 日报

`powershell
python -m theme_sector_radar.cli --replay-daily-from-sector-history 
  --start-date 2026-07-02 
  --end-date 2026-07-02 
  --sector-type industry 
  --top-n 90 
  --report-root reports/full90/theme_sector_radar 
  --history-root data_cache/sector_history
`

### 8.4 从历史数据生成概念 replay 日报

`powershell
python -m theme_sector_radar.cli --replay-daily-from-sector-history 
  --start-date 2026-07-02 
  --end-date 2026-07-02 
  --sector-type concept 
  --top-n 120 
  --report-root reports/full_concept/theme_sector_radar 
  --history-root data_cache/sector_history
`

### 8.5 行业全覆盖 Agent 研判

`powershell
python -m theme_sector_radar.cli --research-agents 
  --as-of 2026-07-02 
  --sector-type industry 
  --history-start-date 2026-05-20 
  --history-end-date 2026-07-02 
  --top-n 90 
  --benchmark hs300 
  --trend-weight-profile trend_confirmation 
  --report-root reports/full90/theme_sector_radar/theme_sector_radar 
  --score-output reports/full90/sector_scores
`

### 8.6 概念全覆盖 Agent 研判

`powershell
python -m theme_sector_radar.cli --research-agents 
  --as-of 2026-07-02 
  --sector-type concept 
  --history-start-date 2026-05-20 
  --history-end-date 2026-07-02 
  --top-n 120 
  --benchmark hs300 
  --trend-weight-profile trend_confirmation 
  --report-root reports/full_concept/theme_sector_radar/theme_sector_radar 
  --score-output reports/full_concept/sector_scores
`

## 9. 已知问题和注意点

### 9.1 实时日报可能卡在网络接口

--daily --provider akshare --top-n 90 在当前环境中可能卡住，原因多与东方财富接口、代理或市场概览请求有关。

当前更稳定的做法是：

1. 下载 sector_history
2. 用 sector_history replay 日报
3. 基于 replay 日报做全覆盖评分和 Agent 研判

### 9.2 report_root 容易串目录

如果 eport_root 指错，评分和 Agent 研判可能复用旧的 Top10 报告。

全覆盖运行建议使用独立目录：

- 行业：eports/full90/
- 概念：eports/full_concept/

### 9.3 概念与行业不建议直接混合排名

行业更适合看主线趋势，概念更适合看弹性和题材扩散。

推荐结构：

- 行业独立榜
- 概念独立榜
- 行业 x 概念共振榜

## 10. 后续优化方向

### 10.1 正式化统一排名模块

当前概念统一排名已经生成报告产物，但还没有沉淀成正式 CLI 子命令。

建议新增：

`powershell
python -m theme_sector_radar.cli --unified-rank 
  --sector-type concept 
  --as-of 2026-07-02 
  --profile stable_trend
`

### 10.2 行业 x 概念共振榜

下一步可以把行业和概念连接起来，形成共振观察表。

示例字段：

- 行业名称
- 行业趋势分
- 概念名称
- 概念综合分
- 共振强度
- 共同成分股数量
- 风险提示

### 10.3 概念覆盖扩容

当前概念覆盖 120 个，后续可扩到 THS 全量概念，大约 300+。

注意：概念数量更多，噪音也更大，需要保留分层过滤。

### 10.4 CatalystEventAgent 继续观察

当前 CatalystEventAgent 是 report-only，不参与最终投票和排名。

只有在真实外部事件数据覆盖率、映射率和回测表现稳定后，才考虑进入 selective vote。

### 10.5 回测验证继续扩大

建议继续用最近一个月、两个月、三个月数据做：

- 统一排名 Top10 后续表现
- Agent 标签表现
- 行业/概念共振表现
- 短线分 vs 趋势分分歧表现

## 11. 当前使用约定

- 默认回复只展示 Top 10
- 全量结果保存在 CSV/JSON/Markdown 文件中
- 中文标签优先展示
- 不使用 buy/sell/hold 表述
- 不修改 i-hedge-fund 原项目
- 报告用于研究、观察和复盘

## 12. 当前项目状态

截至 2026-07-03：

- 行业全覆盖链路：可运行
- 概念全覆盖链路：可运行
- 趋势评分：已完成多轮语义修复
- 短线评分：已增加历史不足 cap
- Agent 组：已具备分层结构
- 概念统一排名：已生成报告产物
- 回测框架：已有基础能力
- 实时 AkShare 网络：仍存在环境不稳定问题
- 推荐日常主路径：sector_history replay + 全覆盖评分 + Agent 研判
