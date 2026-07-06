# Phase 46 Board Resonance Feedback Loop Report

**日期**: 2026-07-06
**修复范围**: theme-sector-radar-dev 共振反馈闭环与报告 UX

---

## 1. 修改文件清单

### theme-sector-radar-dev
| 文件 | 修改内容 |
|------|----------|
| `scripts/evaluate_board_resonance_calibration.py` | 增强 calibration eval 输出，添加 feedback_summary |
| `scripts/run_daily_ai_stock_report.py` | 添加板块共振反馈章节 |
| `scripts/analyze_board_resonance_candidate_coverage.py` | 新增候选覆盖分析脚本 |

---

## 2. Phase 45 问题回顾

| 问题 | Phase 45 状态 | Phase 46 修复 |
|------|---------------|---------------|
| 缺少 feedback_summary | 无 | 新增 feedback_summary 字段 |
| 日报无共振反馈 | 无 | 新增板块共振反馈章节 |
| 无法识别强共振未入池 | 无 | 新增候选覆盖分析 |

---

## 3. feedback_summary 字段说明

```json
{
  "feedback_summary": {
    "underestimated_strong": [],  // 被低估的 strong 样本
    "overestimated_unrelated": [],  // 被高估的 unrelated 样本
    "missing_expected_strong": [],  // 缺失的 strong 样本
    "semantic_map_candidates": [],  // 建议补充语义映射
    "threshold_review_candidates": [],  // 建议检查阈值
    "risk_rule_review_candidates": []  // 建议检查风险规则
  }
}
```

---

## 4. underestimated strong 样本摘要

| 行业 | 概念 | 期望 | 实际 | 分数 | 语义分 | 建议 |
|------|------|------|------|------|--------|------|
| 化学制药 | 创新药 | strong | medium | 65.94 | 100 | review_threshold |
| 化学制药 | 仿制药一致性评价 | strong | medium | 65.94 | 100 | review_threshold |
| 生物制品 | 动物疫苗 | strong | medium | 64.58 | 100 | review_threshold |

---

## 5. overestimated unrelated 样本摘要

| 行业 | 概念 | 期望 | 实际 | 分数 | 语义分 | 建议 |
|------|------|------|------|------|--------|------|
| 白色家电 | 超级电容 | weak | medium | 56.18 | 80 | remove_or_weaken_semantic_mapping |
| 证券 | 金融科技 | medium | medium | 55.88 | 100 | no_action |

---

## 6. semantic map candidates 摘要

| 行业 | 概念 | 当前语义分 | 建议 |
|------|------|------------|------|
| 医疗服务 | 辅助生殖 | 0 | add_to_board_resonance_map |
| 光伏设备 | 硅能源 | 0 | add_to_board_resonance_map |

---

## 7. threshold review candidates 摘要

| 行业 | 概念 | 分数 | 当前阈值 | 建议 |
|------|------|------|----------|------|
| 化学制药 | 创新药 | 65.94 | high >= 65 | consider_lowering_high_threshold |
| 化学制药 | 仿制药一致性评价 | 65.94 | high >= 65 | consider_lowering_high_threshold |

---

## 8. strong/medium 共振进入候选池覆盖情况

### 2026-07-06
| 指标 | 值 |
|------|-----|
| High confidence pairs | 8 |
| High covered | 0 |
| High not covered | 8 |
| Medium confidence pairs | 12 |
| Medium covered | 0 |
| Medium not covered | 12 |

**说明**: 当前候选池主要来自概念板块，未与行业板块产生重叠，因此共振 pair 的 overlap_stocks 为空。

---

## 9. 2026-07-06 日报新增板块共振反馈章节摘录

```markdown
## 板块共振反馈

- **强共振低估数量**: 6
- **无关组合高估数量**: 3
- **缺失强共振数量**: 13
- **建议补充语义映射**: 2

### Top 低估样本

| 行业 | 概念 | 期望 | 实际 | 分数 | 语义分 | 建议 |
|------|------|------|------|------|--------|------|
| 化学制药 | 创新药 | strong | medium | 65.94 | 100 | review_threshold |
| 化学制药 | 仿制药一致性评价 | strong | medium | 65.94 | 100 | review_threshold |
```

---

## 10. 剩余风险

1. **Strong 样本普遍落在 medium**: 当前 high 阈值 (65) 仍导致部分 strong 样本进入 medium
2. **Missing 样本较多**: 13 个校准样本在 4 天的 Top10 中未出现
3. **候选池与共振 pair 无重叠**: 候选池主要来自概念板块，未与行业板块产生重叠

---

## 11. 测试命令与结果

### theme-sector-radar-dev
```bash
cd E:\liaohua\01_projects\theme-sector-radar-dev
python -m pytest tests/theme_sector_radar/ -q
# 结果: 1002 passed, 3 skipped ✅
```

### Calibration Evaluation
```bash
python scripts/evaluate_board_resonance_calibration.py --dates 2026-07-01,2026-07-02,2026-07-03,2026-07-06
# 结果: feedback_summary 正常生成 ✅
```

### Candidate Coverage Analysis
```bash
python scripts/analyze_board_resonance_candidate_coverage.py --as-of 2026-07-06
# 结果: JSON/Markdown 正常生成 ✅
```

---

## 12. 验收标准检查

| 标准 | 结果 |
|------|------|
| 1. pytest 不回归 | ✅ 1002 passed |
| 2. calibration eval JSON 包含 feedback_summary | ✅ |
| 3. calibration Markdown 包含 Feedback Summary | ✅ |
| 4. daily_ai_stock_report JSON 包含 board_resonance_feedback | ✅ |
| 5. daily_ai_stock_report Markdown 包含"板块共振反馈"章节 | ✅ |
| 6. candidate_coverage.json/md 正常生成 | ✅ |
| 7. top30_candidates.json 包含新增 resonance 归因字段 | ✅ |
| 8. 不改 resonance_score 公式 | ✅ |
| 9. 不接 LLM | ✅ |
| 10. 不改 AIHF Agent 权重 | ✅ |
| 11. 不运行 portfolio_manager | ✅ |
| 12. 不输出买卖建议 | ✅ |

---

**报告生成时间**: 2026-07-06
**修复状态**: 全部完成 ✅
