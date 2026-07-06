# Phase 13: Daily 报告集成 Unified Pipeline 验收报告

**日期**: 2026-07-04  
**验收人**: Claude Code  
**项目**: theme-sector-radar-dev

---

## 1. 改动范围

| 文件 | 改动 |
|------|------|
| `theme_sector_radar/models.py` | `RadarReport` 新增 4 个 optional 字段 |
| `theme_sector_radar/cli.py` | 新增 `_build_unified_markdown_section()` + 集成逻辑 + 2 个 CLI 参数 |
| `theme_sector_radar/reports/*` | **未改** (通过后处理追加，不触碰报告生成器) |

## 2. 新增 CLI 参数

| 参数 | 说明 |
|------|------|
| `--include-unified-pipeline` | 在 daily 报告中嵌入 unified_pipeline 结果 |
| `--unified-mode quick\|deep` | unified_pipeline 模式 (默认 quick) |

**默认行为不变**: 不带 `--include-unified-pipeline` 时，现有 `--daily` 行为完全不变。

## 3. 集成流程

```
daily 主流程完成 (报告已保存)
  ↓
  if --include-unified-pipeline:
    ↓
    run unified_pipeline.py (quick mode)
    ↓
    ├─ 成功: 后处理 JSON + Markdown
    │   - JSON: unified_observation_pool / unified_data_source / unified_run_health
    │   - MD: 追加 "## 联合观察池" 小节
    │
    └─ 失败: unified_pipeline_error 记录，主流程不受影响
```

## 4. JSON 报告新增字段

```json
{
  "unified_observation_pool": {
    "trend_top_stocks": [...],
    "burst_top_stocks": [...],
    "as_of_date": "2026-07-02",
    "mode": "quick"
  },
  "unified_data_source": { ... },
  "unified_run_health": { ... }
}
```

## 5. Markdown 报告新增小节

```markdown
## 联合观察池 (Unified Pipeline)

> ⚠️ 不作为操作依据或买卖推荐。

### ⚠️ 健康门禁: WARN
- 全部成分股来源于离线映射...

### 数据来源
- 成分股来源: http_mapping=10
- 量化评分: http_enhanced=44

### 趋势观察候选 Top10
| # | 代码 | 名称 | 综合分 | ...
```

## 6. Smoke 验证

```bash
python -m theme_sector_radar.cli --daily --as-of 2026-07-02 \
  --offline-fixture --fixture-profile full --lookback-days 5 \
  --report-root reports/theme_sector_radar \
  --include-unified-pipeline --unified-mode quick
```

输出:
```
  ✅ JSON 报告已更新 (含联合观察池)
  ✅ Markdown 报告已更新 (含联合观察池)
  Unified Pipeline 完成: 健康门禁 WARN
```

## 7. 失败隔离

| 场景 | 主流程 | unified 结果 |
|------|--------|-------------|
| unified_pipeline 正常 | ✅ 完成 | ✅ 嵌入 |
| unified_pipeline 抛异常 | ✅ 完成 | ⚠️ error 记录 |
| unified_pipeline status != ok | ✅ 完成 | ⚠️ warnings 记录 |

## 8. 测试结果

| 命令 | 结果 |
|------|------|
| `pytest tests/theme_sector_radar/ -q` | **966 passed，零回归** |
| `smoke: --include-unified-pipeline` | ✅ JSON + MD 均已更新 |
