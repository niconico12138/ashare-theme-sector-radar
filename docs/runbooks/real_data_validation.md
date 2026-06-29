# 真实数据验证操作手册

## 1. 每天盘后运行

### 1.1 运行真实 AkShare 日报

```powershell
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/run_daily.ps1
```

或直接运行 CLI：

```bash
python -m theme_sector_radar.cli --daily --as-of YYYY-MM-DD --provider akshare --refresh --lookback-days 5 --report-root reports/theme_sector_radar
```

### 1.2 配置文件

确保 `config/daily.local.json` 或 `config/daily.example.json` 配置正确：

```json
{
  "as_of": "auto",
  "provider": "akshare",
  "refresh": true,
  "fallback_cache_days": 7,
  "lookback_days": 5,
  "report_root": "reports/theme_sector_radar",
  "top_n": 10,
  "offline_fixture": false,
  "fixture_profile": null,
  "log_root": "logs/daily_runs"
}
```

## 2. 确认 AkShare Daily 成功

### 2.1 检查 run_log.json

```bash
cat reports/theme_sector_radar/YYYY-MM-DD/run_log.json
```

确认以下字段：
- `status`: 应为 "ok" 或 "degraded"
- `provider`: 应为 "akshare"
- `data_source_mode`: 应为 "akshare_refresh" 或 "cache_fallback"

### 2.2 检查报告状态

```bash
cat reports/theme_sector_radar/YYYY-MM-DD/theme_sector_radar.json | jq '.status'
```

## 3. 确认 data_cache 存在

### 3.1 检查缓存文件

```bash
ls -la data_cache/YYYY-MM-DD/raw_snapshot.json
```

### 3.2 检查缓存内容

```bash
cat data_cache/YYYY-MM-DD/raw_snapshot.json | jq '.as_of_date'
```

## 4. 确认报告可读

### 4.1 打开 Markdown 报告

```powershell
# Windows
Start-Process "reports\theme_sector_radar\YYYY-MM-DD\theme_sector_radar.md"

# 或查看内容
cat reports/theme_sector_radar/YYYY-MM-DD/theme_sector_radar.md
```

### 4.2 检查报告结构

确认报告包含：
- 市场短线温度
- 行业板块 Top N
- 概念板块 Top N
- 行业 + 概念共振
- 数据完整性
- 风险提示
- 声明

## 5. 记录人工观察结论

### 5.1 使用人工验收模板

复制模板：
```bash
cp docs/templates/daily_manual_review_template.md docs/reviews/daily/YYYY-MM-DD-review.md
```

### 5.2 填写模板

按模板字段逐一填写：
- 日期
- 市场温度是否符合盘感
- 行业 Top N 是否合理
- 概念 Top N 是否合理
- 轮动变化是否有解释力
- 风险提示是否充分
- 数据质量问题
- 是否有明显误判
- 备注

## 6. 多日权重实验

### 6.1 前提条件

- 连续 3-5 个真实交易日成功运行
- data_cache 中有足够数据

### 6.2 运行多日权重实验

```bash
python -m theme_sector_radar.experiments.weight_comparison \
  --start-date 2026-06-24 \
  --end-date 2026-06-28 \
  --use-cache \
  --output reports/experiments/weights/2026-06-24_to_2026-06-28-cache
```

### 6.3 查看实验结果

```bash
cat reports/experiments/weights/2026-06-24_to_2026-06-28-cache/multi_day_summary.md
```

## 7. 常见问题

### 7.1 AkShare 网络失败

- 检查网络连接
- 查看 run_log.json 中的 warnings
- 使用 `--use-cache` 优先使用缓存

### 7.2 报告 status=degraded

- 检查 data_completeness 字段
- 查看 warnings 了解具体问题
- 运行 fixture smoke test 验证环境

### 7.3 data_cache 不存在

- 确认 run_daily.ps1 运行成功
- 检查 config 中的 provider 设置
- 查看 logs/daily_runs/ 中的脚本日志
