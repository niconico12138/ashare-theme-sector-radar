# A 股主题板块雷达

一个面向 A 股主题与行业轮动的研究型量化系统：从可追溯的数据输入开始，完成板块方向识别、板块内个股筛选、择时与退出研究、历史验证和 Shadow 模型对照。

## 准确定位

本项目当前是 **Paper/Shadow research system（纸面/影子研究系统）**，不是实盘交易系统。

- 不连接券商，不提交订单，不生成仓位指令。
- `formal_candidate_selection` 是研究候选集合，不是买入清单。
- 输出不作为个股操作依据。
- 所有新评分、Linkage、择时、止盈止损和 ML 结果都必须经过数据时点、样本量和晋级门禁。
- 缺失、过期、无法证明来源或无法证明 PIT（point-in-time）的数据会被标记、降级或 fail-closed。
- 研究结果不构成投资建议，也不承诺未来收益。

## 系统做什么

系统回答四个依次收紧的问题：

1. 当前哪些板块值得进入研究范围？
2. 板块内哪些股票真正与该板块方向具有关联？
3. 在同一候选池中，哪些股票更值得优先研究？
4. 入场、退出和 Shadow 排序证据是否足够支持下一步研究？

## 当前本地研究状态（如实说明）

本地研发工作树已经包含比公开基础版本更完整的实验链，但以下结果仍属于 Paper/Shadow：

- 方向分 → Linkage V2 → `formal_candidate_selection` 链已可运行。2026-07-16 的一次结果包含 1,029 条候选关系、554 只股票，最终保留 30 条研究候选；这不是生产晋级。
- 当前默认候选主链是方向分 → Linkage V2。趋势 TopN / 短线 TopN 路径已从默认运行中关闭，仅在显式 `legacy` 研究模式下启用；方向主链证据不足时 fail-closed，不自动回退旧路径。
- 旧 `relevance_score` 的 `0.60` 门槛不再参与方向主链筛选；它仍在桥接层全量计算并以 `legacy_relevance_score` 形式保留，仅用于历史对照。正式板块关联准入由 Linkage V2 负责；显式 `legacy` 模式仍保留旧筛选行为以便复核。
- Linkage V2 的 A/B/C 评估仍为 `insufficient_evidence`：历史成分股没有完成足够可靠的版本化，严格 PIT 证据和成熟 3/5 日标签不足。
- ML 支路采用 LightGBM LambdaRank 做候选池内的个股 Shadow 重排序，不负责选板块，也不决定买入、止盈或止损。当前只有 1 个历史重建日、0 个前瞻候选日和 0 个成熟 5 日标签日，因此真实训练被门禁阻止；合成训练仅用于验证软件链。
- ML 训练参数由 `config/ml_stock_ranker_v1.json` 和 `theme_sector_radar/ml/experiment.py` 统一登记；配置内容 SHA 与物理文件 SHA 分开记录，旧关联度不进入 ML 特征，promotion 和 live trading 永远关闭。
- 择时、非平稳入场、动态止盈、动态止损和压力集研究均保留保守结论；样本不足时保持 `observe`、`insufficient_evidence` 或 `not_evaluated`，不会包装成可交易策略。

## 总体架构

```mermaid
flowchart TB
    subgraph S["一、数据来源"]
        S1["AkShare / 公开行情"]
        S2["本地 StockDB（可选）"]
        S3["本地行情服务（可选）"]
        S4["离线夹具 / 脱敏示例"]
    end

    subgraph D["二、数据与溯源层"]
        D1["数据源路由、重试与新鲜度"]
        D2["行情、K线、板块成分、基准"]
        D3["标准化、身份、PIT 与覆盖率校验"]
        D4["快照、交易日历、SHA 与数据血缘"]
    end

    subgraph V["三、统一事件层 Shadow"]
        V1["公告、政策、商品与行情异常"]
        V2["事实 / 生命周期 / 证据 / 市场反馈视图"]
        V3["板块与个股事件调整 A/B Shadow"]
    end

    subgraph R["四、板块研究层"]
        R1["板块雷达基础分"]
        R2["方向分：时序 50% / 截面 30% / 排名动量 20%"]
        R3["基础分 → 当前排名 → 排名动量（间接关联）"]
        R4["方向候选与板块簇约束"]
        R5["风险、数据质量与多窗口共识"]
    end

    subgraph B["五、板块到个股层"]
        B1["板块成分股与身份过滤"]
        B2["Linkage V2：共振、相对强弱、权重、资金流、质量"]
        B3["个股 Quant 因子与质量覆盖"]
        B4["Linkage V2 + Quant：去重、配额、集中度"]
    end

    subgraph T["六、择时与退出研究层"]
        T1["1m / 5m 因子研究"]
        T2["下一交易日入场与因果路径"]
        T3["动态止盈、止损与压力集"]
        T4["过拟合、尾部与稳定性审计"]
    end

    subgraph M["七、Shadow 验证层"]
        M1["行业板块 ML Shadow"]
        M2["个股候选池特征归档"]
        M3["个股 ML Shadow：LightGBM LambdaRank"]
        M4["Quant / Linkage / Hybrid / Event A-B 对照"]
        M5["PIT、成熟标签、漂移与晋级门禁"]
    end

    subgraph O["八、研究输出层"]
        O1["JSON / Markdown 日报"]
        O2["板块与个股候选"]
        O3["审计产物、SHA、降级标记"]
        O4["历史验证与 Shadow 对照报告"]
    end

    S1 --> D1
    S2 --> D1
    S3 --> D1
    S4 --> D1
    D1 --> D2 --> D3 --> D4
    D3 --> V1 --> V2 --> V3
    D3 --> R1
    D3 --> R2
    R1 --> R3
    R2 --> R3
    R3 --> R4 --> R5
    R1 -. "不与方向分直接相加" .-> R2
    V3 -. "事件调整 Shadow，不覆盖正式分" .-> R5
    V3 -. "板块 / 个股 A-B 对照" .-> B3
    R4 --> B1
    B1 --> B2 --> B4
    D3 --> B3
    B3 --> B4
    B4 --> T1 --> T2 --> T3 --> T4
    R2 -. "行业 ML 并行 Shadow" .-> M1
    B4 --> M2 --> M3
    B4 --> M4
    T4 --> M1
    M1 --> M4 --> M5
    M3 --> M4
    V3 -. "事件特征仅作 Shadow 输入" .-> M4
    R4 --> O1
    B4 --> O2
    T4 --> O4
    M5 --> O4
    D4 --> O3
    M5 --> O3
```

## 股票如何被选出来

```mermaid
flowchart LR
    A["研究日期"] --> B["冻结当日可见数据"]
    B --> C["校验行情、成分股、交易日历与来源"]
    C --> D["计算基础分与基础排名"]
    D --> E["计算时序 / 截面 / 排名动量方向分"]
    E --> F["方向主路径筛选板块"]
    F --> G["读取板块成分股与个股因子"]
    G --> H["计算 Linkage V2 与个股 Quant"]
    H --> I["排除身份、数据或关联证据不足的股票"]
    I --> J["按板块配额、去重与板块簇集中度约束"]
    J --> K["输出 formal Paper/Shadow 候选"]
    K --> L["未来标签、择时、事件与 ML Shadow 对照"]
```

当前候选排序的研究逻辑是：基础分生成板块当前排名，方向分使用板块自身时序、截面强度和历史排名动量，方向分主路径决定研究宇宙；基础分与方向分不直接相加，但基础排名会间接进入排名动量层。身份过滤后保留方向成分股，Linkage V2 判断股票是否承接板块，Quant 分补充股票自身质量；旧关联度只作为历史对照字段，趋势/短线旧路径默认关闭。行业 ML、个股 ML 和事件调整均为独立 Shadow，不覆盖受保护的正式评分字段。

## Codex / MCP 调用层

现有 Python 程序仍是策略和数据的唯一事实来源；MCP 只提供稳定的结构化调用边界，Skill 只规定调用顺序和安全规则。当前 MCP 工具包括 `check_data_health`、`get_direction_candidates`、`get_stock_ranking` 和 `run_full_paper_pipeline`。它们全部保持 `paper_shadow_research_only`，不连接券商、不生成订单。运行说明见 [`docs/mcp_paper_shadow.md`](docs/mcp_paper_shadow.md)。

## 数据层与可信度

数据流按 `as_of` 日期组织，并尽量绑定以下证据：

- 行情和板块成分来源、查询日期、最新可用日期。
- 版本化 A 股交易日历及其 SHA256。
- 候选源文件、标签文件、模型和报告的内容 SHA。
- 因子覆盖率、缺失因子、降级原因和数据质量状态。
- 历史评估的 PIT 证据、purge/embargo、训练/观察窗口与样本外资格。

如果无法证明“当时可见”，系统不会把回放结果称为严格 PIT；如果未来标签尚未成熟，系统不会把缺失标签当作负样本。

## 目录说明

| 路径 | 职责 |
|---|---|
| `theme_sector_radar/` | 核心包：数据、模型、评分、Agent、历史、回测、报告、择时和 ML Shadow。 |
| `scripts/` | 日常运行、候选导出、历史回填、择时研究、Linkage、ML 归档和审计 CLI。 |
| `tests/` | 数据契约、评分、候选链、PIT、paper-only、择时、退出和 ML 测试。 |
| `docs/` | 架构、运行手册、研究设计、结果和复现说明。 |
| `config/` | 可公开的配置示例，例如板块簇映射。 |
| `examples/` | 小型脱敏示例。 |
| `models/` | 仅保存可公开的合成/研究模型夹具，不代表真实策略效果。 |
| `data_cache/`、`reports/`、`test_output/` | 本地数据和生成产物，默认不纳入 Git。 |

`.planning/` 是本地协作过程材料，不属于公开源码发布内容。

## 安装与离线示例

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e .[dev]
```

不接网络数据即可运行示例模式：

```bash
python scripts/export_top30_candidates.py --sample
python scripts/run_selection_validation_batch.py --mode sample --force
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --offline-fixture --fixture-profile full --lookback-days 5
```

真实数据模式需要用户自行配置 `.env`、AkShare/行情服务或本地 StockDB；真实数据、密钥和本地缓存不应提交到 Git。

真实日常运行示例：`python run_daily.py --as-of 2026-07-08 --provider akshare`。
日常报告写入 `reports/theme_sector_radar/<date>/`，并可包含 `run_log.json`；该目录是本地生成产物，不纳入 Git。

## 验证

```bash
python -m pytest tests/ -q
python -m compileall theme_sector_radar scripts
```

网络测试需显式启用；普通测试默认遵守离线/无网络策略。发布前应检查 `git diff --check`、严格 JSON、paper-only 合约和受保护评分字段扫描。

## License

MIT License，详见 [LICENSE](LICENSE)。
