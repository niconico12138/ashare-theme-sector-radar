# 非平稳市场下的买入与退出研究设计

## 状态与边界

- 状态：已确认，后续研究方向固定。
- 执行状态：历次评分可信度复审发现均已完成 TDD。当前 fresh hermetic 全量 `3258 passed, 19 deselected in 246.70s`，0 failed；Path A v3 产物身份与 paper-only 可信链未重算。行业方向三层分解仅作为新增 shadow breakdown，正式分与晋级结论不变。旧关联度已降级为历史对照字段，方向主链不再使用 `0.60` 硬门槛。ML Shadow 真实数据 readiness 仍阻断训练，最终独立复审已完成且 A/B 均为 `Critical=0, Important=0`。
- 当前固定身份：selection manifest `9e297b2aa8914f8bded8a2eb507f91b7752bffe065dd036cb248fb25720fa066`；candidate 1m/5m manifest 分别为 `d085d410bccb629565202af6134242a9611b2df7ed6b3c039b4636cfdde8b4fc` / `b5338934e24cf4b2d11d71e7665e560d62adda54e8a14ed977d940859f8cb08f`；decision SHA 为 `7c8cfa3500495ee095c5952d36f6fcea472891ea9e6c8dd9e78e68b66585e3f9`；calendar SHA 为 `62ce83c12f6e73fd598e220896d27cffc6bc23268ad9644c622f4bca24e1e8f7`；长期事件 SHA 为 `e92a2fd232cddb2df0abb14b0e8e374ad7a2423f2e1840df6a02d46506ab979a`。当前决策为 11 `observe`、3 `insufficient_evidence`、0 Champion/Challenger，`live_trading_ready=false`。旧 `35dc70...` 及更早 decision SHA 均为内容寻址历史身份。
- 范围：paper trading / shadow research。
- 禁止：不连接券商，不生成实盘指令，不修改官方分数字段。
- 核心原则：近期样本决定当前使用规则，同类市场环境负责确认，长期历史只做灾难性风险否决。

> 因果复审已确认旧 paper records 存在同日回扫前视。旧动态止盈正收益、旧止损零触发和旧长期 20,573 条触发数字均已作废，不得再作为研究结论引用。

## 问题清单

1. 买入因子可能随市场变化而衰减，尚未完成近期有效性和冗余分析。
2. v31/v32 比 v29 简洁，但仍经过多轮迭代，存在阈值选择、版本选择和小样本过拟合风险。
3. 动态止盈尚未形成稳定 paper 优势，策略相关样本偏少，长期策略关联路径仍缺失。
4. 动态止损没有稳定因子；此前以次日 -5% 为主要标签，与盘中止损目标不完全一致。
5. 全历史等权会使旧行情压制当前规律；只看近期又会放大短样本偶然性。
6. 板块历史成分关系不完整，长期板块测试只能作为覆盖受限的辅助证据。

## 多时间尺度验证框架

### 当前有效性

- 最近 60 个交易日决定当前是否可用。
- 最近 120 个交易日确认不是短期偶然。
- 当前最后 20 个交易日是已经被多轮研究观察过的 `observed_evaluation_tail`，不是盲测 holdout，不得用于样本外声明。
- 当前尾部窗口 20 日中有 18 日存在源候选文档、14 日存在至少一个完整 session 候选；其中 2026-07-01 是物理文档存在但候选数为 0 的日期。日期覆盖不足时所有相关硬门槛必须为 `insufficient`。
- 真正的 holdout 只能在参数、版本、代码和数据口径不可变冻结后向前采集，期间不得查看结果后调参。

### 市场环境确认

- 按强势、震荡、弱势市场分别统计。
- 当前市场环境必须有效。
- 非当前环境不要求全部有效，但不得出现不可接受的尾部风险。

### 长期否决

2024-2025 历史样本不与近期样本等权选优，仅检查：

- 最大回撤和尾部事件是否恶化。
- 规则是否仅在单一时期有效。
- 是否存在参数轻微变化即失效。
- 是否由少数日期、板块或股票主导。

## 买入因子与 v31/v32

- 对八类买入因子分别计算 60/120 日有效性、方向一致性和市场环境依赖。
- 做相关性/重复贡献分析，禁止重复因子通过数量放大同一信息。
- 对 v31/v32 做条件移除、阈值上下扰动、五段 walk-forward、观察尾部、集中度和版本比较；当前观察尾部只作描述性压力检查。
- 与较简单基线比较；只有复杂版本在样本外稳定改善才保留复杂度。
- 当前不新增买入因子，先找出现有组合缺口。

## 动态止盈

- v31/v32 含尾盘与收盘结构因子，信号只能在信号日收盘后确认；禁止使用信号日早盘或盘中 K 线作为策略 entry 后回扫。
- 5m 的约束覆盖整条研究链，不只覆盖 entry/exit 路径：用于选中 v26/v31/v32 的候选盘中因子也必须由完整 1m session 重聚合后重新计算。原生 5m OHLC 或缺少来源身份的 5m 候选根目录不得进入审计。
- 可信 5m 候选写入新的 derived root，保留原候选文件不覆盖；每个输出绑定源 1m 文件 SHA、`aggregated_from_complete_1m_session` 身份和完整/缺失计数。缺少 241 根完整 1m bars 的候选清空盘中因子并保持不可选。
- 因果 entry 固定为下一真实交易日第一根完整 1m/5m K 线开盘价；记录同时保存 `signal_date`、`entry_date`、源 cadence 和数据哈希。
- 下一交易日分钟线必须来自可验证的历史分钟数据源；缺失、cadence 不符或存在首 bar 缺口时保持未标注，不回退到信号日数据。
- 未触发退出的收益为下一交易日 entry 开盘至该日收盘收益；旧的选股日收盘至次日收盘标签只允许保存在 causal-valid 记录的 `selection_forward_return_pct`，invalid 记录不得残留该字段，也不得与盘中退出收益直接比较。
- 策略相关近期样本决定 2%/3% 峰值回撤候选。
- 长期路径样本用于压力测试，不参与近期参数等权投票。
- 指标包括触发后 MAE、保存回撤、错失上涨、下一根 K 线成交和市场环境稳定性。
- exit_v4 保持 paper 候选，验证前不升级。

## 动态止损

主要标签改为触发后的路径，而不是只看次日收益：

- 触发后 5、15、30 根 K 线收益。
- 触发后最大不利变动。
- 触发后最大有利变动。
- 快速修复率。
- 相比固定 -3% 风险基线减少的回撤。

相对弱势、资金流恶化和板块同步走弱全部按新标签重测；旧的次日尾部率只作为辅助指标。

止损与止盈必须复用同一因果 entry 路径：

- 只允许 v31/v32 已选 entry，接口不得默认退化为全部候选。
- -3% 触发以 trigger bar 收盘确认，下一根连续交易 K 线开盘模拟成交。
- 缺失中间 bar 时 next-bar fill 不可用，对应 5/15/30 bar 路径不得标记完整；午间休市按 A 股交易时段连续性处理。

## Champion / Challenger

- Champion：当前近期与环境门槛均通过的 paper 版本。
- Challenger：新候选，只能并行观察，不能直接替换 Champion。
- 每月重新审计；切换必须有完整样本外证据。
- 任一长期否决条件触发时，版本降级为 observe 或 insufficient_evidence。

## 晋级条件

候选必须同时满足：

1. 最近 60/120 日均优于基线。
2. 当前市场环境有效。
3. 冻结后真正的前瞻 holdout 不反转；当前 `observed_evaluation_tail` 不具备该证明资格。
4. 阈值扰动后方向一致。
5. 时间、板块、股票集中度受控。
6. 长期历史无灾难性回撤恶化。
7. 下一根 K 线成交并计入摩擦后仍成立。

未满足任一硬门槛不得进入执行层。

## 最新全链落地约束

- 候选数据必须先通过 `candidate_source_identity`：源 1m 文件 SHA、派生文件 SHA、候选集合、完整/无效状态、bars 和因子重算结果必须一致。
- 1m 有效 session 固定为 241 根；5m 有效 session 固定为由同一完整 1m session 聚合出的 48 根。原生 5m 文件不得进入选股或退出研究。
- records 必须逐条重算 signal/entry 交易日、非空证券名称、路径 SHA、entry open、MFE/MAE、收盘收益、退出触发、模拟成交和数据质量；无效记录不得残留路径或 `selection_forward_return_pct`。
- records 生成端与 entry/profit/stop 审计端都必须从调用方绑定的 source root 与当前 candidate root 独立重建完整 `(signal_date, code, timing_version_id)` cohort；缺失、额外、重复记录、snapshot/as_of、候选源字段或有效 selection label 不一致一律拒绝，并保存内容确定的 key manifest SHA。
- canonical 依赖链限定为 intraday factor backfill → trusted 1m/5m candidate rebuild → paper records → entry/profit/stop audits → final decision；该链所有 JSON 输入使用严格解析，拒绝 `NaN`、`Infinity`、数值溢出和重复 object key，所有 artifact 使用内容寻址归档和原子替换。
- trusted candidate rebuild 的输入根与输出根必须分离；派生候选除 bars、bar identity 和重算盘中因子外，所有文档及候选继承字段必须与源 1m 文档一致。
- `run_timing_factor_research.py`、frequency validation 与 data-source probe 仅属 exploratory/latest-health 输出，不具 canonical provenance 资格，不得作为 records 或 audit 输入；其固定文件名或覆盖语义不在本文的 canonical 完整性声明内。
- entry/profit/stop 审计必须重新验证当前 candidate root manifest，不能只信任 records 中保存的旧身份；profit 必须由调用方绑定 candidate root、selection root 和精确 v31/v32 集合，上游 entry records 必须为精确 v26/v31/v32 集合。
- 长期止损 reaudit 与 stop audit 只能读取先校验路径/SHA 的 JSONL 事件文件，并从事件逐条重算 summary、baseline 和 factors；固定使用 5/15/30 bar、5 折和最少 30 信号，顶层与逐事件 paper 身份必须严格为布尔真。报告内嵌事件、声明式参数或指标不得成为可信输入；声称策略关联时，每条事件必须携带并通过版本、规范日期、causal entry、path SHA 与 cadence 校验，否则降级为辅助证据。
- profit 长历史只有由调用方独立绑定日历路径/SHA、candidate/source/selection root，逐条 causal record 与精确 v31/v32 cohort 均通过当前源重建后才可参与否决，否则保持 `not_evaluated`。
- 最终 decision 必须同时绑定审计报告 SHA 和其上游 records SHA，并强制精确的 2 份 entry、4 份 profit（1m/5m × 2%/3%）和 2 份 stop 拓扑；决策时还必须重算当前 1m/5m manifest，并核对同周期四份报告的 candidate root、source root、manifest 与日历 SHA。任一缺失、额外或文件内容改变都要求拒绝或重新生成下游结论。
- 当前环境只允许绑定日历中的最新交易日。最新日无有效标签时保持 `insufficient`，禁止回退旧环境。
- 止损研究范围固定为 v31/v32；v26 只作为买入基线，不得混入止损事件。
- realtime 收盘确认必须同时满足 snapshot label 与 `spot_result.generated_at` 均严格晚于 15:00，且源日期等于 `as_of`；任一字段缺失、无效或未收盘都必须 fail closed。
- selection validation 必须通过 `selection_source_identity` 扫描 `DATE/next_day_selection_validation.json`，manifest 绑定日期、相对路径和文件 SHA；非日期辅助目录只有在不直接放置目标文件时可忽略，若直接放置目标文件必须 fail closed。
- `observed_evaluation_tail` 的日期集合必须严格等于可信交易日历最后 20 日，且升序唯一；覆盖计数、覆盖比例和 status 必须从当前 candidate manifest 的 `document_dates` 与 `complete_candidate_dates` 重新计算，不能信任旧记录或报告自报。
- stop 长历史不得因事件或报告自报策略关联而晋级；缺少调用方独立 entry/calendar/cohort 外部锚时必须保持 `auxiliary_only`，`eligible_as_long_history_veto=false`，并标记外部锚不可用。
- final decision 必须由调用方固定八份 audit SHA，加载报告前比较实际文件 SHA；2 entry、4 profit、2 stop 拓扑必须精确，且当前 candidate/selection manifest 与所有报告中的 root、range、manifest 和日期集合必须一致。
- CLI 参数或继承环境变量解析出的 effective report root 必须在任何 TCP/HTTP/health 请求前完成验证；显式根缺少请求日期的 exact-date score JSON 时必须立即拒绝，禁止扫描或回退其他日期。默认根也必须先严格解析并执行相同 score contract：exact 文件存在但损坏时拒绝，只有 exact 文件物理缺失时才可按日期倒序选择不晚于 `as_of` 的合法历史文件；损坏的最近历史文件必须继续查找更早合法文件。父进程把同一份已校验 payload 与实际 fallback 日期交给 child，child 不得重读文件或把 fallback 日期伪装为请求日期。默认/显式入口都必须先拒绝非 ISO 日期，禁止把 `as_of` 当作路径片段。score payload 必须包含非空 `scores`，每项具备合法板块名称/类型且数值字段有限；可选 trend/burst level 字段存在时必须为文本。严格 JSON 对任何转换为 float 时溢出的超大整数给出带字段路径的受控拒绝。
- 显式根下 research/concept/cache 的稳定读取必须先打开文件，再复核 canonical containment 与文件身份，拒绝 symlink/junction 交换；industry 顶层日期、类型、报告类型和每行必需字段必须完整匹配，concept 必需表头和非空数值必须完整，任一行失败整源拒绝。cache key 与 payload 的 `as_of_date` 必须绑定请求研究日，显式根禁用 cache 写入以消除创建时 junction 竞态，默认无 override 的历史 cache 行为保持不变。bridge enrichment 必须同时保留计算所需的 `weight` 和兼容展示字段 `sector_weight`，不得在归一化前丢失真实成分权重。测试 fixture 必须同时清除继承报告根、模块路径缓存及 bridge 全局状态。
- paper-only 结构契约必须作为生产共享门禁递归拒绝订单/命令/仓位/价格字段，包括 `side`、`action`、`tradeAction`、`executionSide`、`positionPct`、`quantity`、`qty`、`limit_price`、`broker_order`、`live_order` 及数值或布尔触发值；records writer 必须在创建 artifact 前校验整份报告，records 顶层与逐条记录、final 的 records provenance 以及八份 audit 都必须从同一已解析快照执行该门禁。有效记录的 `factor_exit_triggers.entry_price` 仅接受非布尔、正有限 int/float；新生成的无效记录不得写该字段。冻结 canonical 只兼容 `causal_entry_valid=false`、无 bars 且数值恰为 0 的旧占位，字符串、布尔、null、负数和有效记录的 0 均拒绝。final 还必须把 audit 内嵌的 calendar 日期集合、来源和范围与已哈希日历 JSON 逐项比较，并要求 stop 1m/5m 的 records 路径与 SHA 分别等于对应 entry records；`records_*`、顶层 `entry_records_*` 与 `label_source.entry_records_*` 任一别名必须 path/SHA 成对出现，多组并存时必须完全一致，禁止跨别名拼接或优先级遮蔽冲突。
- 组合实验的 candidate discovery、selection provenance 与报告 data coverage 必须共用 `effective_end=min(requested_end, as_of)`；`end` 为空或晚于 `as_of` 时均不得纳入未来候选。
- final decision 的冻结 serializer 必须保持既有扩展 source provenance 形状：`path`、实际/调用方预期 SHA、schema/as_of/timeframe/snapshot、calendar、candidate 与上游 records 身份均继续持久化；加载时对已解析并哈希的 calendar snapshot 执行完整 schema/market/date_count/日期范围/周末/覆盖校验，并比较 calendar dates/source/requested start/requested end。1m/5m 单粒度校验后还必须联结相同 selection manifest、calendar identity 和由已验证 source path/SHA 构造的共享 source snapshot；临时联结身份不写入冻结 serializer。治理校验不得删减既有字段或改变已冻结 decision JSON 的可复现 SHA。
- 所有 calendar artifact 必须校验规范 ISO 范围、`date_count` 与日期集合自洽，拒绝重复日期，且实际日期不得越过声明范围；顶层 builder 对字符串不得先截断再校验，只允许真实 `date/datetime` 对象规范转换。生成 records 时保存的 dates/source/path/SHA/requested range 必须由 entry/profit/stop audit 与调用方日历逐项复验，calendar A 的 records 不得交给 calendar B。candidate rebuild 的 source/output 根必须互不包含；candidate 与 selection 文档的 payload `as_of` 必须等于规范 ISO 目录日。source minute bars 必须通过包含父 candidate code/name 与 bars 的安全 envelope SHA 绑定证券身份，不能用对象子树或换证券数据维持旧哈希。selection/candidate manifest 校验返回刚解析并哈希的内存快照，records、entry/profit/stop、profit-long 只能消费该快照；rebuild source/derived、records、calendar、八份 audit、long-history envelope 与事件 JSONL 的解析内容和声明 SHA 同样必须来自各自同一 byte snapshot。stop-history reaudit 也必须在同一 JSONL bytes 上同时完成 SHA、逐行严格解析和递归 paper-only 门禁。长历史事件仅对 `fixed_stop_path.trigger_price` 这一正有限观测标量作窄豁免，其他类型或嵌套执行字段继续拒绝；新事件必须显式携带完整 paper guard，仅 SHA 固定为 `e92a2fd232cddb2df0abb14b0e8e374ad7a2423f2e1840df6a02d46506ab979a` 的既有事件文件可兼容缺少两项后来新增的 guard。普通 `pytest -q` 必须默认排除显式 `network` marker，网络合同只能单独显式运行，不属于 hermetic paper/shadow 验收。daily wrapper 的默认根只用于父进程校验并通过 stdin 绑定 payload，不得向 child 注入 report-root override；因此历史 `data_cache/sector_stocks` 行为不变。新 serializer 还显式写入 no-execution 与不修改官方分数身份。下一根 open 缺失时不得用 close 冒充模拟成交。

## 前瞻冻结路线

- 从本次规则冻结后开始，日历层面的最短路线是连续新增 34 个交易日：前 14 日把现有 106 日扩到 120 日训练区，后 20 日作为从未查看过的前瞻 holdout。
- 34 日只是日历下限，不自动代表数据下限。训练区和前瞻 holdout 每个交易日都必须有源文档和至少一个完整 session 候选；当前 106 日中有 104 日存在源文档、100 日满足完整候选覆盖，因此还必须回补缺口或继续滚动采集，直至 120 日训练区与 20 日前瞻 holdout 均达到 100% 日期覆盖。
- 冻结期间不得修改 v26/v31/v32 条件、2%/3% 退出阈值、止损阈值、候选筛选、成交模型或门槛；任何修改都会重置前瞻计时。

最新全链重算的当前结果为 11 个 `observe`、3 个 `insufficient_evidence`、0 Champion/Challenger，仍为 paper-only。八份 observed tail 均为 20 日、18 个源文档日、14 个完整候选日；六份 records 合并为 147 个共同 entry path。该数字以结果文档和内容哈希报告为准。
## Current verification override (2026-07-16)

## Current Formal Candidate-Chain Override (2026-07-19)

- The formal Paper/Shadow activity candidate source is now `direction_linkage_v2`: verified `direction_score_shadow` candidates flow into the fail-closed Linkage V2 selector and then the SHA-bound sector-cluster quota. This is an activity-source replacement, not production promotion of the V2 scoring policy.
- Direction input SHA: `44c776aec07052f9152ba634b7b9ac739f926704bcb66c14f936562134867152`. Sector history root: `data_cache/sector_history_v20260717`, with 90 industry histories available through 2026-07-16. Cluster-map SHA: `06cd454ce47cdb690a0a1c3f67a699528ca93e8e710935ae81be501a0fa4c77b`.
- Fresh isolated report: `test_output/formal_replacement_2026-07-16-with-history-stockdb/unified_report.json`, SHA `6ebca8c3db369a357fac1f9d09e0f30223e58e0e6ba79988ea4afe1d5c701e73`; it reports `active_for_paper_research` with 30 selected stocks. V2 coverage is 1,001/1,029 relations and 540/554 unique stocks; maximum cluster ratio is `0.333333`, with zero unmapped sectors.
- This status does not change the A/B/C promotion result: historical evidence remains insufficient, `strict_pit_eligible=false`, Legacy remains the frozen scoring baseline, and no broker, order, position, or live instruction path is present.
- Historical formal-chain verification snapshot: full pytest `3137 passed, 19 deselected in 35.13s`; replacement-chain regression `287 passed in 6.78s`; `compileall` and `git diff --check` pass. Strict parse is `261 JSON + 1 JSONL + 12 lines`; paper-only artifacts pass; protected-field scan is `tracked_added=0, untracked_production=0`; formal machine acceptance passes. Its Review A and Review B are historical and not the current closing credential.

The A4/B3 pair closed the earlier Phase 11 and is historical evidence only. It is not a completion credential for the 2026-07-17 score-credibility extension. The first new pair returned A=`0/2/2`, B=`0/7/1`; the second returned A2=`0/1/0`, B2=`0/2/0`; the third returned C=`0/2/0`, D=`0/1/0`. None cleared the gate. The third pair's findings were fixed with a `3 failed` RED to `3 passed` GREEN before requesting a fourth pair: non-labelable dates now advance scoring/rank state, the gate requires exactly 1d/3d/5d with positive train and test folds across every horizon, and fold comparisons cover both train and test against same-horizon production baselines.

The current verification supersedes older test-count lines above: the Path A v3 file regression is `25 passed`, the affected paper-only/Path A regression is `197 passed`, and full pytest is `2948 passed, 19 deselected in 16.63s`, with zero failures. Earlier results and review pairs are historical evidence; their findings are fixed, and a new independent pair is required.

The historical two-week paper/shadow snapshot is `2026-06-29` through `2026-07-10`: entry-bars manifest SHA `192ce3e2bb764029cedb7f5a8db09e287225bf94034078cc593dc2e4a0cbc29f`, 143 requested sessions, 121 complete, 22 invalid; both 1m and 5m have 193 candidates, 119 complete, 74 invalid. `2026-07-04` is a non-trading-day input; its 20 candidate rows are invalid and excluded from trading-date coverage. Entry records are 1m `4/3` and 5m `3/3` record/causal-valid; v26 is the only hit and both 2%/3% profit record sets are zero. All eight audits are `insufficient_sample` at 10 observed dates versus 20 required. These identities are superseded snapshots, not the current canonical chain.

The historical temporary records manifest SHA is `07c378b33a419261bbc8e69c873041b4783b4c519348024143d3c2b6c31f1ac6`. The corresponding historical 5m audit SHAs are entry `481847e0f6632f1003fc5438a1e39c85109c6bfae643378e563bf4991087cc0f`, profit 2% `f3f40748e2f651b245b9fa346070178aed69d01610f90c99008d63326b38e62b`, profit 3% `8c4e209cf39324a83c41e4391cedcd8b3cd7ef544dc23795d590fa408dbe8836`, and stop `91b6eff1eabed5b208cebe72ad9401f843c192e5c3d552454f27e425c2355d86`.

The historical temporary decision SHA is `5af98e818170c767d3c388f71eb4b8d0847f52faa4dba9422ea823017eb42123`: 14 `insufficient_evidence`, 0 observe, 0 Champion, 0 Challenger, and `live_trading_ready=false`. A4/B3 remain the historical temporary-chain reviewers, not the score-extension closing pair. This remains paper/shadow research only; no broker or executable instruction path is used.

## Sector-score credibility extension (2026-07-17)

- The architecture remains unchanged. The extension only corrects snapshot semantics, connects previously neutral short-horizon inputs, aligns trend windows, makes tied ranking explicit, and adds an isolated PIT validation path for base, trend, and burst sector scores.
- PIT features are recomputed from the actual dated inputs. Future 1/3/5-session returns are labels only; they cannot enter features, ranking, candidate construction, or gate selection. The latest 20 label-eligible sessions are an already observed evaluation tail with labels unmaterialized; `blind=false`, `eligible_for_oos_claim=false`, and the preceding five sessions are purged from development for the maximum 5-day horizon.
- Candidate score weights are shadow-only. Promotion requires predeclared aggregate and rolling-fold stability gates, gap-sensitive train metrics, all-horizon non-negative evidence, same-horizon production-baseline non-degradation, fold-level non-degradation, and tie/constant/cap health checks; a failed candidate cannot alter production weights or protected stock-score fields.
- Every future-return label uses the shared source calendar target date. A sector missing that target date is excluded from the cross-section rather than silently advancing by its own row index.
- Scores and ranks are computed from the full as-of-visible sector cross-section before future-label availability is checked. Missing future labels can remove only that sector's labeled sample; they cannot alter another sector's as-of score or rank.
- The current Path A v3 self-describing strict JSON report SHA is `b321b00fe2c5e5c0dbbfda034f46c11ff9094ea587cbd6e2d12fc943281091ab`; `5e4df313...f7a5c6` is its pre-identity-annotation content SHA. It contains five shadow candidates; technical v3 uses 72 eligible dates / 6,480 samples after excluding 1,800 incomplete-window rows and builds walk-forward folds from those eligible dates. Evidence is a retrospective record-date slice over an unversioned current sector universe, so `strict_pit_eligible=false`. The final 20 dates remain an observed tail, not blind/OOS; `promotion_allowed=false` and `live_trading_ready=false` remain mandatory.

## Canonical session-identity refresh (2026-07-17)

- Fresh candidate streaming found 148 stale `complete_session=false` classifications per timeframe after the StockDB alternate-session contract became authoritative. No compatibility bypass was added: only the existing candidate→records→audits→decision chain was re-derived; PIT and unrelated data layers were not recalculated.
- The caller-bound entry-bars manifest SHA is `884b40b60bee79da40e7402c3c5eb706447df67f6ad00d582b29013af9b13ec1` for 182 sessions (147 complete / 35 invalid). Current candidate manifests are 1m `d085d410bccb629565202af6134242a9611b2df7ed6b3c039b4636cfdde8b4fc` and 5m `b5338934e24cf4b2d11d71e7665e560d62adda54e8a14ed977d940859f8cb08f`, each with 160 documents and 1,409 complete / 1,393 invalid candidates.
- Current records counts/causal-valid counts are entry 1m `193/161`, entry 5m `198/152`, profit 1m `64/55` for both thresholds, and profit 5m `65/47` for both thresholds. Durable records manifest SHA is `21db14443d2ebd30e596887b3aee1590a8058c0fffd2e174bc18e039651bcfa6`; all eight audits report tail `20`, source `18`, complete `14`; final decision SHA is `7c8cfa3500495ee095c5952d36f6fcea472891ea9e6c8dd9e78e68b66585e3f9`, with 11/3/0 and live false unchanged.
- The historical canonical root snapshot strictly parsed as `172 JSON + 2 JSONL + 38,778 lines`; it is retained as provenance. The superseded code suite was `3137 passed, 19 deselected`; the superseded formal-candidate strict inventory was `261 JSON + 1 JSONL + 12 lines`.

## Historical Verification Snapshot (2026-07-19; superseded)

- The current code suite is `3253 passed, 19 deselected in 236.06s`; the old-relevance/Linkage regression remains `309 passed`, while current ML/archive/experiment/inventory coverage is `82 passed`. `compileall`, `git diff --check`, protected-field scanning, and strict JSON/JSONL parsing pass. The current strict inventory parsed 379 JSON files and 1 JSONL file with 12 lines; one pre-existing truncated `test_output/theme_sector_radar.json` is explicitly excluded and was not overwritten. The direction bridge now records legacy relevance for comparison only and leaves active association to Linkage V2. The ML artifact inventory binds 68 files: 63 immutable legacy JSON files are `superseded_legacy`, 3 model binaries are hash-bound, and the 2 current cycle JSON files contain inline `live_trading_allowed=false`.

Historical predictor-safety snapshot, superseded by the current artifact-contract result below: full pytest
`3224 passed, 19 deselected in 249.86s`; ML/archive focused regression remains
`53 passed`, strict inventory remains `378 JSON + 1 JSONL/12 lines`, ML-scope
paper-only remains `51/51`, and protected exact writes remain `0`.
- The latest artifact-contract continuation supersedes the earlier ML timing and artifact
identities: full pytest is `3253 passed, 19 deselected in 236.06s`, focused ML coverage is
`82 passed`, readiness SHA is `80ea9944c6e2fea4978054fa3f1033c722a4172e559dc2b248b053105fd9ba87`,
cycle SHA is `4d910f9657cb31aa285066deba324e7732400b8dd72ae5372eacbcdbc2aaa6af`,
config file SHA is `949101a2c1c7ee69bf235120fb11f720efeb448eccd27df591b2e14f778096cf`,
effective experiment SHA is `a315047c2783f174b068999733f27aa8d86fce38f292b3a814b5536f7d6a7b7d`,
and artifact-inventory SHA is `0655da8b5be1b71c1000a967a184537183f235bf490680cf2459d10274437ff1`.
Observed feature and label sources must now replay exactly from the verified archive;
readiness independently re-runs that verifier. Archive and inventory safety flags are
fail-closed, registry/model files are paired, all known ML test-output roots are covered,
and synthetic bundles carry a parameter-bound experiment contract at save, load, and
prediction. Missing safety fields on immutable historical archive files only downgrade
their strict-evidence eligibility; those files are not rewritten.
Readiness remains blocked at one historical candidate snapshot, zero prospective dates,
zero verified training dates, and zero mature five-day labels; no observed model exists.
- Historical interrupted-run snapshot, superseded by the artifact-inventory result above: full pytest
`3224 passed, 19 deselected in 250.84s`; observed-cycle readiness SHA is
`fae2a73cad95ef31f6ba50c89951c38af6cb77c13f09150fd5cf1c869857e527` and cycle report
SHA is `2fab11135deed739ea19622d1bdad082c765acc90c9b612afacb03274bc46497`.
The experiment file SHA is `b21f89c4b41f7ac903b412a0d1b245505a79b5adaad472601bb49a04cae92020`;
the effective experiment SHA is `a4d6e3c8fc705cc2363de0d419f14e752791403e8aca1a1613f6d44f6684e972`.
Readiness remains blocked at 1 candidate snapshot, 0 prospective dates, 0 verified training
dates and 0 mature 5-day labels; no observed model directory exists.
- The canonical nonstationary identities remain the fourth-round values: selection manifest `9e297b2aa8914f8bded8a2eb507f91b7752bffe065dd036cb248fb25720fa066`, decision SHA `8a0c2f202032991a3e11b55205a3ce2dc6c277fe85e25b21577703027535df3b`, long-history event SHA `e92a2fd232cddb2df0abb14b0e8e374ad7a2423f2e1840df6a02d46506ab979a`. This concept-data stage did not recalculate canonical records, audits, or final decision.
- Concept data is an independent paper/shadow path: StockDB native board keys -> immutable date-bound membership snapshot -> AkShare concept history -> `concept_direction_score_shadow.v1` -> concept member bridge. It never enters the formal industry candidate chain and cannot write `quant_score`, `final_score`, `v2_score`, `selection_score`, or `selection_score_adjusted`.
- A read-only StockDB probe found 978 concept keys; 977 were usable A-share member boards and 1 ETF-only board was excluded with a recorded source audit. Historical dates without an exact membership snapshot remain fail-closed. No broker or executable instruction path is present.

## Current ML Shadow Verification Override (2026-07-20)

Fresh full pytest is `3258 passed, 19 deselected in 246.70s`; the ML/archive/experiment/
inventory suite is `87 passed in 34.94s`; and the archive-focused suite is `20 passed in
28.27s`. The observed cycle remains fail-closed at `readiness_gate_blocked_training`,
so no observed model or live path exists.

Current readiness SHA is
`7d350962f51239869c66d667c12e932e76e0ad0cfd9a82d59a4fe3d9211797a6`; cycle report SHA
is `91443a9d7b42a47857e5b2827b946f3395f82bbd009e07474b99e25953e52753`; artifact
inventory SHA is `c6d6f22c3412aaa43c32a30a8a4230d31c6b931f1c48d2c1e54487ccb1ec6e53`; and
archive evidence SHA is `2c3f7058826e19a7d311942598435ad9e83b82692d2e863ca5c0e72eb449ffe2`.

The inventory contains 69 artifacts (66 JSON and 3 model binaries), including 64
immutable legacy JSON artifacts and 2 current cycle JSON artifacts. Strict parsing is
`379 JSON + 1 JSONL/12 lines`; compileall, diff-check, expected-SHA, and protected-field
checks pass. The two fresh independent read-only reviews remain the closing gate.
