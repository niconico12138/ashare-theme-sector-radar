# Phase 6 真实 AkShare 多日缓存回放与盘后日报工作流计划

日期：2026-06-29  
目标：把 theme_sector_radar 从"开发验证工具"推进到"可每天盘后运行的板块雷达日报工具"

## 1. daily run 工作流

### 1.1 标准盘后日报命令
```bash
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --provider akshare --refresh --fallback-cache-days 7 --lookback-days 5 --report-root reports/theme_sector_radar
```

### 1.2 输出目录
```
reports/theme_sector_radar/YYYY-MM-DD/
  ├── theme_sector_radar.json
  ├── theme_sector_radar.md
  ├── raw_snapshot.json
  └── run_log.json
```

## 2. AkShare refresh/cache/replay 三种模式

| 模式 | 参数 | 说明 |
|------|------|------|
| refresh | --provider akshare --refresh | 强制刷新，访问网络 |
| cache | --provider akshare --use-cache | 优先使用缓存 |
| replay | --replay-cache | 不访问网络，只读取已有缓存 |

## 3. 多日缓存回放策略

### 3.1 replay-cache 模式
```bash
python -m theme_sector_radar.cli --replay-cache --start-date 2026-06-24 --end-date 2026-06-28 --lookback-days 5 --report-root reports/theme_sector_radar
```

### 3.2 回放逻辑
1. 不访问网络
2. 只读取 data_cache 或 reports 中已有快照
3. 每天生成或重建对应报告
4. 每天自动比较最近可用前一日报告
5. 如果某天缺数据，生成 degraded/failed run_log，不影响后续日期

## 4. report index 设计

### 4.1 index.json
```json
{
  "generated_at": "2026-06-29T10:00:00",
  "report_root": "reports/theme_sector_radar",
  "reports": [
    {
      "as_of_date": "2026-06-28",
      "status": "ok",
      "data_quality_score": 85.0,
      "market_temperature_label": "warm",
      "top_industries": ["人工智能", "半导体", "芯片"],
      "top_concepts": ["CPO概念", "ChatGPT概念", "人工智能概念"],
      "new_entries": ["芯片"],
      "rising_fast": ["锂电池"],
      "persistent_strength": ["半导体", "人工智能"],
      "risk_up": [],
      "report_path": "reports/theme_sector_radar/2026-06-28/theme_sector_radar.json",
      "markdown_path": "reports/theme_sector_radar/2026-06-28/theme_sector_radar.md",
      "run_log_path": "reports/theme_sector_radar/2026-06-28/run_log.json"
    }
  ]
}
```

### 4.2 index.md
```markdown
# A股行业/概念板块雷达日报索引

| 日期 | 状态 | 数据质量 | 市场温度 | 行业前三 | 概念前三 | 新晋 | 快速升温 | 风险升高 | 报告 |
|------|------|---------|---------|---------|---------|------|---------|---------|------|
| 2026-06-28 | ok | 85 | warm | 人工智能, 半导体, 芯片 | CPO概念, ChatGPT概念 | 芯片 | 锂电池 | - | [链接](2026-06-28/theme_sector_radar.md) |
```

## 5. run_log 设计

### 5.1 run_log.json 字段
```json
{
  "command_args": "--daily --as-of 2026-06-28 --provider akshare --refresh",
  "started_at": "2026-06-29T10:00:00",
  "finished_at": "2026-06-29T10:00:30",
  "duration_ms": 30000,
  "provider": "akshare",
  "status": "ok",
  "comparison_status": "ok",
  "cache_fallback_used": false,
  "warnings": [],
  "output_files": [
    "theme_sector_radar.json",
    "theme_sector_radar.md",
    "raw_snapshot.json"
  ]
}
```

## 6. 网络失败降级策略

### 6.1 降级逻辑
1. 网络失败时尝试 fallback cache
2. 如果 fallback cache 也不存在，生成 degraded 报告
3. run_log 记录失败原因
4. 不影响后续日期的报告生成

### 6.2 run_log 状态
- ok: 正常完成
- degraded: 部分数据缺失
- failed: 严重失败

## 7. CLI 命令设计

### 7.1 新增参数
- `--daily`: 日报模式
- `--replay-cache`: 缓存回放模式
- `--start-date`: 开始日期
- `--end-date`: 结束日期
- `--report-root`: 报告根目录

### 7.2 默认值
- `--report-root`: reports/theme_sector_radar
- `--lookback-days`: 5
- `--fallback-cache-days`: 7

## 8. 测试与验收命令

```bash
# 默认测试
python -m pytest tests/theme_sector_radar/ -v

# fixture daily
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --offline-fixture --fixture-profile rotation-day2 --lookback-days 5 --report-root reports/theme_sector_radar

# replay-cache
python -m theme_sector_radar.cli --replay-cache --start-date 2026-06-27 --end-date 2026-06-28 --lookback-days 5 --report-root reports/theme_sector_radar

# AkShare daily (如果网络可用)
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --provider akshare --refresh --fallback-cache-days 7 --lookback-days 5 --report-root reports/theme_sector_radar
```
