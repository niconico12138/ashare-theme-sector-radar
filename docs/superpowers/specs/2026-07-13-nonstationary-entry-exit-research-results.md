# 非平稳买入与退出研究结果

> 状态：第四轮 canonical 可信度整改、临时两周模拟链、ML Shadow 安全整改和两份全新独立只读复审已完成；最新全量为 `3258 passed, 19 deselected in 246.70s`，复审 A/B 均为 `Critical=0, Important=0, Minor=0`。正式 canonical 结论仍为 `11 observe / 3 insufficient / 0 promotion / live false`，临时两周决策仍为 `14 insufficient_evidence / 0 observe / 0 promotion / live false`；系统保持 paper/shadow-only。

## 最终结论

- 截至 2026-07-13，共评估 14 个 paper 候选：11 个 `observe`、3 个 `insufficient_evidence`。
- Champion 为 0，Challenger 为 0，实盘就绪候选为 0，`live_trading_ready=false`。
- v31/v32、2%/3% 动态止盈以及三类动态止损因子均不得进入执行层。
- 当前没有 2026-07-13 的有效市场环境标签，`current_regime` 为 `insufficient`；系统不会回退使用旧环境。
- 当前最后 20 日是已被多轮迭代观察过的 `observed_evaluation_tail`，不是盲测 holdout，不得作为样本外证明。
- 全程仅限 paper/shadow research，不连接券商，不生成实盘指令。

## 数据身份

- 原始候选源为 `agent_bridge_mds_1m_expanded_v2`，研究区间为 2026-01-30 至 2026-07-10。
- 可信 1m 根 manifest 为 `d085d410bccb629565202af6134242a9611b2df7ed6b3c039b4636cfdde8b4fc`。
- 可信 5m 根 manifest 为 `b5338934e24cf4b2d11d71e7665e560d62adda54e8a14ed977d940859f8cb08f`。
- 两个根各有 160 份候选文档、2,802 个候选，其中 1,409 个完整、1,393 个无效。这里的 1,409 是候选数量；每条有效路径的 K 线数量分别固定为 1m 241 根、5m 48 根。旧 `49c79e...422ad2d` / `2bf9cf...69176e` 是 StockDB session 语义更新前的历史身份。
- 5m 候选 bars 和盘中因子全部由同日完整 1m session 重聚合、重计算；不再读取原生 5m OHLC。
- 每个派生文档绑定调用方指定的源 1m root、源文件 SHA 和自身输出 SHA；canonical backfill → trusted rebuild → records → audits → decision 链的 JSON 读取拒绝 NaN/Infinity、数值溢出和重复 object key，写出使用 `allow_nan=False`、内容寻址归档和原子替换。selection validation 另由 `selection_source_identity` 严格扫描 `DATE/next_day_selection_validation.json`，manifest 绑定日期、相对路径、文件 SHA 与 manifest SHA；exploratory/frequency/probe 输出不具 canonical provenance 资格，不得作为该链输入。
- trusted rebuild 已禁止输入/输出同根，并比较所有非派生继承字段；六份 records 与八份 audit 均从当前 candidate root 和当前 selection manifest 独立重建完整记录 cohort。六份 cohort 记录数依次为 193、198、64、65、64、65，均为 `validated`；cohort 还使用真实 snapshot label 比较全部非路径源字段，并要求有效记录的 selection label 与候选源一致。profit 由调用方绑定 candidate/source/selection root 与精确 v31/v32，entry 上游绑定精确 v26/v31/v32。调用方 entry-bars manifest 覆盖 182 个 session（147 complete / 35 invalid），SHA 为 `884b40b60bee79da40e7402c3c5eb706447df67f6ad00d582b29013af9b13ec1`。
- realtime 信号可见性同时核对 snapshot label 与行情源 `generated_at`；源时间缺失、无效、早于收盘或日期不等于 `as_of` 时均保持隐藏。

## 因果样本

| 用途 | 粒度 | 总记录 | causal-valid | 无效 |
|---|---:|---:|---:|---:|
| entry，v26/v31/v32 | 1m | 193 | 161 | 32 |
| entry，v26/v31/v32 | 5m | 198 | 152 | 46 |
| profit 2%，v31/v32 | 1m | 64 | 55 | 9 |
| profit 2%，v31/v32 | 5m | 65 | 47 | 18 |
| profit 3%，v31/v32 | 1m | 64 | 55 | 9 |
| profit 3%，v31/v32 | 5m | 65 | 47 | 18 |

- 信号只在信号日收盘后确认，模拟 entry 为下一真实交易日第一根完整 K 线开盘。
- 所有有效 1m/5m 路径分别为 241/48 根；每条有效 5m record 还绑定 241 根完整源 1m session 及其 SHA，验证器重新聚合后逐值比较 5m bars，并从 bars 重算 MFE/MAE、退出触发、模拟退出收益和数据质量。无效记录不保留 bars、路径 SHA、收益、路径统计或 `selection_forward_return_pct`，六份 records 的 invalid 标签残留数均为 0。
- `as_of` 后 entry 为 0；跨粒度重叠样本的开盘最大差为 0。
- 实际日历窗口为全历史 106 日、观察尾部 20 日、观察尾部前训练区 86 日，因此 `recent_120` 必须保持 `insufficient_sample`。
- 观察尾部 20 日中有 18 日存在源候选文档、14 日存在至少一个完整 session 候选，源文档/完整候选日期覆盖率分别为 90%/70%；2026-07-01 是候选数为 0 的物理文档日。对应门槛仍强制为 `insufficient`，recent60 与 86 日训练区的两类日期覆盖均为 100%。

## 买入结果

下表为下一交易日开盘至收盘、扣除 0.1% 往返摩擦后的平均收益；括号内为有效选中数。

| 粒度 | 版本 | recent60 | 86 日训练区 | 20 日观察尾部 | 正向有效 fold | 高相关因子对 |
|---|---|---:|---:|---:|---:|---:|
| 1m | v26 | +0.2607% (60) | -0.0670% (90) | +2.3545% (16) | 2/5 | 4 |
| 1m | v31 | +1.1078% (16) | +0.3507% (26) | +3.6403% (4，不足) | 4/5 | 5 |
| 1m | v32 | +0.5115% (15) | -0.1886% (21) | +3.6403% (4，不足) | 2/4 | 4 |
| 5m | v26 | +0.4025% (59) | -0.0559% (91) | +3.0427% (14) | 3/5 | 4 |
| 5m | v31 | +0.1874% (14) | -0.6766% (20) | +3.3305% (5，不足) | 2/4 | 5 |
| 5m | v32 | +0.5797% (12) | -0.4696% (18) | +3.6403% (4，不足) | 2/4 | 4 |

- 可信因子重建后，recent60 的方向比旧撤回报告改善，但 86 日训练区、观察尾部有效性、walk-forward 和因子冗余仍不稳定。
- 1m v31 是当前最值得继续观察的买入候选，但首个 fold 为 -1.4221%，观察尾部仅 4 条有效选中且日期覆盖不足，并有 5 对高相关因子，过拟合风险仍为 `high`。
- 1m v32 与两个 5m 候选在训练区或滚动段出现反转；v31/v32 继续冻结，不利用当前观察尾部调参。
- 四个 v31/v32 买入候选最终均为 `observe`，不是 paper Challenger。

## 动态止盈

2% 与 3% 峰值回撤候选在当前样本中结果完全相同，未形成可识别阈值差异。

| 粒度 | recent60 配对净差 | 86 日训练区 | 观察尾部 | 全历史 | 正向 fold | 尾部避免/恶化 |
|---|---:|---:|---:|---:|---:|---:|
| 1m | -0.1051% (19) | +0.0411% (29，不足) | +0.2499% (4) | +0.0664% (33) | 1/3 | 0/0 |
| 5m | -0.1219% (14) | +0.0818% (21，不足) | 0.0000% (5) | +0.0661% (26) | 1/3 | 0/0 |

- recent60 均弱于固定退出，三个 fold 仅一个为正；小幅全历史正差不能抵消当前窗口失败。
- 所有触发后的下一根连续 K 线 fill 均可用；当前观察尾部没有避免或恶化尾部损失。
- 四个动态止盈候选均为 `observe`；长期策略关联止盈路径仍为 `not_evaluated`。

## 动态止损

- 止损审计只允许 v31/v32 entry；v26-only 记录已从研究范围排除。
- 1m 有 33 个去重策略 entry、8 个固定 -3% 收盘确认触发；5m 有 26 个 entry、6 个触发。
- 1m 相对弱势仅有 4 个 eligible、3 个信号；5/15/30 bar 继续尾部率为 33.33%/66.67%/66.67%，且 66.67% 信号集中在同一日期。
- 1m 资金流恶化有 8 个 eligible、2 个信号，三个 horizon 的继续尾部率均为 50%，集中度仍失败。
- 5m 相对弱势只有 1 个信号，三个 horizon 均继续尾部；5m 资金流恶化为 0 信号。
- 当前缺少触发时点可见的板块分钟序列，板块同步走弱在 1m/5m 均明确为 `data_unavailable`，不得用静态映射补造。
- 最终只有 1m/5m 板块同步走弱和 5m 资金流恶化为 `insufficient_evidence`；其余三个止损候选为 `observe`，但均未通过集中度与样本门槛。

## 长期压力集

- 2024-2025 压力集保持 160,243 个股票日、19,389 个固定 -3% 收盘确认触发，其中 2024 年 11,605 个、2025 年 7,784 个。
- 请求研究宇宙为 338 只股票，原始 ZIP 中实际观测到 331 只；`code_count=331`，不再把请求数误写成实际覆盖数。
- 报告绑定 2 个股票 ZIP 和 476 个实际读取的板块 ZIP SHA；事件 JSONL SHA 与报告一致。
- 长期 reaudit 与 1m stop audit 只从已验证 JSONL 读取 19,389 个事件，并重新计算 summary、baseline 和 factors；内嵌事件及报告声明式指标不再受信。该压力集仍非策略关联，因此严格保持 `auxiliary_only`；5m 仍为 `not_evaluated`。
- stop 长历史统计参数固定为 5/15/30 bar、5 折和每因子至少 30 个信号，不接受报告自报参数覆盖；顶层报告与每条 JSONL 事件都必须具有严格 paper 身份。仅凭报告或事件自报策略关联不得晋级；未来若声称策略关联，必须由调用方提供独立 entry/calendar/cohort 外部锚，并逐条验证版本、规范 ISO signal/entry 日期、causal entry、entry path SHA 和 cadence，否则整份证据降级为 `auxiliary_only`。
- profit 长历史只有在调用方独立绑定交易日历路径/SHA、candidate root、源 1m root、selection root，并重新通过 causal record 与 v31/v32 cohort 校验后才可参与否决；本轮没有满足这些条件的长期路径，保持 `not_evaluated`。
- 长期报告 SHA 为 `40f8cf93813d8f1c783f0b96d38ac326f017a01bfe291777e160265891a9cf21`；事件 JSONL SHA 为 `e92a2fd232cddb2df0abb14b0e8e374ad7a2423f2e1840df6a02d46506ab979a`。
- 该压力集使用首分钟代理参考价、当前静态板块映射，不是历史策略真实 entry，只能作为辅助压力证据；5m 不复用 1m 长历史。

## Provenance 与验证

- 六份 records SHA 分别为：entry 1m `d06d1db48c9a2afe7d0562fe785870c6b4db45f5cd02eee81b5a33a29d341929`、entry 5m `a5cd8abd85d02c3e3001e75b744e47ed5687f033c235b509a2e92290e5260195`、profit 1m/2% `04cb6a23f6fb3e0026a57284d0359ccd860005e758b42ce1aa802a20f3c27ade`、profit 5m/2% `f89e3ced85b37fe2e3bd5ba285c121094a88e25ee0b45eac437e0bd226a0ba15`、profit 1m/3% `be1930d26ca92b99f459fecd98922e593dac1f5d38044ea623ed9dfa63d61080`、profit 5m/3% `c37bd9be8970010eab4ba964cd5934aa3e860114e9172a25d799ce331c0641fa`。
- 八份 audit SHA 分别为：entry 1m `56c95686c746b7953676292dc37fcf8928bec7d8c53ce3a46737ce4c6d575181`、entry 5m `7cc09b9e66e9d3c93872b7cd87f6372f182b0b4d4f334adcf12b050d9a52fce2`、profit 1m/2% `5320902873491caa26c0d05d0734fd19aa7ae13f62dc992d96c3fb27d1e30856`、profit 1m/3% `95bb1319d745eb44fd1596eb51c25790ee5bb94a11ffd0aeda8536eb451011de`、profit 5m/2% `f7da00a2fe1804e81b201d3a9f1ecc051c3e0f4cb571556207a3432194562a24`、profit 5m/3% `158197448d98f4da7297ff1144d4854da9f7b476a5e99094edd49ca9c918796e`、stop 1m `357b7cca209b14e46934cebb766cf75f4c37d2fe2b46022a6b3981290fecbfe0`、stop 5m `0252d3abff53148bda9cdd9e5548ccc3a27652ec69ec95d7b41af0e9819e549c`。
- records、八份审计报告和最终 decision 的路径与 SHA 已形成传递式闭环；final 强制精确 2+4+2 输入拓扑，并逐层复验 durable entry-bars manifest。durable final records manifest SHA 为 `21db14443d2ebd30e596887b3aee1590a8058c0fffd2e174bc18e039651bcfa6`，最终 decision SHA 为 `7c8cfa3500495ee095c5952d36f6fcea472891ea9e6c8dd9e78e68b66585e3f9`。
- 全链机器断言通过：selection manifest `9e297b2aa8914f8bded8a2eb507f91b7752bffe065dd036cb248fb25720fa066`、完整派生字段重算、record cohort、invalid 标签隔离、交易日历、跨粒度开盘、六 records 共同 entry-path manifest、106/86/20 窗口及日期覆盖、长期 JSONL 独立重算、八份 audit SHA、decision SHA 和 paper-only 标志全部一致。六 records 合并得到 147 个有效 entry key，跨版本、2%/3% 阈值和 1m/5m 粒度均无底层 1m path 冲突。
- 原 12 模块历史失败集现为 `404 passed in 5.09s`；第四轮研究聚焦 29 文件回归为 `418 passed in 5.70s`；unified bridge 完整文件 fresh 重跑为 `191 passed in 3.42s`；九个直接受影响完整测试文件为 `193 passed in 2.77s`。
- hermetic 全量回归现为 `3003 passed, 19 deselected in 17.95s`，0 failed。上一轮 `2996 passed, 19 deselected in 18.27s` 及更早数字仅为历史整改凭证；19 个 deselected 节点均为显式 `network` 合同。
- Mencius/Pauli 及其后的未清零双审均为历史失败凭证，不是“最新终审”。本轮最新整改来自 Plato/Euclid 的 execution 语义变体和 current PIT 本体身份发现：组合式完整执行结构检测以 `10 failed, 5 passed` RED 复现，修复后目标 `15 passed`、受影响四文件 `197 passed`；current v3 与三份历史 PIT 均已自描述且指针一致。Phase 12 仍等待下一对全新独立只读终审同时清零。
- 普通全量验收未发起 AkShare/代理访问且无 warning。显式网络合同仍可由调用方使用 `-m network` 单独运行，但不属于本轮 hermetic paper/shadow 验收。
- Phase 11 历史 closing pair：A4=`Critical=0, Important=0, Minor=0`；B3=`Critical=0, Important=0, Minor=1`。两份复审均未写入 canonical 产物，且不作为后续评分扩展凭证。
- 历史共享产物根严格解析库存为 172 个 JSON、2 个 JSONL、38,778 行 JSONL；PIT 库存为 4 个严格 JSON。canonical closing identities 未重算；该历史代码快照为 `3003 passed, 19 deselected in 17.95s`，0 failed。

## 固定后续路线

1. 每日继续生成 next-session causal records，保持 v26/v31/v32 与 2%/3% 退出参数冻结。
2. 从规则不可变冻结后，日历层面至少新增 34 个交易日：前 14 日补足 120 日训练区，后 20 日形成真正未观察的前瞻 holdout；期间不得查看结果后调参。
3. 止损因子自然积累到每因子至少 30 个分散信号，并同时约束日期、股票和板块集中度；不放宽阈值制造样本。
4. 补充触发时点 point-in-time 板块分钟序列和历史成分关系后，再测试板块同步走弱。
5. 34 日只是日历下限。当前 106 日中有 104 日存在源文档、100 日有完整候选；仍须回补缺失日期或继续滚动采集，直到 120 日训练区与 20 日前瞻 holdout 都达到 100% 源文档和完整候选日期覆盖。
6. 始终采用 recent60 主导、recent120 确认、冻结后的 20 日前瞻 holdout、长期尾部否决；不做全历史等权选优，也不因当前观察尾部反转追参数。
7. 只有全部硬门槛通过的预声明候选才能成为 paper Challenger；在此之前不接券商、不生成实盘指令。

本报告只描述 paper/shadow research，不构成投资建议或交易指令。
## Current verification override (2026-07-16)

## Current ML Shadow Verification Override (2026-07-20)

The latest full pytest is `3258 passed, 19 deselected in 246.70s`; the ML/archive/
experiment/inventory focused suite is `87 passed in 34.94s`, and the archive-focused suite
is `20 passed in 28.27s`. Compileall, diff-check, strict parsing (`379 JSON + 1 JSONL/12
lines`), protected-field scanning, inventory expected-SHA verification, and paper-only
machine acceptance pass.

The observed ML cycle remains blocked at `readiness_gate_blocked_training`. Current
readiness SHA is `7d350962f51239869c66d667c12e932e76e0ad0cfd9a82d59a4fe3d9211797a6`;
cycle report SHA is `91443a9d7b42a47857e5b2827b946f3395f82bbd009e07474b99e25953e52753`;
artifact inventory SHA is `c6d6f22c3412aaa43c32a30a8a4230d31c6b931f1c48d2c1e54487ccb1ec6e53`;
and archive evidence SHA is `2c3f7058826e19a7d311942598435ad9e83b82692d2e863ca5c0e72eb449ffe2`.

The inventory binds 69 physical ML artifacts (66 JSON and 3 model binaries): 64 are
immutable `superseded_legacy` JSON evidence and 2 current cycle JSON artifacts are
eligible as current research evidence. Real-data readiness remains below the 60-date
gate, with no observed model, broker connection, order instruction, or protected score
write. Two fresh independent read-only reviews remain the closing gate.

## Current Formal Candidate-Chain Results (2026-07-19)

All older `3003 passed` and pre-chain SHA lines later in this file are historical provenance. The current values are the ones in this section.

- `direction_score_shadow -> linkage_v2_shadow -> formal_candidate_selection` is active for Paper/Shadow candidate generation. Legacy remains the frozen comparison and scoring baseline; this activation must not be read as a promotion or live-trading decision.
- Direction input SHA: `44c776aec07052f9152ba634b7b9ac739f926704bcb66c14f936562134867152`; cluster-map SHA: `06cd454ce47cdb690a0a1c3f67a699528ca93e8e710935ae81be501a0fa4c77b`; fresh unified report SHA: `6ebca8c3db369a357fac1f9d09e0f30223e58e0e6ba79988ea4afe1d5c701e73`.
- The 2026-07-16 run selected 30 rows from 1,029 candidate relations / 554 unique stocks. StockDB supplied bars through 2026-07-17; usable V2 coverage was 1,001 relations / 540 unique stocks. Selected rows were `partial` or `ok`, cluster concentration was `0.333333`, and no sector was unmapped.
- Historical formal-chain verification was green: `3137 passed, 19 deselected`; focused formal-chain regression `287 passed`; strict parse `261 JSON + 1 JSONL/12 lines`; paper-only and protected-field checks pass; formal machine acceptance passes. No executable order instruction was generated.
- The separate A/B/C promotion gate remains `promotion_status=insufficient_evidence`: one date, no versioned historical constituent universe, no strict PIT evidence, and no mature 3/5-day evidence. The correct claim is “formal Paper/Shadow activity chain active”, not “V2 promoted to production”.

Hilbert/Kant and A4/B3 are historical review evidence for earlier stages. The earlier score-extension pairs did not clear the gate, and neither did Leibniz=`0/5/0` plus Linnaeus=`0/3/2`. Their merged findings are now covered by the boundary-purge, observed-tail, durable provenance, production-fixture, paper-only alias, duplicate-sector, candidate-directory and content-addressed pytest evidence described below. A new independent pair is required.

The historical temporary paper/shadow snapshot supersedes only older temporary artifact lines: window `2026-06-29` to `2026-07-10`; entry-bars manifest SHA `192ce3e2bb764029cedb7f5a8db09e287225bf94034078cc593dc2e4a0cbc29f`; 143 requested / 121 complete / 22 invalid sessions; 1m and 5m each 193 candidates / 119 complete / 74 invalid. `2026-07-04` is a non-trading-day input; its 20 candidate rows are invalid and excluded from trading-date coverage. Entry records are 1m `4/3` and 5m `3/3` record/causal-valid, v26 only; both 2% and 3% profit record sets are zero. All eight audits are `insufficient_sample` with 10 observed dates versus 20 required. These values are not the current canonical chain.

Temporary records manifest SHA `07c378b33a419261bbc8e69c873041b4783b4c519348024143d3c2b6c31f1ac6`; current 5m audit SHAs are entry `481847e0f6632f1003fc5438a1e39c85109c6bfae643378e563bf4991087cc0f`, profit 2% `f3f40748e2f651b245b9fa346070178aed69d01610f90c99008d63326b38e62b`, profit 3% `8c4e209cf39324a83c41e4391cedcd8b3cd7ef544dc23795d590fa408dbe8836`, and stop `91b6eff1eabed5b208cebe72ad9401f843c192e5c3d552454f27e425c2355d86`. Temporary decision SHA `5af98e818170c767d3c388f71eb4b8d0847f52faa4dba9422ea823017eb42123`; decision is 14 `insufficient_evidence`, 0 observe, 0 Champion, 0 Challenger, `live_trading_ready=false`.

## 板块评分可信度扩展结果（2026-07-17）

- PIT 数据覆盖 90 个行业、117 个可标注交易日和 10,530 条样本；最大 5 日 horizon 边界 purge 移除 `2026-05-27` 至 `2026-06-02` 五个交易日，开发集为 92 日/8,280 条。最后 20 日从 `2026-06-03` 开始，仅为 `observed_evaluation_tail`，`blind=false`、`eligible_for_oos_claim=false`，前视违规为 0。
- 基础分 1/3/5 日 Rank IC 为 `0.009903/0.026663/0.008290`，并列率 `1.1353%`；趋势分为 `0.027589/0.027725/0.004748`，并列率 `38.1884%`、候选/生产 cap 率为 `5.3865%/5.3019%`；短线分为 `0.020600/0.054342/0.026289`，并列率 `78.3213%`。
- 连续基础分、趋势平衡和短线动量三份候选均未通过门禁，结论均为 `remain_shadow_development`。门禁同时消费边界 purge、purge/embargo 后训练折、各测试折、1/3/5 日整体指标、同期限生产基线，以及并列/常量/cap 健康度；当前 observed tail 不具 OOS 证明资格，也不允许用于调参或晋级。打分横截面只由当日可见数据决定，未来标签缺失只移除对应标签行，不改变其他行业当日分数与排名。未修改生产权重，也未修改候选股受保护评分字段。
- 当前 Path A v3 自描述严格 JSON SHA 为 `b321b00fe2c5e5c0dbbfda034f46c11ff9094ea587cbd6e2d12fc943281091ab`，身份注释前内容 SHA 为 `5e4df313...f7a5c6`；源/样本 manifest 为 `0d8e797c...9916bd` / `f62bb7b1...cb959`。五个候选均保持 shadow，技术 v3 为 72 日/6,480 合格样本，1,800 条不完整窗口样本被排除，walk-forward 按合格日期重建。该证据只属于当前未版本化板块宇宙上的记录日期回溯切片，`strict_pit_eligible=false`；current-pointer-updated archive/v2/intermediate SHA 为 `0997c880...4ae30` / `03d50287...2f2a6` / `f3e422f6...77ecb`。`promotion_allowed=false`、`live_trading_ready=false`。
- 历史代码验收为全量 `3003 passed, 19 deselected`；评分报告身份仍以本文前述 `b321b00f...1091ab` 为准。canonical candidate→records→audits→decision 链未因行业三层 shadow 研究重算，正式结论与 18/14 覆盖保持不变。

## 当前验证覆盖（2026-07-19）

- 当前代码全量为 `3253 passed, 19 deselected in 236.06s`；旧关联度降级、方向桥接、Linkage V2 和 ML 隔离回归仍为 `309 passed`，当前 ML/archive/experiment/inventory 聚焦为 `82 passed`；canonical records/audits/final 未重算。决策 SHA 仍为 `8a0c2f202032991a3e11b55205a3ce2dc6c277fe85e25b21577703027535df3b`，结果仍为 `11 observe / 3 insufficient_evidence / 0 Champion / 0 Challenger / live_trading_ready=false`。
- 概念支路新增严格契约：`stockdb_board_client.py`、`board_membership_snapshot.py`、`akshare_concept_history.py`、`concept_direction_shadow.py`、`concept_shadow_pipeline.py` 及独立 CLI。历史日没有精确成员快照时 fail-closed；当前日只读捕获，并以 write-once 快照保存。
- 最新 predictor 安全包络闭环后的全量 pytest 为 `3224 passed, 19 deselected in 249.86s`；observed-cycle readiness SHA 为 `1626fd00a296676e7b195c44a664d1c694601044487d1927c0b0092afcf92c57`，cycle report SHA 为 `192aaa6a7cd9421ee544bd458e033048a39192d70ee74562d4a493ad5493f388`。
- StockDB 实测概念键 `978` 个，可桥接 A 股成员的概念板块 `977` 个，1 个仅 ETF 板块被跳过并写入 source audit。该支路只生成 shadow 概念候选和成员 provenance，不进入正式行业候选链，也不改写五个受保护评分字段。
- 严格 JSON/JSONL 解析共检查 `362` 个文件并全部通过；唯一排除的是既存截断文件 `test_output/theme_sector_radar.json`，未被本轮覆盖。编译、diff、paper-only 和 protected-field 检查均通过。
- 本轮旧关联度改造及 ML 迭代后的严格扫描为 `379 JSON + 1 JSONL/12 lines`，唯一排除仍是既存截断文件 `test_output/theme_sector_radar.json`，未被本轮覆盖。编译、diff、ML 机器验收和 protected-field（0）检查均通过；68 份 ML 产物中 63 份旧 JSON 由 SHA 清单标记为 `superseded_legacy`，3 个 model.txt 已直绑 SHA，2 份当前周期 JSON 内嵌 live false；方向主链只保留 `legacy_relevance_score` 历史对照，不再应用 `relevance_score >= 0.60` 硬门槛。

## ML Shadow 配置绑定历史验收（2026-07-20，已被后续覆盖）

- 从中断点重新执行的全量 pytest 为 `3224 passed, 19 deselected in 250.84s`，零失败；ML/archive 聚焦回归为 `53 passed`。
- 历史观察周期 readiness SHA 为 `fae2a73cad95ef31f6ba50c89951c38af6cb77c13f09150fd5cf1c869857e527`，cycle report SHA 为 `2fab11135deed739ea19622d1bdad082c765acc90c9b612afacb03274bc46497`。配置文件 SHA 为 `b21f89c4b41f7ac903b412a0d1b245505a79b5adaad472601bb49a04cae92020`，effective experiment SHA 为 `a4d6e3c8fc705cc2363de0d419f14e752791403e8aca1a1613f6d44f6684e972`。
- 真实数据仍只有 1 个历史重建候选快照、0 个 prospective snapshot、0 个 verified training dates、0 个成熟 5 日标签，`model_training_ready=false`；训练被 readiness gate 阻断，没有创建 observed 模型目录。
- 严格 JSON/JSONL 为 `378 JSON + 1 JSONL/12 lines`，ML 产物身份清单为 `52/52`，受保护字段精确写入为 `0`；仍不接券商、不生成订单或实盘指令。

## ML Shadow 安全整改验收（2026-07-20）

- 全量 pytest 为 `3253 passed, 19 deselected in 236.06s`，ML/archive/experiment/inventory 聚焦为 `82 passed`。
- readiness SHA 为 `80ea9944c6e2fea4978054fa3f1033c722a4172e559dc2b248b053105fd9ba87`，cycle SHA 为 `4d910f9657cb31aa285066deba324e7732400b8dd72ae5372eacbcdbc2aaa6af`。配置文件 SHA 为 `949101a2c1c7ee69bf235120fb11f720efeb448eccd27df591b2e14f778096cf`，effective experiment SHA 为 `a315047c2783f174b068999733f27aa8d86fce38f292b3a814b5536f7d6a7b7d`。
- 旧产物身份清单 SHA 为 `af806e41861a98c8abc3da24b7a5e98ab06ba8c8aa4c6354b7368c28abe42b3c` 是历史快照；当前 inventory SHA 为 `0655da8b5be1b71c1000a967a184537183f235bf490680cf2459d10274437ff1`，63 份旧 JSON、3 个 model.txt 和 2 份当前周期 JSON 均有明确身份。
- 当前 artifact inventory SHA 为 `0655da8b5be1b71c1000a967a184537183f235bf490680cf2459d10274437ff1`；清单严格解析、直绑三个 `model.txt`，并提供 expected-SHA 只读复验入口。旧 synthetic registry/dataset 缺少安全字段或 experiment contract 时，当前 loader fail-closed 拒绝。
- 本轮新增并验证：同日 PIT 来源预注册门禁、observed feature source 的归档证据绑定、实际 LightGBM booster 参数交叉校验、verified registry 对象登记、公共 raw `RankerModel.predict()` 禁用，以及所有 ML paper/shadow 输出显式 `live_trading_allowed=false`。
- 真实数据仍为 1 个历史重建候选快照、0 个 prospective snapshot、0 个 verified training dates、0 个成熟 5 日标签；训练仍被 readiness gate 阻断，没有 observed 模型或晋级。
