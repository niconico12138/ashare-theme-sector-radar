# 行业板块独立时间外验证准备

## 当前状态

- 暂停新增 ML 轮次；不重复 round1-round40，不训练新模型。
- 真实行业源：90 个 `akshare/ths` 文件，物理记录覆盖 `2026-01-05` 至 `2026-07-16`。
- 现有 5 日标签成熟至 `2026-07-09`；更晚的 `2026-07-10` 至 `2026-07-16` 只有 feature/source bars，尚未形成可评估的完整后验标签。
- 当前 readiness：`blocked_pending_label_maturity`。
- OOS readiness、晋级、live 和 formal predictor flags 全部保持 `false`。

## 严格时间切分

固定为 signal-date 切分，标签 horizon 为 5 个交易日：

| 阶段 | signal window | 约束 |
|---|---|---|
| Train | 2026-02-02 至 2026-06-19 | 仅训练成熟标签 |
| Purge 1 | 2026-06-22 至 2026-06-26 | 与 train 标签成熟区间隔离 |
| Validation | 2026-06-29 至 2026-07-03 | 固定参数比较，不改 test |
| Purge 2 | 2026-07-06 至 2026-07-10 | 与 validation 标签成熟区间隔离 |
| Test/OOS candidate | 2026-07-13 至 2026-07-16 | 等待至少 5 个后续交易日成熟 |

在 test 标签未成熟前，不运行 test 评估、不声称 OOS、不训练事件增强模型。新增数据必须重新建立 source manifest 并比较 dataset identity。

## 候选配置

只允许预注册以下四个已审配置进入下一阶段比较：

- round28：`all_v1`，60 train dates，10 test dates，5 purge，10 estimators，3 leaves，learning rate 0.05，seed 20260720。
- round39：`all_v1`，60/10/5，40 estimators，15 leaves，learning rate 0.05，seed 20260720；risk-off 只作为分析切片，不改变模型特征。
- round16：`all_v1`，70/10/5，40 estimators，15 leaves，learning rate 0.05，seed 20260720。
- round18：`all_v1`，rolling max 80 train dates，10 test dates，5 purge，40 estimators，15 leaves，learning rate 0.05，seed 20260720。

所有候选固定 LambdaRank、relevance levels=5、min_child_samples=2、reg_lambda=1、deterministic=true、force_col_wise=true、n_jobs=1；Rule Top3/5/7、gate=50、gross/net excess、Rank IC、NDCG、胜率、换手、regime 和最大回撤必须统一报告。

## Event enhancement A/B

- A：候选配置的冻结非事件特征、5 日 excess label 和上述时间切分。
- B：A 加入已审核事件特征；本阶段不读取、不训练、不生成 B 输出。
- B 进入实验前必须有 event source manifest SHA、source registry、事件 `as_of` 时间、`effective_from <= as_of`、同一 train/validation/test folds 和同一成本口径。
- A/B 必须 paired 比较 gross/net excess、Rank IC、NDCG、换手、最大回撤和 regime 指标；不得自动晋级。
- 禁止事件输出改变正式选股链、Linkage V2、protected score、broker/order/live 路径。

## Artifact

准备报告：`reports/paper_shadow/industry_sector_ml_shadow/oos_readiness.json`。

该报告只记录 source inventory、dataset identity、切分、候选参数和 A/B contract；`event_source_read=false`、不含任何未审核事件数据。
