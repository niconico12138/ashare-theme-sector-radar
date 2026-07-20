# 个股 ML Prospective Comparison 结果

## 实现

- [prospective_comparison.py](E:/liaohua/01_projects/theme-sector-radar-dev/.worktrees/price-momentum-5m-1m/theme_sector_radar/ml/prospective_comparison.py)
- [run_ml_prospective_comparison.py](E:/liaohua/01_projects/theme-sector-radar-dev/.worktrees/price-momentum-5m-1m/scripts/run_ml_prospective_comparison.py)
- [test_ml_prospective_comparison.py](E:/liaohua/01_projects/theme-sector-radar-dev/.worktrees/price-momentum-5m-1m/tests/theme_sector_radar/test_ml_prospective_comparison.py)

runner 固定 comparison contract SHA：
`b0986ecce040596d030310a92a55ab22fe601105c1de371ce8d30a1fd83a0cc6`。

它消费已验证的 snapshot、成熟 labels 和外部 prediction evidence，不训练模型。prediction evidence 必须同时声明 model artifact、model parameters、feature contract 和 comparison contract SHA，并保持 paper-only 安全字段。

## 当前真实运行

输入 archive：`reports/paper_shadow/ml_stock_ranker/prospective_candidate_archive_v1`

当前仍无首个新交易日真实源：

| 项目 | 值 |
| --- | --- |
| snapshot dates | 0 |
| candidate rows | 0 |
| metrics available | `false` |
| status | `blocked` |
| reason | 未达到 60 日；5 日 labels 与 ML predictions source 也不存在 |

实际输出：[comparison_report.json](E:/liaohua/01_projects/theme-sector-radar-dev/.worktrees/price-momentum-5m-1m/reports/paper_shadow/ml_stock_ranker/prospective_comparison_v1_20260720/comparison_report.json)

物理 SHA：`09cf637aedb7a661779b5d6e3a8ca3e5d9d5ff4ca1d78f6343416b9c329246b1`。

三组策略名称已写入 blocked contract，但当前没有任何指标结果，不得据此宣称 rule/ML/hybrid 优劣或晋级。

## 验证

- comparison 聚焦测试：`5 passed`。
- 覆盖参数漂移、event manifest、重复执行/篡改、标签成熟度与未来日期、输入 SHA、重复记录、保护评分字段、prediction 参数边界和指标结构。
- 全部 `test_ml_*.py`：`133 passed in 39.09s`。
- event source gate 扩展后全部 `test_ml_*.py`：`135 passed in 39.33s`；stock event 默认不进入 comparison。
- `python -m compileall -q theme_sector_radar scripts tests/theme_sector_radar`：通过。
- tracked 与本轮新增文件 `diff-check`：通过。
- 当前 blocked artifact 重放验证：`status=blocked`、`snapshot_dates=0`、`metrics_available=false`，物理 SHA 与上文一致。
