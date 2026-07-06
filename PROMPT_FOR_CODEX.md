# 板块雷达 × 个股选股 联合系统 — 开发指令

> 本文档供 Codex/Codrx 指挥 Hermes Agent 执行开发任务使用。

---

## 一、项目背景

### 1.1 Theme Sector Radar（板块雷达）

**路径**: `E:\Workspace\ai-stock-projects\theme-sector-radar-dev`

独立 CLI 盘后板块分析系统，纯规则评分，不依赖 LLM。

**核心能力**:
- 从东方财富/同花顺获取 A 股行业板块和概念板块数据
- 双评分体系：趋势持续分（判断板块是否已形成持续趋势）+ 短线爆发分（判断板块是否正在短线爆发）
- 7 个分析 Agent 投票（技术趋势、短线热度、轮动分析、风险控制、数据质量、市场环境、叙事）
- 多窗口趋势共识（5/10/20 日窗口交叉验证）
- 输出：板块 Top N + 共识标签 + 研判日报（JSON + Markdown）

**关键输出文件**:
```
reports/sector_scores/{YYYY-MM-DD}/sector_scores.json   # 板块双评分
reports/sector_research/{YYYY-MM-DD}/sector_research.json  # 综合研判
reports/theme_sector_radar/{YYYY-MM-DD}/theme_sector_radar.json  # 原始雷达
```

**数据模型** (theme_sector_radar/models.py):
- `SectorScore`: 板块评分（score, positive_score, risk_penalty, focus_level, phase）
- `ResonanceResult`: 行业-概念共振
- `MarketTemperature`: 市场温度（涨跌家数/涨跌停）

**CLI 入口**: `python -m theme_sector_radar.cli`
- `--score-sectors` 板块综合评分
- `--research-agents` 板块综合研判
- `--daily` 日报模式

### 1.2 ai-hedge-fund smart_screener（个股选股）

**路径**: `E:\Workspace\ai-stock-projects\ai-hedge-fund`

基于 ai-hedge-fund 多 Agent 架构的 A 股智能选股系统。

**三阶段流水线**:
```
Phase 1: Qlib Alpha158 + LightGBM 全市场量化打分 → Top50
Phase 2: 信号检测器过滤 → B级以上（置信度≥65）+ MA20趋势过滤
Phase 3: 5个A股Agent深度确认（游资/北向/政策/情绪/轮动）
```

**关键文件**:
- `smart_screener.py` — 主入口，串联三阶段
- `src/data/ashare_adapter.py` — A 股数据适配器（三大报表合并）
- `src/agents/china_youzi.py` — 游资分析师
- `src/agents/northbound_flow.py` — 北向资金
- `src/agents/policy_analyst.py` — 政策面
- `src/agents/china_sentiment.py` — 市场情绪
- `src/agents/industry_rotation.py` — 行业轮动

**数据源**:
- Qlib 本地数据: `~/.qlib/qlib_data/cn_data`（3093只A股）
- 实时行情: 腾讯 API `qt.gtimg.cn`（绕过 Clash 代理）
- LLM: MiMo v2.5 Pro（`api.xiaomimimo.com`）

**CLI 入口**: `python smart_screener.py`
- `--quick` 快速模式（Phase1+2，<1分钟，0成本）
- `--deep` 深度模式（Phase1+2+3，~10分钟，消耗LLM）
- `--confirm 600519` 单股确认

---

## 二、联合系统架构

### 2.1 设计目标

将板块雷达的 Top-Down 板块筛选与个股选股的 Bottom-Up 量化打分结合，实现：
- 先选赛道（热门板块）再选马（板块内优质个股）
- 板块关联度作为个股评分的加权因子
- 资金流对齐验证真实关联

### 2.2 架构图

```
┌─────────────────────────────────────────────────────┐
│                  unified_pipeline.py                  │
│                  （新增，联合调度入口）                  │
├─────────────────────────────────────────────────────┤
│                                                       │
│  Step 1: Theme Sector Radar 日报                      │
│  ┌───────────────────────────────────────────────┐   │
│  │ theme_sector_radar CLI                        │   │
│  │  → 趋势 Top 5 板块                             │   │
│  │  → 短线 Top 5 板块                             │   │
│  │  → 板块评分 + 资金流方向                        │   │
│  └───────────────────────────────────────────────┘   │
│                        ↓                              │
│  Step 2: 板块→成分股查询 + 关联度计算                  │
│  ┌───────────────────────────────────────────────┐   │
│  │ sector_stock_bridge.py（新增）                  │   │
│  │  → AkShare 查询板块成分股（权重+代码）           │   │
│  │  → 腾讯API 获取成分股实时行情                    │   │
│  │  → 东方财富获取板块/个股资金流                    │   │
│  │  → 计算板块关联度                               │   │
│  └───────────────────────────────────────────────┘   │
│                        ↓                              │
│  Step 3: 个股量化评分（增强版）                        │
│  ┌───────────────────────────────────────────────┐   │
│  │ smart_screener Phase1（改造）                   │   │
│  │  → Qlib打分 OR 多因子打分                       │   │
│  │  → 加入板块关联度权重                            │   │
│  │  → 总分 = 量化分×0.6 + 板块关联度×0.4           │   │
│  │  → 仅保留高关联度个股（>=0.6）                   │   │
│  └───────────────────────────────────────────────┘   │
│                        ↓                              │
│  Step 4: 输出                                        │
│  ┌───────────────────────────────────────────────┐   │
│  │  → 趋势板块 Top10 个股（带板块标签+关联度）      │   │
│  │  → 短线板块 Top10 个股（带板块标签+关联度）      │   │
│  │  → JSON + Markdown 报告                        │   │
│  └───────────────────────────────────────────────┘   │
│                                                       │
└─────────────────────────────────────────────────────┘
```

### 2.3 板块关联度计算公式

```python
板块关联度 = w1 × 成分股权重分 + w2 × 涨幅排名分 + w3 × 资金流对齐分

建议权重: w1=0.2, w2=0.4, w3=0.4
```

**成分股权重分**: 该股在板块中的权重百分比（东方财富提供），归一化到 0~1

**涨幅排名分**: 该股在板块成分股中的涨幅排名百分位，归一化到 0~1
- 排名前 10% → 1.0
- 排名后 10% → 0.0

**资金流对齐系数**:
```
板块净流入 + 个股净流入  → 1.2（双重正向，加强）
板块净流入 + 个股净流出  → 0.3（方向背离，大幅削弱）
板块净流出 + 个股净流入  → 0.5（个股逆势拉升，谨慎）
板块净流出 + 个股净流出  → 0.8（同步撤退，关联但负面）
```
归一化到 0~1：系数 / 1.2

---

## 三、开发任务清单

### P0 — 核心桥接（先做这个）

#### Task 1: 创建 `sector_stock_bridge.py`

**位置**: `E:\Workspace\ai-stock-projects\theme-sector-radar-dev\sector_stock_bridge.py`

**功能**:
1. 读取 theme-sector-radar 最新报告，提取趋势/短线 Top5 板块
2. 调用 AkShare 查询每个板块的成分股（`ak.stock_board_industry_cons_em(symbol="板块名")`）
3. 调用腾讯 API 获取成分股实时行情（涨跌幅、成交额）
4. 调用东方财富获取板块资金流 + 个股主力资金流
5. 计算每只成分股的板块关联度（三维度加权）
6. 过滤高关联度个股（关联度 >= 0.6）
7. 返回结构化数据供下游使用

**输出格式**:
```python
{
    "as_of_date": "2026-07-01",
    "trend_sectors": [
        {
            "sector_name": "证券",
            "trend_score": 40.4,
            "burst_score": 34.4,
            "fund_flow_direction": "inflow",  # inflow/outflow/neutral
            "stocks": [
                {
                    "code": "600030",
                    "name": "中信证券",
                    "sector_weight": 0.15,      # 在板块中的权重
                    "change_pct": 2.3,           # 当日涨幅
                    "rank_in_sector": 1,         # 板块内涨幅排名
                    "individual_fund_flow": 50000000,  # 个股主力净流入
                    "sector_fund_flow": 800000000,     # 板块主力净流入
                    "relevance_score": 0.87,     # 板块关联度
                    "relevance_breakdown": {
                        "weight_score": 0.15,
                        "rank_score": 1.0,
                        "flow_alignment": 1.0    # 1.2/1.2 = 1.0
                    }
                },
                ...
            ]
        },
        ...
    ],
    "burst_sectors": [ ... ],  # 同结构
    "cross_sectors": [ ... ]   # 同时出现在两个列表的板块
}
```

**注意事项**:
- AkShare 的 `stock_board_industry_cons_em` 接口可能被 Clash 代理拦截，需要在调用前清除代理环境变量（参考 smart_screener.py 开头的做法）
- 腾讯 API `qt.gtimg.cn` 已验证可用，用于获取实时行情
- 东方财富资金流 API（`push2.eastmoney.com`）被 Clash 拦截，需要降级方案：
  - 降级方案1: 新浪财经资金流 API
  - 降级方案2: 用涨幅排名近似代替资金流对齐（关联度公式中 flow_alignment 设为 1.0）
- 板块成分股列表需要缓存，避免重复请求（参考 `data_cache/` 目录结构）

#### Task 2: 创建 `unified_pipeline.py`

**位置**: `E:\Workspace\ai-stock-projects\theme-sector-radar-dev\unified_pipeline.py`

**功能**:
1. 调用 theme_sector_radar CLI 生成板块报告
2. 调用 sector_stock_bridge 获取板块关联度数据
3. 对高关联度个股运行 smart_screener Phase1 量化打分
4. 综合排序：`总分 = Qlib量化分 × 0.6 + 板块关联度 × 0.4`
5. 输出趋势 Top10 + 短线 Top10 个股

**CLI 参数**:
```bash
python unified_pipeline.py \
  --as-of 2026-07-01 \
  --trend-top-n 5 \
  --burst-top-n 5 \
  --min-relevance 0.6 \
  --output reports/unified/{date}/ \
  --mode quick  # quick/deep
```

**注意事项**:
- smart_screener.py 位于 `E:\Workspace\ai-stock-projects\ai-hedge-fund\`，需要正确设置 sys.path
- Qlib 初始化有 Windows 特殊处理（freeze_support、joblib monkey-patch），参考 smart_screener.py 开头
- MiMo API key: `sk-cnykvq4og9nkj05ga349ffpa756k2vy2jlx4ltdpv1h69wgu`

### P1 — 增强功能

#### Task 3: 板块-个股共振报告

在 unified_pipeline 输出中增加：
- 哪些个股同时受益于多个板块（如化学制药+生物制品）
- 板块资金流向变化趋势（今日 vs 昨日）
- 个股在板块中的相对位置变化

#### Task 4: 历史回测验证

用 `sector_research_backtest.py` 已有框架，回测"选热门板块成分股"策略：
- 对比：纯 Qlib Top50 vs 板块加权 Top50
- 指标：胜率、夏普比率、最大回撤
- 回测周期：至少 3 个月

#### Task 5: 每日自动运行

在 smart_screener.py 或新增脚本中支持 cron 调度：
- 每日 15:30（收盘后）自动运行
- 输出推送到指定渠道

---

## 四、后续优化方向

### 4.1 短期（1-2 周）

- [ ] 板块关联度加上**个股历史板块归属稳定性**（过去 20 个交易日是否稳定属于该板块）
- [ ] 支持**概念板块**（当前只做行业板块，概念板块如"算力""AI"等热度更高）
- [ ] 输出增加**板块轮动信号**（哪些板块正在从短线切换到趋势）

### 4.2 中期（1 个月）

- [ ] 接入 ai-hedge-fund 的 **Phase3 Agent 深度确认**（对板块加权 Top10 运行 5 个 A 股 Agent）
- [ ] 增加**板块资金流监控**（当板块资金流向反转时自动预警）
- [ ] 回测框架完善，输出 Sharpe/Sortino/Calmar 等完整风险指标

### 4.3 长期（季度级）

- [ ] 盘中实时版本（当前仅盘后）
- [ ] 板块轮动策略自动化（自动切换持仓板块）
- [ ] 与 qlib 项目的 Optuna 调参联动（板块加权参数自动优化）

---

## 五、环境与依赖

### Python 环境
- 主 venv: `E:\Workspace\ai-stock-projects\ai-hedge-fund\.venv`（Python 3.12）
- theme-sector-radar 可以共用此 venv 或独立 venv

### 关键依赖
```
akshare          # 板块数据 + 成分股查询
pydantic         # 数据模型（theme-sector-radar 已用）
pandas           # 数据处理
requests         # 腾讯API调用
```

### 网络环境
- **Clash Verge 代理**: 127.0.0.1:7897，会拦截东方财富 API
- **可用 API**: 腾讯行情 `qt.gtimg.cn`（已验证）、新浪财经 API
- **被拦截**: 东方财富 push2.nufm.dfcfw.com、akshare 部分接口
- **绕过方案**: 调用前清除 `_PROXY` 环境变量，或设置 `no_proxy`

### 数据路径
- Qlib 数据: `~/.qlib/qlib_data/cn_data`（3093只A股 + SH000300指数）
- 板块雷达缓存: `theme-sector-radar-dev/data_cache/`
- 板块雷达报告: `theme-sector-radar-dev/reports/`

---

## 六、执行指令示例

### 给 Codex/Codrx 的指令模板

```
请指挥 Hermes Agent 完成以下任务：

1. 在 E:\Workspace\ai-stock-projects\theme-sector-radar-dev\ 下创建 sector_stock_bridge.py
   - 读取 reports/sector_scores/ 最新报告
   - 查询板块成分股（AkShare）
   - 计算三维度板块关联度（成分股权重×涨幅排名×资金流对齐）
   - 参考 PROMPT_FOR_CODEX.md 中的输出格式

2. 创建 unified_pipeline.py
   - 串联板块雷达 + 桥接层 + 个股打分
   - 输出趋势Top10和短线Top10个股
   - 参考 smart_screener.py 的 Qlib 初始化方式

3. 运行测试验证
   - 用 2026-07-01 的数据跑一次完整流程
   - 输出报告到 reports/unified/2026-07-01/
```

---

*本文档由 Hermes Agent 生成，供 Codex/Codrx 项目协调使用。*
*最后更新: 2026-07-02*
