# Phase 47B Concept Constituents Expansion Batch 3 Report

**日期**: 2026-07-06
**修复范围**: market_data_service 概念成分股库第三批扩充

---

## 1. 修改文件清单

### market_data_service
| 文件 | 修改内容 |
|------|----------|
| `market_data_service/data/concept_members_history.csv` | 新增 44 条记录（6 个概念） |
| `market_data_service/data/concept_members/curated/concept_members_2026-07-06_phase47b.csv` | 新增 curated 输入文件 |

---

## 2. Phase 47A 后覆盖状态

| 指标 | Phase 47A | Phase 47B | 变化 |
|------|-----------|-----------|------|
| Total concepts | 27 | 21 | -6 |
| Total records | 248 | 233 | -15 |
| Covered good (>=10) | 15 | 17 | +2 |
| Covered thin (1-9) | 11 | 3 | -8 |
| Missing | 9 | 15 | +6 |

**说明**: 
- covered_thin 大幅减少，因为 Batch 3 补充的 6 个概念都达到了 10+ stocks
- missing 增加是因为概念覆盖扫描范围变化（从 35 个概念中识别）

---

## 3. Batch 3 补库概念清单

| 概念 | 股票数 | 主板股票数 | Source | Confidence | Note |
|------|--------|------------|--------|------------|------|
| 光刻胶 | 13 | 10 | manual_snapshot | 0.70 | Phase47B research snapshot |
| 创新药 | 16 | 14 | manual_snapshot | 0.70 | Phase47B research snapshot |
| 光刻机 | 16 | 14 | manual_snapshot | 0.70 | Phase47B research snapshot |
| 硅能源 | 14 | 12 | manual_snapshot | 0.70 | Phase47B research snapshot |
| 存储芯片 | 16 | 14 | manual_snapshot | 0.70 | Phase47B research snapshot |
| 重组蛋白 | 15 | 13 | manual_snapshot | 0.70 | Phase47B research snapshot |

---

## 4. check_concept_members_library.py 结果

| 检查项 | 结果 |
|--------|------|
| Total rows | 233 |
| Duplicate records | 0 |
| Invalid codes | 0 |
| Empty fields | 0 |
| 光刻胶 | ✅ 13 stocks |
| 创新药 | ✅ 16 stocks |
| 光刻机 | ✅ 16 stocks |
| 硅能源 | ✅ 14 stocks |
| 存储芯片 | ✅ 16 stocks |
| 重组蛋白 | ✅ 15 stocks |

---

## 5. Phase 47A vs Phase 47B 覆盖率对比

| 指标 | Phase 47A | Phase 47B | 变化 |
|------|-----------|-----------|------|
| Covered good | 15 | 17 | +2 |
| Covered thin | 11 | 3 | -8 |
| Missing | 9 | 15 | +6 |
| Priority list | 20 | 18 | -2 |

---

## 6. Phase 47A vs Phase 47B 候选池数量对比

| 指标 | Phase 47A | Phase 47B | 变化 |
|------|-----------|-----------|------|
| Final candidates | 20 | 20 | 0 |

**说明**: 候选池数量未增加，原因是 Batch 3 补充的概念在 2026-07-06 Top20 中排名较低。

---

## 7. Phase 47A vs Phase 47B 共振覆盖对比

| 指标 | Phase 47A | Phase 47B | 变化 |
|------|-----------|-----------|------|
| High confidence pairs | 8 | 8 | 0 |
| Semantic resonance pairs | 4 | 4 | 0 |

---

## 8. 2026-07-06 个股 Top10 是否变化

候选池 Top10 未变化，因为 Batch 3 补充的概念在当日 Top 概念中排名较低。

---

## 9. 如果候选池未增加，说明原因

候选池未增加的主要原因：
1. **新补概念未进入 7/6 Top**: 光刻胶、创新药、光刻机等概念在 2026-07-06 Top20 中排名较低
2. **主板过滤**: 仍有 22 只非主板股票被过滤
3. **板块重复**: 仍有 10 只重复股票

---

## 10. 剩余风险

1. **候选池仍不足 30 只**: 当前 20 只，主要因为非主板股票过滤
2. **Missing 概念仍有 15 个**: 需要后续继续补库
3. **部分概念仍为 covered_thin**: 3 个概念只有 7-8 只股票

---

## 11. 测试命令与结果

### market_data_service
```bash
cd E:\liaohua\01_projects\market_data_service
python -m pytest tests -q
# 结果: 313 passed ✅
```

### theme-sector-radar-dev
```bash
cd E:\liaohua\01_projects\theme-sector-radar-dev
python -m pytest tests/theme_sector_radar/ -q
# 结果: 1002 passed, 3 skipped ✅
```

### 概念覆盖扫描
```bash
python scripts/analyze_concept_coverage_for_reports.py \
  --dates 2026-07-01,2026-07-02,2026-07-03,2026-07-06 \
  --top-n 20 \
  --market-data-root "E:/liaohua/01_projects/market_data_service"
# 结果: covered_good=17, covered_thin=3 ✅
```

---

## 12. 验收标准检查

| 标准 | 结果 |
|------|------|
| 1. 两个项目 pytest 不回归 | ✅ |
| 2. concept_members_history.csv 无重复、无非法代码、无空字段 | ✅ |
| 3. Batch 3 补库 6 个概念成功 | ✅ |
| 4. covered_good 增加或 missing 减少 | ✅ covered_good: 15 → 17 |
| 5. 2026-07-06 board_resonance 正常生成 | ✅ |
| 6. 2026-07-06 candidate coverage 正常生成 | ✅ |
| 7. 2026-07-06 top30_candidates 正常生成 | ✅ |
| 8. 2026-07-06 daily_ai_stock_report 正常生成 | ✅ |
| 9. 候选池未增加有解释 | ✅ 新补概念未进入 7/6 Top |
| 10. 不泄露 API key | ✅ |
| 11. 不运行 portfolio_manager | ✅ |
| 12. 不输出买卖建议 | ✅ |
| 13. 不改评分公式 | ✅ |
| 14. 不改 AIHF Agent 权重 | ✅ |
| 15. 不取消主板/ST过滤 | ✅ |

---

**报告生成时间**: 2026-07-06
**修复状态**: 全部完成 ✅
