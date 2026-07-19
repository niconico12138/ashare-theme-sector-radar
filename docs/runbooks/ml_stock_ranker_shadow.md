# ML Stock Ranker Shadow Runbook

## 边界

所有命令只生成 paper/shadow research artifacts。不要把 `ml_quant_score_shadow` 写回正式 `quant_score`、`final_score` 或候选排序。

可选依赖安装：

```powershell
python -m pip install -e ".[ml]"
```

依赖缺失时 CLI 会写 unavailable/readiness，不会使用手写模型降级。
预测日期必须位于 registry 的 `model_available_from` 至其后 45 个日历日内；`model_available_from` 不得早于最后训练标签的实际成熟日。更早日期会因潜在未来信息泄漏 fail closed；超过 45 日会因模型过期 fail closed，必须注册新版本。`synthetic_fixture` 模型默认被普通 CLI 拒绝。

## 输入契约

Feature source 使用 `ml-stock-feature-source-v1`，每个 snapshot 必须包含：

```text
as_of_date
candidates
bars_by_code
```

Label source 使用 `ml-stock-label-source-v1`，必须与 feature source 分文件：

```text
stock_price_rows
sector_price_rows
trading_dates
```

Feature source 不得包含未来收益或标签字段。
标签构建器保留完整 as-of 候选身份，并逐 horizon 记录实际目标交易日；缺标签不会在排序前删除候选。训练只使用成熟 5 日标签，评估覆盖率以完整预测池为分母。

## 构建数据集

```powershell
python scripts/build_ml_stock_dataset.py `
  --feature-source reports/paper_shadow/ml_stock_ranker/inputs/feature_source.json `
  --label-source reports/paper_shadow/ml_stock_ranker/inputs/label_source.json `
  --output reports/paper_shadow/ml_stock_ranker/dataset/dataset.json
```

## 训练 Shadow 模型

```powershell
python scripts/train_ml_stock_ranker_shadow.py `
  --dataset reports/paper_shadow/ml_stock_ranker/dataset/dataset.json `
  --model-dir models/paper_shadow/stock_ranker_lgbm_v1 `
  --report reports/paper_shadow/ml_stock_ranker/training/training_report.json `
  --walk-forward-output reports/paper_shadow/ml_stock_ranker/training/walk_forward_predictions.json `
  --model-version stock_ranker_lgbm_v1 `
  --min-train-dates 60 `
  --test-dates 20 `
  --purge-dates 5 `
  --n-estimators 80
```

模型目录已存在时命令拒绝覆盖。需要新训练时使用新的 model version 和新目录。

## 每日 Shadow 推理

```powershell
python scripts/run_ml_stock_shadow.py `
  --model-dir models/paper_shadow/stock_ranker_lgbm_v1 `
  --expected-registry-sha256 <training-report-registry-sha256> `
  --feature-source reports/paper_shadow/ml_stock_ranker/inputs/feature_source.json `
  --as-of 2026-07-18 `
  --output reports/paper_shadow/ml_stock_ranker/predictions/2026-07-18.json
```

## 规则对比

Rule rows 只提供对照分和准入标志，不进入 ML 特征：

```powershell
python scripts/evaluate_rule_vs_ml_shadow.py `
  --predictions reports/paper_shadow/ml_stock_ranker/training/walk_forward_predictions.json `
  --dataset reports/paper_shadow/ml_stock_ranker/dataset/dataset.json `
  --rule-rows reports/paper_shadow/ml_stock_ranker/evaluation/rule_rows.json `
  --output reports/paper_shadow/ml_stock_ranker/evaluation/comparison.json `
  --top-k 10 20 30
```

Stage 1 结果固定为 `architecture_only_shadow`，不会产生 eligible promotion。

## 数据 readiness

```powershell
python scripts/audit_ml_stock_data_readiness.py
```

当前输出：`reports/paper_shadow/ml_stock_ranker/data_readiness_2026-07-18.json`。

## 合成技术 fixture

默认 fixture 已生成。重复验证时必须使用新的输出目录，避免覆盖：

```powershell
python scripts/run_ml_stock_synthetic_fixture.py `
  --anchor-date 2026-07-18 `
  --output-root reports/paper_shadow/ml_stock_ranker/synthetic_fixture_calendar_v2_rerun `
  --model-dir models/paper_shadow/stock_ranker_lgbm_v1_synthetic_fixture_calendar_v2_rerun
```

Fixture 只验证软件链，不是回测证据。

## Unified 后续接入

主流程只应调用以下公共 API：

```python
from theme_sector_radar.ml.feature_builder import build_feature_row
from theme_sector_radar.ml.predictor import predict_shadow
from theme_sector_radar.ml.registry import load_model_bundle
```

`load_model_bundle()` 必须接收训练报告或受信 manifest 中记录的
`expected_registry_sha256`；不能用 registry 文件修改后的自报 SHA 解除 fixture
身份或安全信封。

对候选建立只读副本后生成独立报告和 SHA。不要修改正式股票对象，也不要把 ML 分数并入任何受保护评分字段。
