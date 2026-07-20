# Theme Sector Radar — 项目总览

> 板块雷达 × 个股选股联合系统，供 Codrx 协作优化参考。

---

## 一、项目定位

- 独立 CLI 盘后分析系统，不接入 LangGraph，不依赖 LLM
- 纯规则评分，确定性输出
- 只输出板块强弱筛选 + 个股推荐，不做自动交易
- 服务于 A 股短线板块研究

---

## 二、当前目标架构

> 2026-07-19 运行约定：方向分路径是默认板块主路径；趋势 TopN / 短线 TopN 路径已关闭，仅保留为显式 `legacy` 研究模式。方向分或 Linkage V2 不可验证时不自动回退。

```
数据层
  → 板块雷达基础分
  → 方向分：时序 50% + 截面 30% + 排名动量 20%
  → 方向板块主路径筛选

基础分与方向分不直接相加：基础分生成当前板块排名，排名历史间接进入方向分的排名动量层；正式板块筛选由方向分主路径负责。

板块-个股桥接
  sector_stock_bridge.py / unified_pipeline.py
  → 板块成分股查询与身份过滤
  → Linkage V2：收益共振、相对强弱、成分股权重、资金流、数据质量
  → Linkage V2 + 个股 Quant 排序
  → 板块配额、去重、集群集中度约束
  → 默认最多 30 只 Paper/Shadow 候选

并行 Shadow 支路
  → 行业板块 ML Shadow
  → 个股候选池 ML Shadow
  → 统一事件层与事件调整 Shadow
  → 只做 A/B 研究对照，不覆盖正式评分或候选链
```

---

## 三、核心模块

### 3.1 板块评分（已有）

| 模块 | 文件 | 说明 |
|---|---|---|
| CLI 入口 | `theme_sector_radar/cli.py` | 20+ 种运行模式 |
| 主流程 | `theme_sector_radar/pipeline.py` | 串联各 Agent |
| 数据模型 | `theme_sector_radar/models.py` | Pydantic 模型 |
| 数据层 | `theme_sector_radar/data/` | AkShare / 缓存 / 降级 |
| Agent 组 | `theme_sector_radar/agents/` | 7 个分析 Agent |
| 评分算法 | `theme_sector_radar/scoring/` | 基础分、方向分、Linkage V2 与个股 Quant |
| 报告生成 | `theme_sector_radar/reports/` | JSON / Markdown |

### 3.2 板块-个股桥接（新增）

| 功能 | 说明 |
|---|---|
| 成分股查询 | AkShare `stock_board_industry_cons_em`，降级到内置映射 |
| 行情获取 | 腾讯 API `qt.gtimg.cn`（绕过 Clash） |
| 资金流 | 东方财富（被封锁时降级到中性值） |
| 关联度计算 | Linkage V2：收益共振、相对强弱、权重、资金流、数据质量；旧关联度只作历史对照 |
| 缓存 | `data_cache/sector_stocks/` 按日期缓存 |

### 3.3 联合选股（新增）

| 功能 | 说明 |
|---|---|
| 综合评分 | `Linkage V2×0.7 + 个股 Quant×0.3` |
| 量化评分 | 降级方案: 涨幅+估值+市值（预留 Qlib 接口） |
| 输出 | 默认输出方向分 + Linkage V2 候选池；legacy 模式保留趋势/短线 Top10 |
| 报告 | `reports/unified/{date}/` |

### 已知网络限制

- Clash Verge 代理 (127.0.0.1:7897) 封锁东方财富所有 API
- `push2.eastmoney.com` 连接重置，即使清除代理环境变量也无效
- 腾讯 API 和新浪财经 API 可用作降级

---

## 五、内置板块映射（20 个板块）

```
证券、保险、化学制药、医疗服务、养殖业、教育、
农产品加工、多元金融、物流、生物制品、
电子化学品、半导体、小金属、光学光电子、厨卫电器、
中药、能源金属、贵金属、机场航运、非金属材料
```

**覆盖不足**：板块评分有 20+ 板块，但映射只有 20 个，部分热门板块无成分股数据。

---

## 六、CLI 命令

```bash
# 板块评分
python -m theme_sector_radar.cli --score-sectors --as-of 2026-07-02

# 板块综合研判
python -m theme_sector_radar.cli --research-agents --as-of 2026-07-02

# 板块-个股桥接
python sector_stock_bridge.py --as-of 2026-07-02

# 联合选股
python unified_pipeline.py --as-of 2026-07-02 --mode quick


# 测试
python -m pytest tests/ -v
```

---

## 七、已知问题

| 问题 | 影响 | 状态 |
|---|---|---|
| 东方财富 API 被封锁 | 无法下载更多历史数据 | 降级中 |
| 板块映射覆盖不足 | 部分热门板块无成分股 | 待扩展 |
| 无真实资金流数据 | 关联度计算简化 | 等待 API 恢复 |
| Qlib 未接入 | 个股量化用降级方案 | 预留接口 |

---

## 八、待优化方向（供讨论）

### 短期

1. **扩展板块映射** — 覆盖更多热门板块（半导体、中药、贵金属等）
3. **优化关联度公式** — 调整权重配比
4. **接入 Qlib** — 替换降级量化方案

### 中期

5. **接入 ai-hedge-fund Phase3** — 5 个 A 股 Agent 深度确认
6. **增加板块轮动信号** — 检测板块从短线切换到趋势
8. **概念板块支持** — 当前只做行业板块

### 长期

9. **盘中实时版本** — 当前仅盘后
10. **板块轮动策略自动化** — 自动切换持仓板块
11. **参数自动优化** — Optuna 调参联动

---

## 九、文件清单

```
新增文件:
  sector_stock_bridge.py       # 板块-个股桥接层
  unified_pipeline.py          # 联合选股管线
  PROMPT_FOR_CODEX.md          # 开发指令文档

新增测试:
  tests/.../test_unified_bridge.py  # 23 个测试用例

新增报告:
  reports/unified/{date}/           # 联合报告

未修改:
  theme_sector_radar/               # 原有模块零修改
```

---

*文档生成时间: 2026-07-02*
*供 Codrx 协作优化参考*
