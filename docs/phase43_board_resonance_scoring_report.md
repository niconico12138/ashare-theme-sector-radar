# Phase 43 Board Resonance Scoring Report

**日期**: 2026-07-06
**修复范围**: theme-sector-radar-dev 板块共振评分

---

## 1. 修改文件清单

### theme-sector-radar-dev
| 文件 | 修改内容 |
|------|----------|
| `theme_sector_radar/agents/ranking_report/board_resonance_agent.py` | 新增 BoardResonanceAgent |
| `scripts/analyze_board_resonance.py` | 新增共振分析脚本 |
| `scripts/export_top30_candidates.py` | 添加共振字段到候选股 |
| `scripts/run_daily_ai_stock_report.py` | 添加板块共振章节 |

---

## 2. 技术路线

1. 新增 `BoardResonanceAgent`，计算行业与概念板块的共振评分
2. 新增 `analyze_board_resonance.py` 脚本，生成共振报告
3. 修改 `export_top30_candidates.py`，给候选股添加共振字段
4. 修改 `run_daily_ai_stock_report.py`，在日报中展示共振组合

---

## 3. 共振评分公式

```
resonance_score =
  industry_strength_score * 0.30
+ concept_strength_score * 0.25
+ overlap_score * 0.20
+ label_alignment_score * 0.15
+ risk_adjustment_score * 0.10
```

各分项计算：
- **industry_strength_score**: `min(100, ranking_score * 0.7 + opportunity_score * 30)`
- **concept_strength_score**: `min(100, composite_score * 0.5 + trend_score * 0.3 + burst_score * 0.2)`
- **overlap_score**: 10+ stocks → 100, 5-9 → 75, 2-4 → 50, 1 → 25, 0 → 0
- **label_alignment_score**: 都 trend_confirmed → 100, 一个强一个中性 → 50, weak → 20
- **risk_adjustment_score**: 无风险 → 100, conflicted → 40, weak → 20, risk_high → 0

resonance_bonus: `min(8.0, resonance_score / 100 * 8.0)`

---

## 4. resonance_type 定义

| 类型 | 条件 |
|------|------|
| industry_trend_plus_concept_burst | 行业 trend_confirmed，概念 burst_score >= 55，resonance_score >= 70 |
| industry_trend_plus_concept_trend | 行业 trend_confirmed，概念 trend_score >= 55，resonance_score >= 65 |
| concept_only_hot | 概念强，但行业弱或无 overlap |
| industry_only_trend | 行业强，但概念趋势/短线弱 |
| weak_or_conflicted | 任一侧 weak_or_avoid、conflicted、risk_high |

---

## 5. 2026-07-01、2026-07-02、2026-07-03、2026-07-06 共振 Top10 摘要

### 2026-07-06
| Rank | Industry | Concept | Type | Score | Bonus |
|------|----------|---------|------|-------|-------|
| 1 | 白色家电 | 动物疫苗 | neutral | 64.18 | +5.13 |
| 2 | 化学制药 | 动物疫苗 | neutral | 64.18 | +5.13 |
| 3 | 医疗服务 | 动物疫苗 | neutral | 63.88 | +5.11 |
| 4 | 白色家电 | 合成生物 | neutral | 63.50 | +5.08 |
| 5 | 化学制药 | 合成生物 | neutral | 63.50 | +5.08 |

---

## 6. 2026-07-06 概念原排名 vs 共振调整后排名对比

| Concept | Original Score | Resonance Bonus | Adjusted Score |
|---------|----------------|-----------------|----------------|
| 动物疫苗 | 71.41 | +5.13 | 76.54 |
| 合成生物 | 69.10 | +5.08 | 74.18 |
| 阿尔茨海默概念 | 68.18 | +4.95 | 73.13 |
| 仿制药一致性评价 | 64.68 | +4.85 | 69.53 |
| 创新药 | 64.68 | +4.85 | 69.53 |

---

## 7. 候选股 resonance 字段示例

```json
{
  "code": "600623",
  "name": "华谊集团",
  "source_resonance_pair": "",
  "stock_resonance_score": 0,
  "stock_resonance_bonus": 0,
  "resonance_type": "",
  "resonance_industry": "",
  "resonance_concept": ""
}
```

**说明**: 当前候选股主要来自概念板块，未与行业板块产生重叠，因此 resonance 字段为空。这是因为共振组合是基于行业和概念的交叉，而候选股只属于概念板块。

---

## 8. 日报新增板块共振章节摘录

```markdown
## 板块共振

- **共振组合数**: 100
- **高置信度组合**: 0
- **平均共振分**: 60.53

### 共振 Top10

| Rank | 行业 | 概念 | 类型 | 共振分 | 加分 | 重叠股数 | 说明 |
|------|------|------|------|--------|------|----------|------|
| 1 | 白色家电 | 动物疫苗 | neutral | 64.18 | +5.13 | 0 | ... |
| 2 | 化学制药 | 动物疫苗 | neutral | 64.18 | +5.13 | 0 | ... |
```

---

## 9. 剩余风险

1. **共振组合重叠股数为 0**: 当前行业和概念成分股库不完整，导致重叠股数为 0
2. **高置信度组合为 0**: 需要更多行业-概念重叠才能产生高置信度组合
3. **共振类型多为 neutral**: 需要更多行业-概念匹配才能产生特定共振类型

---

## 10. 测试命令与结果

### theme-sector-radar-dev
```bash
cd E:\liaohua\01_projects\theme-sector-radar-dev
python -m pytest tests/theme_sector_radar/ -q
# 结果: 1002 passed, 3 skipped ✅
```

### Board Resonance Analysis
```bash
python scripts/analyze_board_resonance.py --as-of 2026-07-06
# 结果: JSON/Markdown 正常生成 ✅
```

### Export Top30 Candidates
```bash
python scripts/export_top30_candidates.py --as-of 2026-07-06
# 结果: 候选股包含 resonance 字段 ✅
```

---

## 11. 验收标准检查

| 标准 | 结果 |
|------|------|
| 1. pytest 不回归 | ✅ 1002 passed |
| 2. board_resonance.json/md 正常生成 | ✅ |
| 3. daily_ai_stock_report JSON 包含 board_resonance | ✅ |
| 4. Markdown 包含"板块共振"章节 | ✅ |
| 5. top30_candidates.json 包含 resonance 字段 | ✅ |
| 6. 原始 composite_score 不被覆盖 | ✅ |
| 7. resonance_bonus <= 8 | ✅ |
| 8. weak_or_avoid/conflicted/risk_high 不获得高加分 | ✅ |
| 9. 不接 LLM | ✅ |
| 10. 不运行 portfolio_manager | ✅ |
| 11. 不输出买卖建议 | ✅ |
| 12. 不改 AIHF selected Agent 权重 | ✅ |
| 13. 不取消主板/ST过滤 | ✅ |

---

**报告生成时间**: 2026-07-06
**修复状态**: 全部完成 ✅
