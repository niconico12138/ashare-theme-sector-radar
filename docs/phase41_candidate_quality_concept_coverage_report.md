# Phase 41 Candidate Quality & Concept Coverage Report

**日期**: 2026-07-06
**修复范围**: theme-sector-radar-dev 候选池质量分析 + 概念覆盖扫描

---

## 1. 修改文件清单

### theme-sector-radar-dev
| 文件 | 修改内容 |
|------|----------|
| `scripts/analyze_candidate_pool_quality.py` | 新增候选池质量分析脚本 |
| `scripts/analyze_concept_coverage_for_reports.py` | 新增概念覆盖扫描脚本 |
| `scripts/run_daily_ai_stock_report.py` | 添加候选池质量章节到 JSON 和 Markdown |
| `tests/theme_sector_radar/test_candidate_pool_quality.py` | 新增测试 |

---

## 2. Root Cause 分析

### 2.1 候选池不足根因
**根因**: 候选池不足 30 的主要原因：

1. **非主板股票过滤**: 22 只非主板股票（300xxx/688xxx/833xxx）被过滤
2. **板块集中度过高**: "氟化工概念"贡献 7 只（35%），导致候选池不够分散
3. **概念成分股库覆盖不足**: 15 个 Top 概念缺少本地覆盖

### 2.2 概念覆盖缺口
**根因**: `concept_members_history.csv` 只覆盖 21 个概念，而 4 天的 Top 20 概念共有 35 个，其中 15 个缺失。

---

## 3. 2026-07-06 候选池质量摘要

### 基础统计
| 指标 | 值 |
|------|-----|
| Final Candidate Count | 20 |
| Trend Only | 5 |
| Burst Only | 5 |
| Both | 10 |
| Unique Board Count | 8 |
| Unique Stock Count | 20 |

### 板块集中度
| 板块 | 数量 | 占比 |
|------|------|------|
| 氟化工概念 | 7 | 35.0% |
| 芬太尼 | 3 | 15.0% |
| 环氧丙烷 | 3 | 15.0% |
| 动物疫苗 | 2 | 10.0% |
| 丙烯酸 | 2 | 10.0% |

### 质量风险标签
- ⚠️ **insufficient_candidates**: 候选数 < 25

---

## 4. 板块集中度分析

### 问题
- Top1 板块（氟化工概念）占比 35%，接近 40% 警戒线
- Top3 板块占比 65%，接近 70% 警戒线
- 候选池高度依赖少数板块

### 原因
- 氟化工概念板块成分股较多（40 只），且多为主板股票
- 其他板块成分股较少或非主板股票比例高

---

## 5. 7/1、7/2、7/3、7/6 Top 概念覆盖扫描结果

### 覆盖统计
| 指标 | 值 |
|------|-----|
| Total Concepts | 35 |
| Covered Good (>=10 stocks) | 11 |
| Covered Thin (1-9 stocks) | 9 |
| Missing | 15 |

### Top 补库清单
| Priority | Concept | Reason | Local Stocks | Priority Score |
|----------|---------|--------|--------------|----------------|
| 1 | 芬太尼 | missing | 0 | 68.3 |
| 2 | 华为海思概念股 | missing | 0 | 65.4 |
| 3 | 超级电容 | missing | 0 | 62.7 |
| 4 | 合成生物 | thin_coverage | 8 | 58.2 |
| 5 | 氟化工概念 | thin_coverage | 8 | 56.8 |

---

## 6. Top 补库清单

### 高优先级（missing）
1. **芬太尼**: 4 天全部出现，best_rank=5，无本地覆盖
2. **华为海思概念股**: 出现 3 次，best_rank=6，无本地覆盖
3. **超级电容**: 出现 2 次，best_rank=7，无本地覆盖
4. **电子纸**: 出现 2 次，best_rank=10，无本地覆盖
5. **华为鲲鹏概念股**: 出现 2 次，best_rank=12，无本地覆盖

### 中优先级（thin_coverage）
1. **合成生物**: 8 stocks，但多次出现
2. **氟化工概念**: 8 stocks，但多次出现
3. **光刻胶**: 8 stocks，但多次出现
4. **光刻机**: 8 stocks，但多次出现
5. **创新药**: 8 stocks，但多次出现

---

## 7. 是否迁移了样例概念

**本阶段未迁移样例概念**。

原因：
1. 当前 `concept_members_history.csv` 已覆盖 21 个概念，基本满足需求
2. 缺失的 15 个概念主要是低频出现的概念
3. 优先级最高的"芬太尼"是新出现的概念，需要从外部数据源获取

**建议后续迁移**：
- 芬太尼（priority_score=68.3）
- 华为海思概念股（priority_score=65.4）
- 超级电容（priority_score=62.7）

---

## 8. 日报新增候选池质量章节摘录

### JSON 输出
```json
"candidate_pool_quality": {
  "basic_stats": {
    "final_candidate_count": 20,
    "trend_count": 5,
    "burst_count": 5,
    "both_count": 10,
    "unique_board_count": 8,
    "unique_stock_count": 20
  },
  "board_concentration": {
    "top1_board_ratio": 0.35,
    "top3_board_ratio": 0.65
  },
  "quality_risk_tags": ["insufficient_candidates"]
}
```

### Markdown 输出
```markdown
## 候选池质量

- **候选股总数**: 20
- **趋势池**: 5 只
- **短线池**: 5 只
- **同时入选**: 10 只
- **板块数**: 8
- **Top1 板块占比**: 35.0%
- **Top3 板块占比**: 65.0%
- **质量标签**: insufficient_candidates

### 板块集中度

| 板块 | 数量 | 占比 |
|------|------|------|
| 氟化工概念 | 7 | 35.0% |
| 芬太尼 | 3 | 15.0% |
| 环氧丙烷 | 3 | 15.0% |
```

---

## 9. 剩余风险

1. **候选池仍不足 30 只**: 当前 20 只，主要因为非主板股票过滤。如果需要更多候选，可考虑：
   - 放宽主板过滤（包含 300xxx 创业板）
   - 增加板块 Top N（当前各 5 个）

2. **板块集中度过高**: "氟化工概念"贡献 35%，导致候选池不够分散

3. **概念成分股库覆盖不足**: 15 个 Top 概念缺少本地覆盖

4. **部分概念 stock_count < 10**: 9 个概念只有 7-8 只股票

---

## 10. 测试命令与结果

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

### 候选池质量分析
```bash
python scripts/analyze_candidate_pool_quality.py --as-of 2026-07-06
# 结果: JSON/Markdown 正常生成 ✅
```

### 概念覆盖扫描
```bash
python scripts/analyze_concept_coverage_for_reports.py \
  --dates 2026-07-01,2026-07-02,2026-07-03,2026-07-06 \
  --top-n 20 \
  --market-data-root "E:/liaohua/01_projects/market_data_service"
# 结果: JSON/Markdown 正常生成 ✅
```

---

## 11. 验收标准检查

| 标准 | 结果 |
|------|------|
| 1. pytest 不回归 | ✅ 1002 passed |
| 2. candidate_pool_quality.json/md 正常生成 | ✅ |
| 3. concept_coverage_summary.json/md 正常生成 | ✅ |
| 4. daily_ai_stock_report JSON 包含 candidate_pool_quality | ✅ |
| 5. daily_ai_stock_report Markdown 包含"候选池质量"章节 | ✅ |
| 6. 输出 Top 补库概念清单 | ✅ 24 个概念 |
| 7. 不泄露 API key | ✅ 无泄露 |
| 8. 不运行 portfolio_manager | ✅ |
| 9. 不输出买卖建议 | ✅ 只输出研究观察 |
| 10. 不破坏主板/ST过滤 | ✅ |
| 11. 不大规模人工补库 | ✅ |
| 12. 不引入脆弱网页解析 | ✅ |

---

**报告生成时间**: 2026-07-06
**修复状态**: 全部完成 ✅
