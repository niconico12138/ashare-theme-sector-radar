# 个股机器学习评分并行支路第一轮结果

## 结论

ML Shadow 的独立 package、四个正式 CLI、真实数据 readiness 和合成端到端 fixture 已落地。现有正式评分、正式排序和候选池没有接入或改变。

真实历史目前不足以训练有意义的个股排序模型，因此本轮没有生成真实收益优越性结论，也没有用当前 2026-07-16 成分股倒灌历史。

## 真实数据 readiness

产物：`reports/paper_shadow/ml_stock_ranker/data_readiness_2026-07-18.json`

- SHA-256：`1d6589278147618028964e1552aa84b64ad2f0429b60275702e3c6bdb024b8d3`
- 候选快照：1 日，2026-07-16；
- 关系：1,029 条；唯一股票：554 只；
- 成熟个股 1 日收益标签：1 日，按 554 只 ML 候选交集覆盖 `536/554=96.75%`；候选池外 forward 代码 36 只不进入分母，3/5 日为 0 日；
- 成熟 5 日个股相对板块超额标签：0 日；
- 行业历史：90 文件、128 个日期，2026-01-05 至 2026-07-16；
- ML 依赖：ready，LightGBM 4.6.0；
- `model_training_ready=false`；
- `strict_pit_eligible=false`；
- 阻塞：候选日少于 60、成熟 5 日超额标签日少于 60、5 日覆盖低于 90%、历史候选/成分股宇宙没有可信验证者。

行业历史可用于板块上下文，但不能替代逐日个股候选身份，因此不会解除训练阻塞。

## 合成技术 fixture

模型：`models/paper_shadow/stock_ranker_lgbm_v1_synthetic_fixture_20260718_calendar_v2/`

报告：`reports/paper_shadow/ml_stock_ranker/synthetic_fixture_calendar_v2_2026-07-18/`

- Fixture manifest SHA：`445e94ddd9e2da41873e96dea6f9edf739a675641fc62c3f0d83033c36cac73b`；
- 16 个合成训练日期、96 条训练记录、17 日/102 行完整特征宇宙；
- 三个 expanding walk-forward folds，实际成熟训练日期数分别为 5/8/11；
- 每折 purge 5 日；
- 42 条 fold 预测，其中 6 条没有未来标签但仍保留在排序宇宙；
- 1/3/5 日标签覆盖率均为 85.71%，不再以内连接后的样本作为分母；
- model SHA：`26fcde60e807452628cc1b87b2e91e6ce9d7b0532fb7f61821b712ed6174fdb3`；
- registry SHA：`0f5e412616b6e5d03d252b833c33b75638a5209ba3def65ec5fe7a13a3271995`；
- feature schema SHA：`24d28267cec2cdf16c33dc85a5bde6d797a97572d7c09df0d585bbde8460f7a3`；
- 模型身份固定为 `synthetic_fixture`，普通预测入口要求外部 registry SHA 并默认拒绝 fixture；
- 合成数据锚点固定为 `2026-07-18`，行业集中度按完整入选池为 100%，不再随标签覆盖率下降；
- 状态 `architecture_only_shadow`，`promotion_allowed=false`。

这些数字只证明 train -> save -> load -> predict -> evaluate 技术链和契约可运行，不代表真实策略表现。

## 代码范围

- `theme_sector_radar/ml/`：schema、contract、feature、label、dataset、split、ranker、predictor、evaluation、registry、readiness 和 source adapter；
- `scripts/build_ml_stock_dataset.py`；
- `scripts/train_ml_stock_ranker_shadow.py`；
- `scripts/run_ml_stock_shadow.py`；
- `scripts/evaluate_rule_vs_ml_shadow.py`；
- `scripts/audit_ml_stock_data_readiness.py`；
- `scripts/run_ml_stock_synthetic_fixture.py`；
- `tests/theme_sector_radar/test_ml_stock_ranker_shadow.py`。

`sector_stock_bridge.py` 和正式评分公式未因本阶段修改；`unified_pipeline.py` 仅增加 Linkage V2 Shadow 的陈旧末根行情 fail-closed，不改变正式受保护评分。

## 验证

- ML 聚焦测试：`30 passed`；
- 本轮扩展跨路径聚焦测试：`184 passed`；
- 最新全量 pytest：`3120 passed, 19 deselected in 33.83s`；
- `compileall`、`git diff --check`、11 个 ML 严格 JSON 与 3 个 Linkage 严格 JSON、paper-only、保护字段 AST 写入扫描和机器验收全部通过；
- Fixture manifest 的 10 个物理文件 SHA 全部复算一致，bundle 以外部 registry SHA 和 34 个冻结特征重新加载成功；
- 新 ML 生产代码中的五个受保护字段写入为 0；
- 本阶段未修改三个冻结正式入口，也未提交代码。
- 两份终审发现的统一交易日历、成熟训练日期、标签/成熟日一致性、安全信封、registry 外部绑定、集中度、readiness 分母和 fixture 重现性问题已按 TDD 整改；旧终审不作通过凭证，replacement 复审由主流程统一组织。

## 下一轮

1. 从下一交易日起逐日持久化相同候选池的 as-of feature source；
2. 标签成熟后追加 1/3/5 日 label source，禁止提前写入；
3. 对板块成分股和候选宇宙做逐日版本化；
4. 累积至少 60 个有效候选日后首次真实 walk-forward；
5. 增加训练 feature 分布基线和 drift 指标；
6. 增加市场状态标签和 fold 稳定性硬门槛；
7. 只有所有预注册门槛完成后，才评估 ML 是否从 shadow 晋级。
