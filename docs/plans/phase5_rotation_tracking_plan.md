# Phase 5 连续多日快照与板块轮动追踪计划

日期：2026-06-29  
目标：让板块雷达从"单日盘后复盘"升级为"多日轮动观察"

## 1. 历史快照读取策略

### 1.1 数据源优先级
1. `--compare-to YYYY-MM-DD` 指定日期
2. `--lookback-days N` 内找最近可用报告
3. 默认 `reports/theme_sector_radar/YYYY-MM-DD/theme_sector_radar.json`
4. 备选 `data_cache/YYYY-MM-DD/raw_snapshot.json`

### 1.2 CLI 参数
- `--compare-to YYYY-MM-DD`: 指定比较日期
- `--lookback-days 5`: 回溯天数，默认 5

### 1.3 降级策略
- 找不到历史快照时，本次报告仍生成
- rotation 字段为空
- warnings 记录原因

## 2. 轮动指标计算

### 2.1 新增字段

每个板块新增：
```json
{
  "previous_rank": 5,
  "current_rank": 2,
  "rank_change": 3,
  "previous_score": 75.0,
  "score_change": 8.0,
  "rotation_tags": ["rising_fast", "score_up"]
}
```

### 2.2 rank_change 规则
- `rank_change = previous_rank - current_rank`
- 正数：排名上升
- 负数：排名下降
- `previous_rank` 为空：`new_entry`

## 3. 轮动标签规则

### 3.1 rotation_tags

| 标签 | 规则 |
|------|------|
| new_entry | 今日进入 Top N，历史不存在 |
| rising_fast | rank_change >= 3 或 score_change >= 8 |
| falling | rank_change <= -3 |
| persistent_strength | 连续两期 Top N 且 final_score >= 75 |
| risk_up | risk_penalty 增加 >= 5 或 risk_level 上升 |
| risk_down | risk_penalty 减少 >= 5 |
| score_up | score_change >= 5 |
| score_down | score_change <= -5 |

## 4. 轮动分类

### 4.1 rotation_summary

```json
{
  "rotation_summary": {
    "industry": {
      "new_entries": ["板块A"],
      "dropped_out": ["板块B"],
      "rising_fast": ["板块C"],
      "persistent_strength": ["板块D"],
      "risk_up": ["板块E"]
    },
    "concept": { ... }
  }
}
```

### 4.2 分类规则
1. **new_entries**: 今日 Top N 中存在，历史 Top N 中不存在
2. **dropped_out**: 历史 Top N 中存在，今日 Top N 中不存在
3. **rising_fast**: rank_change >= 3 或 score_change >= 8
4. **persistent_strength**: 连续两期 Top N 且 final_score >= 75
5. **risk_up**: risk_penalty 增加 >= 5 或 risk_level 上升

## 5. fixture 多日样本

### 5.1 rotation-day1
- 行业板块 25 个
- 概念板块 25 个
- 日期：2026-06-27

### 5.2 rotation-day2
- 行业板块 25 个
- 概念板块 25 个
- 日期：2026-06-28
- 相比 day1：
  - 至少 1 个 new_entry
  - 至少 1 个 rising_fast
  - 至少 1 个 persistent_strength
  - 至少 1 个 dropped_out
  - 至少 1 个 risk_up

## 6. 报告字段设计

### 6.1 JSON 新增字段
```json
{
  "rotation_summary": { ... },
  "comparison": {
    "compare_to_date": "2026-06-27",
    "comparison_source": "reports/theme_sector_radar/2026-06-27/theme_sector_radar.json",
    "comparison_status": "ok",
    "warnings": []
  }
}
```

### 6.2 Markdown 新增章节
```markdown
## 板块轮动变化

**对比日期**: 2026-06-27

### 新晋 Top N
- 板块A (排名上升 5 位)

### 快速升温
- 板块C (排名上升 3 位，评分 +8.0)

### 连续强势
- 板块D (连续 2 期 Top N，评分 78.0)

### 风险升高
- 板块E (风险扣分 +6.0)

### 掉出 Top N
- 板块B (原排名 8，现未上榜)
```

## 7. 测试与验收命令

```bash
# 默认测试
python -m pytest tests/theme_sector_radar/ -v

# 生成 day1
python -m theme_sector_radar.cli --as-of 2026-06-27 --top-n 10 --offline-fixture --fixture-profile rotation-day1 --output reports/theme_sector_radar/2026-06-27-rotation-day1

# 生成 day2 并比较 day1
python -m theme_sector_radar.cli --as-of 2026-06-28 --top-n 10 --offline-fixture --fixture-profile rotation-day2 --compare-to 2026-06-27 --output reports/theme_sector_radar/2026-06-28-rotation-day2

# 使用 lookback
python -m theme_sector_radar.cli --as-of 2026-06-28 --top-n 10 --offline-fixture --fixture-profile rotation-day2 --lookback-days 5 --output reports/theme_sector_radar/2026-06-28-rotation-lookback
```
