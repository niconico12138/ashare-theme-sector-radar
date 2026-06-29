# 故障排查指南

## 1. AkShare 网络失败

### 1.1 症状
```
ProxyError: Unable to connect to proxy
HTTPSConnectionPool... Max retries exceeded
```

### 1.2 原因
- 网络连接问题
- 代理配置问题
- 防火墙阻止

### 1.3 解决方案
1. 检查网络连接
2. 运行 fixture smoke test 验证环境
3. 使用 `--use-cache` 优先使用缓存
4. 检查 `--fallback-cache-days` 配置

## 2. ProxyError

### 2.1 症状
```
ProxyError('Unable to connect to proxy', RemoteDisconnected(...))
```

### 2.2 解决方案
1. 检查系统代理设置
2. 临时禁用代理:
   ```powershell
   $env:HTTP_PROXY = ""
   $env:HTTPS_PROXY = ""
   ```
3. 使用离线 fixture 模式

## 3. 找不到 Python

### 3.1 症状
```
python: command not found
```

### 3.2 解决方案
1. 检查 Python 安装
2. 使用完整路径:
   ```powershell
   C:\Python311\python.exe -m theme_sector_radar.cli ...
   ```
3. 添加 Python 到 PATH

## 4. akshare 未安装

### 4.1 症状
```
ModuleNotFoundError: No module named 'akshare'
```

### 4.2 解决方案
```bash
pip install akshare
```

## 5. 报告 status=degraded

### 5.1 原因
- 数据数量不足
- 部分接口失败
- 数据质量问题

### 5.2 检查方法
1. 查看 run_log.json 中的 warnings
2. 检查 theme_sector_radar.json 中的 data_completeness
3. 运行 fixture smoke test 对比

## 6. Index 未更新

### 6.1 原因
- 报告目录不是标准 YYYY-MM-DD 格式
- 报告文件不存在

### 6.2 解决方案
1. 确保报告目录格式正确
2. 重新运行 replay-cache:
   ```bash
   python -m theme_sector_radar.cli --replay-cache --start-date 2026-06-24 --end-date 2026-06-28 --report-root reports/theme_sector_radar
   ```

## 7. 数据来源串台排查

### 7.1 检查 JSON 报告
```json
{
  "provider": "fixture",  // 或 "akshare"
  "offline_fixture": true,  // 或 false
  "fixture_profile": "rotation-day2",  // 或 null
  "data_source_mode": "fixture"  // 或 "akshare_refresh" 等
}
```

### 7.2 检查 run_log
```json
{
  "provider": "fixture",
  "offline_fixture": true,
  "fixture_profile": "rotation-day2",
  "data_source_mode": "fixture",
  "input_snapshot_source": "fixture"
}
```

### 7.3 验证 fixture_profile
```bash
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --offline-fixture --fixture-profile rotation-day2 --report-root reports/theme_sector_radar
```

检查报告中 concept_top 是否来自 rotation-day2 fixture。

## 8. 运行 Fixture Smoke Test

### 8.1 目的
验证环境和日报链路正常

### 8.2 运行方式
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_daily_fixture.ps1
```

### 8.3 预期结果
- 状态: degraded（fixture 数据数量不足）
- fixture_profile: rotation-day2
- concept_top: CPO概念, ChatGPT概念, 人工智能概念

### 8.4 如果失败
1. 检查 Python 环境
2. 检查 theme_sector_radar 包是否正确安装
3. 查看错误信息
