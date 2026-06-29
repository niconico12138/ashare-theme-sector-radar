# Phase 6 AkShare Daily 验证报告

日期：2026-06-29  
状态：网络不稳定，使用离线模式验证

## 1. 网络状况

当前环境网络连接不稳定，AkShare 接口调用失败：
```
ProxyError: Unable to connect to proxy
```

## 2. 离线模式验证

### 2.1 Daily 模式 (fixture)
```bash
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --offline-fixture --fixture-profile rotation-day2 --lookback-days 5 --report-root reports/theme_sector_radar
```

**结果**: ✅ 成功
- 生成 theme_sector_radar.json
- 生成 theme_sector_radar.md
- 生成 raw_snapshot.json
- 生成 run_log.json

### 2.2 Replay-cache 模式
```bash
python -m theme_sector_radar.cli --replay-cache --start-date 2026-06-27 --end-date 2026-06-28 --lookback-days 5 --report-root reports/theme_sector_radar
```

**结果**: ✅ 成功
- 生成 index.json
- 生成 index.md
- 回放 2 天数据

## 3. run_log 验证

### 3.1 run_log.json 内容
```json
{
  "command_args": "--daily --as-of 2026-06-28 --offline-fixture --fixture-profile rotation-day2 --lookback-days 5 --report-root reports/theme_sector_radar",
  "started_at": "2026-06-29T11:26:32.796353",
  "finished_at": "2026-06-29T11:26:32.810979",
  "duration_ms": 14,
  "provider": "fixture",
  "status": "degraded",
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

### 3.2 验证结果
- ✅ command_args 记录完整
- ✅ started_at/finished_at 时间戳正确
- ✅ duration_ms 计算正确
- ✅ status 记录正确
- ✅ output_files 列表完整

## 4. 索引验证

### 4.1 index.json
- ✅ generated_at 时间戳正确
- ✅ report_root 路径正确
- ✅ reports 列表包含每日报告信息

### 4.2 index.md
- ✅ 表格格式正确
- ✅ 包含日期、状态、数据质量、市场温度等列
- ✅ 包含报告链接

## 5. 结论

### 5.1 已验证功能
- ✅ --daily 参数可用
- ✅ daily 输出固定 YYYY-MM-DD 目录
- ✅ run_log.json 生成且字段完整
- ✅ --replay-cache 不调用网络接口
- ✅ index.json 生成且包含多日报告
- ✅ index.md 生成且表格可读
- ✅ 报告不包含 buy/sell/hold

### 5.2 待网络恢复后验证
- AkShare daily 模式
- 真实数据缓存写入
- 网络失败降级策略

## 6. 建议

当网络恢复后，运行以下命令验证真实 AkShare daily：
```bash
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --provider akshare --refresh --fallback-cache-days 7 --lookback-days 5 --report-root reports/theme_sector_radar
```
