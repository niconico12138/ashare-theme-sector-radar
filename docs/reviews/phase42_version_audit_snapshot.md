# Phase 42: Version Audit Snapshot

## 当前工作区状态摘要

- **总 untracked 文件数**: 62
- **已修改文件数**: 8
- **阶段覆盖范围**: Phase 34-42
- **业务逻辑变更**: 无（本阶段只做审计）

## Untracked 文件分组

### A. 核心运行代码（建议纳入版本管理）

| 文件路径 | 说明 |
|----------|------|
| `theme_sector_radar/factors/__init__.py` | 因子模块初始化 |
| `theme_sector_radar/factors/schema.py` | 因子 schema 定义 |
| `theme_sector_radar/factors/registry.py` | 因子元数据注册 |
| `theme_sector_radar/factors/normalizer.py` | 因子归一化 |
| `theme_sector_radar/factors/calculators.py` | bars 因子计算器 |
| `theme_sector_radar/factors/snapshot.py` | 因子快照构建 |
| `theme_sector_radar/reporting/__init__.py` | 报告模块初始化 |
| `theme_sector_radar/reporting/daily_decision_summary.py` | 日报决策摘要 |
| `theme_sector_radar/reporting/daily_compact_report.py` | 日报简洁报告 |
| `theme_sector_radar/reporting/stock_profile.py` | 个股画像 |
| `theme_sector_radar/reporting/stock_explanation.py` | 个股解释 |
| `theme_sector_radar/reporting/selection_quality.py` | 选股质量 |
| `theme_sector_radar/reporting/report_filename.py` | 报告文件名构造 |
| `theme_sector_radar/reporting/v2_shadow_monitor_section.py` | V2 Shadow Monitor 小节 |
| `theme_sector_radar/data/stock_bars_provider.py` | bars 数据提供者 |
| `theme_sector_radar/scoring/display_score_shadow.py` | display_score_shadow |
| `theme_sector_radar/scoring/factor_composite_shadow_score.py` | factor_composite_shadow_score v1 |
| `theme_sector_radar/scoring/factor_composite_shadow_score_v2.py` | factor_composite_shadow_score v2 |

### B. 回填/诊断/评估脚本（建议纳入版本管理）

| 文件路径 | 说明 |
|----------|------|
| `scripts/backfill_factor_composite_shadow_score.py` | factor composite shadow score 回填 |
| `scripts/backfill_stock_analysis_fields.py` | stock analysis fields 回填 |
| `scripts/build_factor_forward_returns.py` | factor forward returns 构建 |
| `scripts/diagnose_bars_factor_definitions.py` | bars 因子定义诊断 |
| `scripts/diagnose_bars_group_discrimination.py` | bars 分组区分度诊断 |
| `scripts/diagnose_factor_composite_attribution.py` | factor composite attribution 诊断 |
| `scripts/diagnose_factor_composite_negative_ic.py` | factor composite 负 IC 诊断 |
| `scripts/diagnose_factor_forward_return_bars.py` | factor forward return bars 诊断 |
| `scripts/diagnose_stock_bars_sources.py` | stock bars 数据源诊断 |
| `scripts/evaluate_bars_factor_shadow_policy.py` | bars factor shadow policy 评估 |
| `scripts/evaluate_display_score_shadow.py` | display_score_shadow 评估 |
| `scripts/evaluate_factor_composite_shadow_score.py` | factor composite shadow score 评估 |
| `scripts/evaluate_factor_composite_v2_stability.py` | factor composite v2 稳定性评估 |
| `scripts/evaluate_sector_support_by_opportunity_type.py` | sector support 按机会类型评估 |
| `scripts/evaluate_stock_enhanced_factors.py` | stock enhanced factors 评估 |
| `scripts/mine_v2_historical_opportunities.py` | v2 历史机会挖掘 |
| `scripts/update_factor_v2_shadow_monitor.py` | v2 shadow monitor 更新 |
| `scripts/validate_bars_factor_backfill_chain.py` | bars 因子回填链路验证 |

### C. 测试文件（建议纳入版本管理）

| 文件路径 | 说明 |
|----------|------|
| `tests/theme_sector_radar/test_bars_data_lineage.py` | bars 数据血缘测试 |
| `tests/theme_sector_radar/test_bars_factor_shadow_policy_evaluation.py` | bars factor shadow policy 评估测试 |
| `tests/theme_sector_radar/test_daily_compact_report.py` | 日报简洁报告测试 |
| `tests/theme_sector_radar/test_daily_decision_summary.py` | 日报决策摘要测试 |
| `tests/theme_sector_radar/test_display_score_shadow.py` | display_score_shadow 测试 |
| `tests/theme_sector_radar/test_factor_calculators.py` | bars 因子计算器测试 |
| `tests/theme_sector_radar/test_factor_composite_attribution.py` | factor composite attribution 测试 |
| `tests/theme_sector_radar/test_factor_composite_negative_ic_diagnosis.py` | factor composite 负 IC 诊断测试 |
| `tests/theme_sector_radar/test_factor_composite_shadow_score.py` | factor composite shadow score 测试 |
| `tests/theme_sector_radar/test_factor_composite_shadow_score_backfill.py` | factor composite shadow score 回填测试 |
| `tests/theme_sector_radar/test_factor_composite_shadow_score_evaluation.py` | factor composite shadow score 评估测试 |
| `tests/theme_sector_radar/test_factor_composite_shadow_score_v2.py` | factor composite shadow score v2 测试 |
| `tests/theme_sector_radar/test_factor_composite_v2_stability.py` | factor composite v2 稳定性测试 |
| `tests/theme_sector_radar/test_factor_forward_return_bars_diagnosis.py` | factor forward return bars 诊断测试 |
| `tests/theme_sector_radar/test_factor_forward_returns_builder.py` | factor forward returns 构建测试 |
| `tests/theme_sector_radar/test_factor_schema.py` | 因子 schema 测试 |
| `tests/theme_sector_radar/test_factor_v2_shadow_monitor.py` | factor v2 shadow monitor 测试 |
| `tests/theme_sector_radar/test_mine_v2_historical_opportunities.py` | v2 历史机会挖掘测试 |
| `tests/theme_sector_radar/test_report_filename.py` | 报告文件名测试 |
| `tests/theme_sector_radar/test_sector_support_by_opportunity_type.py` | sector support 按机会类型评估测试 |
| `tests/theme_sector_radar/test_selection_quality.py` | 选股质量测试 |
| `tests/theme_sector_radar/test_stock_analysis_fields_backfill.py` | stock analysis fields 回填测试 |
| `tests/theme_sector_radar/test_stock_enhanced_factors_evaluation.py` | stock enhanced factors 评估测试 |
| `tests/theme_sector_radar/test_stock_explanation.py` | 个股解释测试 |
| `tests/theme_sector_radar/test_stock_profile.py` | 个股画像测试 |
| `tests/theme_sector_radar/test_v2_disagreement_history.py` | v2 分歧历史测试 |
| `tests/theme_sector_radar/test_v2_shadow_monitor_report_section.py` | v2 shadow monitor 报告小节测试 |
| `tests/theme_sector_radar/test_bars_data_lineage.py` | bars 数据血缘测试 |
| `tests/theme_sector_radar/test_bars_factor_shadow_policy_evaluation.py` | bars factor shadow policy 评估测试 |

### D. 文档/规范

| 文件路径 | 说明 |
|----------|------|
| `docs/runbooks/dual_agent_development_workflow.md` | 双 agent 开发工作流 |

### E. 生成报告/临时产物（不建议纳入版本管理）

| 文件路径 | 说明 |
|----------|------|
| `reports/stock_factor_validation/*` | 生成的评估报告 |
| `reports/factor_composite_shadow_score/*` | 生成的因子报告 |
| `reports/stock_analysis_backfill/*` | 生成的回填报告 |
| `data_cache/*` | 数据缓存 |

## 建议纳入版本管理的文件

### 核心代码（A 组）
- 所有 `theme_sector_radar/factors/` 下的文件
- 所有 `theme_sector_radar/reporting/` 下的文件
- `theme_sector_radar/data/stock_bars_provider.py`
- `theme_sector_radar/scoring/display_score_shadow.py`
- `theme_sector_radar/scoring/factor_composite_shadow_score.py`
- `theme_sector_radar/scoring/factor_composite_shadow_score_v2.py`

### 脚本（B 组）
- 所有 `scripts/backfill_*.py`
- 所有 `scripts/diagnose_*.py`
- 所有 `scripts/evaluate_*.py`
- 所有 `scripts/validate_*.py`
- `scripts/build_factor_forward_returns.py`
- `scripts/mine_v2_historical_opportunities.py`
- `scripts/update_factor_v2_shadow_monitor.py`

### 测试（C 组）
- 所有 `tests/theme_sector_radar/test_*.py`

### 文档（D 组）
- `docs/runbooks/dual_agent_development_workflow.md`

## 不建议纳入版本管理的文件

### 生成报告（E 组）
- `reports/stock_factor_validation/*`
- `reports/factor_composite_shadow_score/*`
- `reports/stock_analysis_backfill/*`
- `data_cache/*`

这些是生成产物，应在 `.gitignore` 中排除。

## 风险说明

1. **当前风险**: 大量核心代码和测试处于 untracked 状态，导致阶段成果不可审计、不可回滚
2. **建议**: 尽快将 A/B/C/D 组文件纳入版本管理
3. **不建议**: 将 E 组生成报告纳入版本管理

## 下一步建议

1. **立即执行**: 将 A/B/C/D 组文件纳入版本管理
2. **创建 .gitignore 规则**: 排除 `reports/`、`data_cache/`、`codex_tmp/` 等生成目录
3. **创建 commit**: 以 "Phase 34-41: Factor schema, bars factors, shadow monitoring" 为主题
4. **建立分支保护**: 确保核心代码变更经过 review
