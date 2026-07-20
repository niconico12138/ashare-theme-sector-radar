# 行业板块 ML Shadow 四十轮执行记录

## 状态

- [x] 固定纸面/PIT/不交易边界。
- [x] 绑定真实行业历史物理源 manifest 和 dataset identity。
- [x] 保留已有 round1/2，不重做已完成实验。
- [x] 完成 round3 至 round10 独立实验。
- [x] 只读复用 round1-round10，完成 round11-round20 增量实验。
- [x] 每个新增轮次保存独立 round manifest；失败轮次保留 rejected/insufficient 证据。
- [x] 确认新增范围仅为 round21-round40，没有创建 round41 以后轮次。
- [x] 只读保留 round1-round20，新增 round21-round40。
- [x] 为 round21-round40 保存独立 round manifest、prediction、evaluation、model、registry 和 SHA。
- [x] 覆盖特征去冗余/组合、异常值/缺失值、seed/复杂度、gate、Top-k、成本、时间段和 regime 对照。
- [x] 确认没有创建 round41 以后轮次。
- [x] 行业聚焦测试、compileall、diff-check 通过。
- [x] 全量 pytest 已运行；记录非本支路 `risk_events` 未闭合导入导致的 92 个收集错误。
- [x] 每轮保存 prediction、evaluation、model binary、registry 和 SHA。
- [x] 完成 feature ablation、Rule Top3/5/7、ML Top3/5/7、gate、Rank IC、NDCG、胜率、换手和 regime 评估。
- [x] 添加 fixture/synthetic 拒绝、dataset source rebuild、禁写字段和安全 flag 测试。
- [ ] 取得严格 PIT prospective evidence。
- [ ] 取得独立时间段重复验证和成本敏感性分析。
- [ ] 讨论任何正式晋级。

## 轮次记录

round1/2 是此前完成并在本轮只读复用的方向分全特征和去 rule-direction 基线。round3 至 round8 是特征消融，round9 是低复杂度压力实验，round10 是更长 purge 的隔离压力实验。没有轮次接入正式 predictor、formal candidate selection、Linkage V2、broker 或 order/live 路径。

round11-round20 继续做 purge、测试窗口、最小训练窗口、rolling window 及两组特征组合敏感性。round11 被标签 horizon 门禁拒绝并保留失败 manifest；round12-round20 完成全部研究 artifact。round21-round40 全部完成；没有新增失败轮次。最终总轮次为 40，前 20 轮未覆盖或重算。

## 可复现命令

```text
python scripts/run_industry_sector_ml_shadow.py
pytest -q tests/theme_sector_radar/test_industry_sector_ml_shadow.py
python -m compileall -q theme_sector_radar/ml/industry_sector_shadow.py scripts/run_industry_sector_ml_shadow.py tests/theme_sector_radar/test_industry_sector_ml_shadow.py
git diff --check -- theme_sector_radar/ml/industry_sector_shadow.py scripts/run_industry_sector_ml_shadow.py tests/theme_sector_radar/test_industry_sector_ml_shadow.py
```

CLI 在已有根目录上只复用完整 round artifact；缺失轮次才执行训练。若 source manifest、dataset identity、prediction/registry SHA 或禁写字段不满足约束，应 fail closed。

## 后续优先级

1. 先用 fresh strict-PIT prospective window 重复 round4/7/9 的特征组合。
2. 对 round10 设计固定样本量的长 purge 比较，避免 folds 数变化造成误读。
3. 明确市场波动特征的聚合定义，并重新做 source-bound dataset identity。
4. 补充置信区间、时间段稳定性和换手/成本敏感性，但仍保持 paper-only。
