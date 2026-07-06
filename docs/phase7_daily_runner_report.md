# Phase 7: 一键运行脚本与每日运行 Runbook 验收报告

**日期**: 2026-07-04  
**验收人**: Claude Code  
**项目**: theme-sector-radar-dev

---

## 1. 新增文件

| 文件 | 说明 |
|------|------|
| `scripts/run_daily_unified_pipeline.py` | 每日一键运行 Python 脚本 |
| `docs/runbooks/daily_unified_pipeline.md` | 每日运行 Runbook 文档 |

## 2. 脚本功能

### 前置检查
- StockDB (127.0.0.1:7899) TCP 端口检查
- market_data_service API (http://127.0.0.1:8000) health check

### 主流程
1. 前置检查通过 → 运行 `unified_pipeline.py` (quick mode)
2. 读取输出 JSON 报告
3. 打印运行摘要（健康门禁、数据来源、量化评分来源）
4. 根据 `--fail-on-health-fail` 决定退出码

### 退出码

| 码 | 含义 |
|----|------|
| 0 | 成功（含 WARN） |
| 1 | API 不可达 |
| 2 | 健康门禁 FAIL (需 `--fail-on-health-fail`) |

### 参数

| 参数 | 默认值 |
|------|--------|
| `--as-of` | 今天 |
| `--mode` | quick |
| `--api-url` | http://127.0.0.1:8000 |
| `--fail-on-health-fail` | 关闭 |
| `--output-dir` | auto |

## 3. Smoke 验证

```
python scripts/run_daily_unified_pipeline.py --as-of 2026-07-02 --mode quick

── 前置检查 ──
  ✅ StockDB (127.0.0.1:7899): 可连接
  ✅ market_data_service API: 可访问

── 运行摘要 ──
⚠️ 健康门禁: WARN
  - 全部成分股来源于离线映射 (http_mapping)，EM 可能不可用
  成分股来源: {"http_mapping": 10, ...}
  量化评分来源: {"http_enhanced": 44}

✅ 每日运行完成
```

## 4. 测试结果

| 命令 | 结果 |
|------|------|
| `pytest tests/.../test_unified_bridge.py -v -q` | **65 passed** (+10 Phase 7) |
| `pytest tests/theme_sector_radar/ -q` | **935 passed，零回归** |
| `run_daily_unified_pipeline.py smoke` | ✅ exit 0, 含健康门禁 |

### 新增测试 (10 个)
- `test_check_tcp_port_localhost` — TCP 端口检查不崩溃
- `test_check_tcp_port_closed` — 关闭端口返回 False
- `test_check_http_health_api_url` — API health check 成功
- `test_check_http_health_unreachable` — API 不可达返回 False
- `test_find_latest_report` — 查找报告文件
- `test_load_report_has_required_fields` — 报告含 run_health + data_source
- `test_main_help_does_not_crash` — --help exit 0
- `test_main_api_unreachable` — API 不可达 exit 1
- `test_main_api_ok_runs_pipeline` — API OK → 正常执行
- `test_main_fail_on_health_fail_flag` — --fail-on-health-fail 参数接受

## 5. Runbook 内容

[docs/runbooks/daily_unified_pipeline.md](E:\liaohua\01_projects\theme-sector-radar-dev\docs\runbooks\daily_unified_pipeline.md) 包含：
- 前置条件（StockDB, API）
- 一键运行命令
- 参数说明
- 退出码说明
- 服务启动命令
- 典型执行输出
- 报告文件路径
- 健康门禁状态解读
- Windows 任务计划程序配置
- 故障排除指南

## 6. Bug 修复

| Bug | 修复 |
|-----|------|
| 脚本 emoji 打印 GBK 崩溃 | 添加 `sys.stdout.reconfigure(encoding='utf-8')` |
| subprocess GBK 解码失败 | 添加 `encoding="utf-8"` 到 `subprocess.run()` |
