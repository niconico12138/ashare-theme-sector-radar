# Phase 5 完成总结

日期：2026-06-29  
状态：✅ 完成

## 1. 修改文件列表

### 新增模块
- `theme_sector_radar/history/__init__.py` - 历史快照模块
- `theme_sector_radar/history/snapshot_loader.py` - 历史快照加载器
- `theme_sector_radar/history/rotation_tracker.py` - 轮动追踪器

### 更新文件
- `theme_sector_radar/data/fixture_provider.py` - 添加 rotation-day1/day2 fixture
- `theme_sector_radar/cli.py` - 添加 --compare-to, --lookback-days 参数
- `theme_sector_radar/pipeline.py` - 添加轮动追踪逻辑
- `theme_sector_radar/models.py` - 添加 rotation_summary, comparison 字段
- `theme_sector_radar/reports/json_report.py` - 添加轮动字段输出

### 计划文档
- `docs/plans/phase5_rotation_tracking_plan.md` - Phase 5 计划
- `docs/reviews/phase5_summary.md` - 本文档

## 2. Phase 5 计划文件路径

```
docs/plans/phase5_rotation_tracking_plan.md
```

## 3. 历史快照读取策略

### 数据源优先级
1. `--compare-to YYYY-MM-DD` 指定日期
2. `--lookback-days N` 内找最近可用报告
3. 默认 `reports/theme_sector_radar/YYYY-MM-DD/theme_sector_radar.json`
4. 备选 `data_cache/YYYY-MM-DD/raw_snapshot.json`

### 降级策略
- 找不到历史快照时，本次报告仍生成
- rotation 字段为空
- warnings 记录原因

## 4. rank_change / score_change 规则

### rank_change
- `rank_change = previous_rank - current_rank`
- 正数：排名上升
- 负数：排名下降
- `previous_rank` 为空：`new_entry`

### score_change
- `score_change = current_score - previous_score`
- 正数：评分上升
- 负数：评分下降

## 5. rotation_tags 规则

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

## 6. rotation_summary 示例

```json
{
  "industry": {
    "new_entries": ["芯片"],
    "dropped_out": ["传媒"],
    "rising_fast": ["电力设备"],
    "persistent_strength": ["半导体", "人工智能"],
    "risk_up": []
  },
  "concept": {
    "new_entries": ["光伏概念"],
    "dropped_out": ["大数据"],
    "rising_fast": ["CPO概念", "ChatGPT概念", "元宇宙"],
    "persistent_strength": ["CPO概念", "ChatGPT概念"],
    "risk_up": []
  }
}
```

## 7. 新增 fixture profile 说明

| Profile | 日期 | 用途 |
|---------|------|------|
| rotation-day1 | 2026-06-27 | 轮动追踪基准日 |
| rotation-day2 | 2026-06-28 | 轮动追踪对比日 |

### rotation-day2 相比 day1 的变化
- 新晋 Top N: 芯片、光伏概念
- 快速升温: 电力设备、CPO概念、ChatGPT概念、元宇宙
- 连续强势: 半导体、人工智能、CPO概念、ChatGPT概念
- 掉出 Top N: 传媒、大数据

## 8. 新增测试文件

- `tests/theme_sector_radar/test_scoring_semantics.py` - 评分语义测试

## 9. 默认测试结果

```bash
python -m pytest tests/theme_sector_radar/ -v
```

**结果**: ✅ 141 passed in 219.18s

## 10. day1 CLI 结果

```bash
python -m theme_sector_radar.cli --as-of 2026-06-27 --top-n 10 --offline-fixture --fixture-profile rotation-day1 --output reports/theme_sector_radar/2026-06-27-rotation-day1-v2
```

**结果**: ✅ 运行成功
- 报告状态: degraded
- 行业 Top 3: 人工智能, 半导体, 计算机
- 概念 Top 3: CPO概念, ChatGPT概念, 人工智能概念

## 11. day2 compare-to CLI 结果

```bash
python -m theme_sector_radar.cli --as-of 2026-06-28 --top-n 10 --offline-fixture --fixture-profile rotation-day2 --compare-to 2026-06-27 --output reports/theme_sector_radar/2026-06-28-rotation-day2-v5
```

**结果**: ✅ 运行成功
- 报告状态: degraded
- comparison_status: ok
- rotation_summary 包含轮动信息

## 12. lookback CLI 结果

```bash
python -m theme_sector_radar.cli --as-of 2026-06-28 --top-n 10 --offline-fixture --fixture-profile rotation-day2 --lookback-days 5 --output reports/theme_sector_radar/2026-06-28-rotation-lookback
```

**结果**: ✅ 运行成功
- 自动找到最近可用的历史快照
- rotation_summary 包含轮动信息

## 13. Markdown 轮动章节示例

```markdown
## 板块轮动变化

**对比日期**: 2026-06-27

### 新晋 Top N
- 芯片
- 光伏概念

### 快速升温
- 电力设备 (排名上升)
- CPO概念 (评分上升)
- ChatGPT概念 (评分上升)
- 元宇宙 (评分上升)

### 连续强势
- 半导体 (连续 2 期 Top N)
- 人工智能 (连续 2 期 Top N)
- CPO概念 (连续 2 期 Top N)
- ChatGPT概念 (连续 2 期 Top N)

### 掉出 Top N
- 传媒
- 大数据
```

## 14. 是否仍然完全未修改原 ai-hedge-fund 项目

**✅ 完全未修改**

原项目 `E:\Workspace\ai-stock-projects\ai-hedge-fund` 的文件未被修改：
- `src/main.py` - 未修改
- `src/agents/common.py` - 未修改

## 15. 硬性边界遵守情况

- ✅ 不允许修改 `E:\Workspace\ai-stock-projects\ai-hedge-fund`
- ✅ 不允许接入 LangGraph
- ✅ 不允许注册到 `ANALYST_CONFIG`
- ✅ 不允许输出个股推荐
- ✅ 不允许输出 buy/sell/hold
- ✅ 不允许输出买入、卖出、持有建议
- ✅ 不允许自动交易
