# 个股 ML Shadow 历史因子重建与 Round11-Round20 结果

## 范围与边界

本轮只新增个股 ML historical paper/shadow 支路，不重跑、不覆盖既有
`historical_iterations_v2_20260720` 的 round1-round10。旧 suite 仅按文件 SHA
`8d3c8ca05c9d59d4f0cea83a9fa3fc126fcb981745212dc01aa604ae9575a70`
只读引用。round11-round20 各自创建一个 research-only model registry；这些
registry 使用非正式 schema，正式 loader 必须拒绝。没有创建正式 predictor，
没有接入 broker、order、live 路径，也没有修改正式选股链。

所有新增 artifact 均为：

- `strict_pit_eligible=false`
- `eligible_for_oos_claim=false`
- `promotion_allowed=false`
- `live_trading_allowed=false`
- `formal_predictor_compatible=false`

## Source-Rebuild 盘点

输入仍是 v9 数据集逻辑 SHA
`7c45de04b255d4b47ed4011fee1594705c10c85416893c26e9415f57c4e46cef`，
共 99 个候选日、1,730 个候选行。重建逐一复验候选 manifest 中 99 个文件、
方向报告及其 90 个历史文件 SHA，并只接受精确 `as_of_date` 和精确板块名称。

结果如下：

| 项目 | 行数 | 覆盖率 | 结论 |
| --- | ---: | ---: | --- |
| 候选总行数 | 1,730 | 100% | 全部保留审计记录 |
| 方向源日期重叠 | 723 | 41.79% | 仅表示当天存在方向报告 |
| 方向精确同名观察 | 675 | 39.02% | 候选为 concept，方向为 industry，不可直接等同 |
| 方向 strict-PIT 可用 | 0 | 0% | universe 明确为当前文件集向历史投影 |
| Linkage V2 exact-as-of | 0 | 0% | 唯一报告日 2026-07-16，晚于候选末日 2026-07-03 |
| 方向和 Linkage 同时可用 | 0 | 0% | 禁止运行新增因子对照 |
| 排除行 | 1,730 | 100% | 每行均保留 `excluded_reason` |

排除原因计数：方向源无精确日期 1,007 行；日期存在但无精确板块名 48 行；
概念/行业字段语义不一致 675 行；方向 universe 非 PIT 1,730 行；Linkage V2
无精确日期源 1,730 行。观察值与 ML 可用值分开保存；不可用值为 `null`，
没有用 0、当前值、未来值或 fixture 填充。

因此本轮 source gate 为
`blocked_do_not_validate_direction_or_linkage_v2`，不能宣称方向分或 Linkage V2
已经验证。进入下一轮相关因子研究前，必须补齐带 capture timestamp 和 SHA 的
逐日股票-板块 membership，以及逐日 Linkage 股票/板块收益、成分权重、资金流、
质量组件输入；至少形成 60 个可训练日、purge 区间和独立测试日。

## 候选特征 Inventory

`feature_inventory.json` 先于实验生成，逐一重放 v9 manifest 中 99 个每日候选
文件及其 SHA，共审计 99 日、1,730 条 candidate `factor_snapshot`、40 个实际
factor id。嵌套 snapshot 的股票代码 1,730/1,730 与候选一致；嵌套 `as_of`
均为空，因此日期只从同一 content-bound candidate 文件的外层 `as_of` 继承，
artifact 明确记录 `snapshot_as_of_inherited_rows=1730`，不冒充内嵌 PIT 证据。

round11-round20 只选用下列 11 个已预注册技术/价格结构/波动/成交/板块上下文
原始字段。每个字段均成对加入 `_missing` indicator，缺失数值虽以 0 进入数值
矩阵，但 indicator 必为 1，不存在静默补 0。

| 原始特征 | finite 行 | 覆盖率 |
| --- | ---: | ---: |
| sector_support_score | 1,730 | 100.00% |
| close_strength_score / intraday_reversal_risk_score | 各 1,693 | 97.86% |
| 其余 8 个选用技术字段 | 各 1,700 | 98.27% |

禁止的 `quant_score/final_score/v2_score/selection_score/selection_score_adjusted/
relevance_score/legacy_relevance_score`、未来标签及非预注册字段均未进入 feature
matrix。模型按 `as_of_date` 分组做横截面 LambdaRank；标签只用于训练和评估。
`ml_quant_score_shadow` 与规则 baseline 并行保存，不写回候选或覆盖正式排序。

## Round11-Round20

后十轮只使用既有 `stability_core_v1` 技术特征或其子集。默认合约仍为按日期
expanding walk-forward、60 个训练日、5 日 purge、5 日测试、5 日标签期；
round11-round20 覆盖窗口、purge、seed、复杂度、特征消融和随机对照。每轮同时
报告 Top1/3/5，并做 0/10/25bps flat rebalance cost 压力切片。下表 Lift 顺序为
Top1/3/5，胜率顺序同样为 Top1/3/5；fold、regime 和成本明细保存在独立
`evaluation.json` 中。

| Round | 方法 | Top1/3/5 Lift | Rank IC | Top1/3/5 胜率 | 结论 |
| --- | --- | --- | ---: | --- | --- |
| 11 | purge=10 | 0.014093 / 0.002548 / 0.002434 | 0.020715 | 0.5862 / 0.5862 / 0.5517 | 保留为严格时间隔离证据；仅 29 个评估日 |
| 12 | 最少 70 训练日 | 0.019472 / 0.004456 / 0.002302 | 0.010480 | 0.5833 / 0.5000 / 0.5000 | 保留为训练窗压力证据；仅 24 个评估日 |
| 13 | rolling 60 | 0.000803 / -0.010282 / 0.000566 | 0.007390 | 0.4706 / 0.3824 / 0.5294 | Top3 明显转负，不采用为候选配置 |
| 14 | seed=20260721 | 0.011787 / 0.003088 / -0.000150 | -0.010209 | 0.5294 / 0.5000 / 0.5000 | 与基线一致，仅保留确定性 seed 证据 |
| 15 | 5 特征 compact | 0.013216 / 0.009732 / -0.000403 | -0.006561 | 0.5294 / 0.6176 / 0.4412 | Top5 转负，仅保留新窗口假设 |
| 16 | 同时去 sector support 与 reversal | 0.010986 / 0.013078 / 0.004617 | 0.045268 | 0.5294 / 0.5294 / 0.6176 | 三档 Lift 为正，保留为新窗口假设 |
| 17 | 去 range/drawdown/breakout | -0.005490 / -0.011459 / -0.015583 | -0.063486 | 0.5000 / 0.3824 / 0.3235 | 三档均负，淘汰；价格形态组不可轻易移除 |
| 18 | 去 volume/close quality | 0.010389 / 0.017660 / 0.000573 | 0.025959 | 0.5294 / 0.7353 / 0.5000 | 三档 Lift 为正，保留为新窗口假设 |
| 19 | 日内标签确定性轮转 | -0.003802 / -0.000828 / -0.004812 | 0.023847 | 0.5294 / 0.5294 / 0.4412 | null control 三档 Lift 均负，按设计淘汰 |
| 20 | 20 trees / 7 leaves | 0.004146 / 0.006455 / -0.005270 | -0.018884 | 0.5294 / 0.5000 / 0.4118 | 低复杂度不稳定，淘汰为候选配置 |

基线 Top1/3/5 Lift 为 `0.011787/0.003088/-0.000150`，Rank IC 为
`-0.010209`。部分新轮次点估计高于基线，但所有结果来自同一个 99 日历史重建
窗口，不能据此择优、晋级或声明 OOS。相对值得带到独立新窗口继续观察的是
round16 联合消融与 round18 去 volume/close-quality；round11/12 只应保留为
样本缩减后的隔离压力证据。

## Artifact 与验证

Source-rebuild 目录：
`reports/paper_shadow/ml_stock_ranker/historical_factor_source_rebuild_v2_20260720`。
v2 保留 v1 的覆盖结论，仅补强逐候选行的方向 report SHA、history manifest
SHA，以及 exact-as-of Linkage report SHA 约束；v1 保留为历史 artifact。

- `source_catalog.json` 文件 SHA：
  `bdaa77a8ba60e5f7542fa33550d3dbc9441df73ea46a566aec50bfb7f3808a96`
- `source_rebuilt_dataset.json` 文件 SHA：
  `23edc880b64900b054f7469da457b4c218e801e4d28b4c33b04cb4121757627a`
- `rebuild_report.json` 文件 SHA：
  `a0494c76fcf9402c2ff0d2322ba0ff816f7f931feddeaed5b5af2ad8f5e208ae`
- rebuild report 逻辑 SHA：
  `48776574dace898ab9f93824513a3e1aaa1dfd0f2f41f30e3b414189dc20897d`

Round11-round20 目录：
`reports/paper_shadow/ml_stock_ranker/historical_iterations_round11_20_v2_20260720`。
根目录先保存 `feature_inventory.json`，每轮目录恰好包含
`prediction.json/evaluation.json/model.txt/registry.json/manifest.json`，合计
10 份 prediction、10 份 evaluation、10 个实际 LightGBM model、10 份
research registry 和 10 份 SHA manifest。整个目录共 52 个文件。inventory
文件 SHA 为 `2f675141e4a05f82eb743b1c6bfe27ce5e89f20b7661096bceca4b18cdc3f870`，
逻辑 SHA 为 `d55c9c8e92825850af0729aa1293a3364a4c77ca6ac2dca3360ec770a342b1e4`；
suite 文件 SHA 为
`7a14e1175151e86f5fa6f4908eb07536d1425086e0ac84ebe36f6c8547e52e3a`。

新增及直接相关测试当前为 `15 passed in 4.09s`；全部 `test_ml_*.py` 为
`114 passed in 38.05s`。`python -m compileall -q theme_sector_radar scripts
tests/theme_sector_radar`、tracked diff-check、新增文件 whitespace check 均通过；
独立 artifact 审计确认 10 次正式 loader 拒绝、受保护字段精确键 0、true safety
flags 0。
