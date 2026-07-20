# 行业板块 ML Shadow 四十轮研究设计

## 目标与边界

本支路是行业板块的独立、纸面、研究型 ML Shadow。它不改变方向分正式主链，不调用 `formal_candidate_selection`，不进入 Linkage V2，不写入 `quant_score`、`final_score`、`v2_score`、`selection_score` 或 `selection_score_adjusted`，不连接 broker，不生成订单。

安全字段固定为 `false`：

- `strict_pit_eligible`
- `eligible_for_oos_claim`
- `promotion_allowed`
- `live_trading_allowed`
- `formal_predictor_compatible`

解释 Agent 只保留 `enabled=false`、`status=reserved_not_run` 接口，不参与训练、预测或评估。

## 数据与绑定

- 物理来源：`data_cache/sector_history/industry/*.json`。
- 仅接受 `sector_type=industry` 的历史文件；`fixture_only=true`、source 含 fixture/synthetic 的文件直接拒绝。
- 每个源文件保存绝对路径、记录数、source、抓取时间和物理 SHA-256。
- 数据集在每次校验时从 source manifest 重新 build，并比较 canonical dataset identity；不能只靠 artifact 内自报 SHA。
- 当前覆盖：90 个行业、9,720 个 feature rows、9,270 个有成熟标签 rows、103 个成熟日期，日期范围 `2026-02-02` 至 `2026-07-09`。
- 数据集 identity：`4fb067baad7ff654f0109d16adbf74fa1bc85414152029340726b4ff1cc7c5a3`。
- dataset.json 物理文件 SHA：`dc890b7dac69f8d7334ce30f43c73d92904b6f3fd480f84d15c908c8d79a9e3c`。

## 特征与标签

完整 profile 覆盖时序动量、波动/回撤、成交量/成交额变化、截面百分位、排名动量、市场收益/breadth/dispersion/volatility，以及只用于消融的 rule-direction 特征。标签是：

`future_5d_industry_return_minus_cross_sectional_median`

特征的 `as_of_date` 严格早于 `training_label_end_date`。训练采用日期分组 expanding walk-forward；默认 60 个训练日期、10 个测试日期、5 日 purge，另设 round10 的 10 日 purge 对照。评估只使用测试折的 prediction，并同时报告 Rule Top3/5/7、ML Top3/5/7、Rule gate + ML rank、raw/excess return、universe lift、Rank IC、NDCG、胜率、换手和 regime 分层。

## 预注册十轮

1. `round1_all_v1`：完整特征，检验全量信息是否优于方向分基线。
2. `round2_no_rule_direction_v1`：去除 rule-direction，检验 ML 是否保留独立增益。
3. `round3_time_series_only_v1`：只保留时序、波动、成交活跃度。
4. `round4_cross_section_only_v1`：只保留截面排名和排名动量。
5. `round5_rank_momentum_only_v1`：窄的排名动量特征集。
6. `round6_market_state_only_v1`：只保留市场状态，作为淘汰对照。
7. `round7_no_market_state_v1`：去除市场状态，检验行业自身特征。
8. `round8_compact_v1`：五个预注册核心特征，检验低维复现。
9. `round9_low_complexity_v1`：完整特征但 `n_estimators=20`、`num_leaves=7`。
10. `round10_long_purge_v1`：完整特征但 purge 延长到 10 日。

每轮拥有独立 prediction、evaluation、model.txt、registry.json 和 SHA 引用。已有 round1/2 只复用既有 artifact，不重新训练；round3 至 round10 为本轮新增实验。

## round11-round20 增量设计

前十轮 artifact 只读复用，不重跑、不覆盖。round11-round20 使用同一物理源 manifest 和 canonical dataset identity，每个新增轮次保存独立 `round_manifest.json`；训练或参数门禁失败时，只保存 `rejected/insufficient` manifest，不伪造 prediction、evaluation 或 model。

11. `round11_short_purge_v1`：purge=2，主动验证是否会被 5 日标签成熟度门禁拒绝。
12. `round12_long_purge15_v1`：purge=15，进一步扩大标签隔离。
13. `round13_short_test_window_v1`：每折 5 个测试日期，观察局部稳定性。
14. `round14_long_test_window_v1`：每折 15 个测试日期，观察聚合窗口敏感性。
15. `round15_min_train50_v1`：最少 50 个训练日期，检查较早样本起点。
16. `round16_min_train70_v1`：最少 70 个训练日期，检查更长训练历史。
17. `round17_rolling60_v1`：训练窗口最多保留最近 60 个日期。
18. `round18_rolling80_v1`：训练窗口最多保留最近 80 个日期。
19. `round19_time_series_cross_v1`：时序动量、风险形态与截面排名组合，不含市场状态和 rule-direction。
20. `round20_time_series_market_v1`：时序动量、风险形态与市场状态组合，不含截面排名和 rule-direction。

总轮次现扩展为 40；round1-round20 只读保留，新增 round21-round40。代码不注册、CLI 不创建 round41 以后轮次。

## round21-round40 增量设计

21. `round21_cross_section_market_v1`：截面排名与市场状态组合。
22. `round22_no_volume_amount_v1`：去成交量/成交额变化。
23. `round23_no_volatility_drawdown_v1`：去波动和回撤。
24. `round24_rule_direction_only_v1`：仅 rule-direction 特征的 ML 对照。
25. `round25_fixed_clip_stress_v1`：按固定语义边界裁剪异常值。
26. `round26_missing_zero_stress_v1`：按稳定 SHA 规则对约 10% 特征做零填充压力测试。
27. `round27_seed_variant_v1`：相邻确定性 seed。
28. `round28_low_complexity10_v1`：10 estimators、3 leaves。
29. `round29_high_complexity_v1`：80 estimators、31 leaves。
30. `round30_gate30_v1`：Rule gate=30。
31. `round31_gate70_v1`：Rule gate=70。
32. `round32_topk135_v1`：Top1/3/5。
33. `round33_topk5710_v1`：Top5/7/10。
34. `round34_cost10_v1`：10 bps turnover cost。
35. `round35_cost25_v1`：25 bps turnover cost。
36. `round36_early_window_v1`：早期评估区间。
37. `round37_late_window_v1`：晚期评估区间。
38. `round38_risk_on_v1`：risk-on regime。
39. `round39_risk_off_v1`：risk-off regime。
40. `round40_no_rule_low_complexity_v1`：去 rule-direction 的低复杂度组合。

每个新增轮次独立保存 `round_manifest.json`、prediction、evaluation、model、registry 和文件 SHA；失败或证据不足时保存 rejected/insufficient manifest。

## 结果判定规则

“采用”只表示保留为下一轮研究候选特征组合，不表示正式晋级；“淘汰”表示不再作为当前研究主假设。任何结果都不能绕过 false safety flags、严格 PIT 证据和 prospective OOS 门禁。
