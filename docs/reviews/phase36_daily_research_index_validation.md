# Phase 36: Daily Research Index and Review Workflow Validation

## 修改内容

1. 新增 `sector_research_index.py` 模块：多日研究索引
2. 修改 `cli.py`：新增 `--build-research-index` 参数
3. 新增 `test_sector_research_index.py`：9 个测试

## 索引功能

### 板块出现频率

统计每个板块在多日中出现的次数、标签历史和 regime 历史。

### 标签变化检测

检测哪些板块的 consensus_label 在不同日期之间发生变化。

### 分数趋势

跟踪每个板块的 ranking_score、opportunity_score、confidence_score 随时间的变化。

### 风险信号检测

检测 veto 触发和 conflict 级别变化。

### Regime 关联

统计不同 regime 下出现的板块。

### 人工复盘模板

提供结构化的复盘问题清单。

## 索引结果

| 指标 | 值 |
|------|-----|
| 覆盖天数 | 28 |
| 跟踪板块数 | 52 |
| 标签变化数 | 101 |
| 风险信号数 | 34 |

## 输出

- `reports/sector_research/index/research_index.json`
- `reports/sector_research/index/research_index.md`

## 验证结果

### 测试结果

9 个新增测试全部通过：
- `test_build_index_basic` ✅
- `test_sector_frequency` ✅
- `test_label_changes` ✅
- `test_risk_signals` ✅
- `test_review_template` ✅
- `test_markdown_generation` ✅
- `test_save_index` ✅
- `test_no_trade_advice_words` ✅
- `test_empty_date_range` ✅

### 完整测试结果

664 passed, 4 warnings

## 结论

### 是否修改了生产决策规则

**否。** 只新增了索引和复盘工具，不改变任何评分、标签、投票、Veto 逻辑。

### 下一步建议

1. 每日盘后运行 `--build-research-index` 更新索引
2. 基于索引进行人工复盘
3. 如果索引工具有价值，考虑在 Phase 38+ 新增自动化监控

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
