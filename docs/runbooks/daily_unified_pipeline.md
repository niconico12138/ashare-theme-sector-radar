# 每日运行 Unified Pipeline Runbook

## 概述

每日盘后运行 `unified_pipeline.py`（quick 模式）生成板块→个股联合选股报告。

## 前置条件

| 组件 | 默认地址 | 用途 |
|------|---------|------|
| StockDB | 127.0.0.1:7899 | 个股日 K 线数据 |
| market_data_service API | http://127.0.0.1:8000 | 板块成分股、行业总览 |

## 一键运行

```powershell
cd E:\liaohua\01_projects\theme-sector-radar-dev
python scripts/run_daily_unified_pipeline.py
```

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--as-of YYYY-MM-DD` | 今天 | 分析日期 |
| `--mode quick` | quick | quick=快速筛选, deep=完整分析 |
| `--api-url URL` | http://127.0.0.1:8000 | market_data_service 地址 |
| `--fail-on-health-fail` | 关闭 | health=fail 时 exit code=2 |
| `--output-dir PATH` | auto | 覆盖输出目录 |

## 退出码

| 码 | 含义 |
|----|------|
| 0 | 成功 |
| 1 | API 不可达 |
| 2 | 健康门禁 FAIL (需 --fail-on-health-fail) |
| other | unified_pipeline.py 错误 |

## 启动服务

### 启动 market_data_service API

```powershell
cd E:\liaohua\01_projects\market_data_service
python -m market_data_service.api_server --host 127.0.0.1 --port 8000
```

### 验证 API 健康

```powershell
python -c "from theme_sector_radar.data.market_data_http_client import MarketDataHttpClient; c=MarketDataHttpClient(); print(c.health_check())"
```

## 典型执行流程

```
======================================================================
  Unified Pipeline — 每日盘后执行
  时间: 2026-07-04 15:15:00
======================================================================

── 前置检查 ──
  ✅ StockDB (127.0.0.1:7899): 可连接
  ✅ market_data_service API (http://127.0.0.1:8000): {"stockdb":{"ok":true},...}

── 运行 Unified Pipeline ──

  [1/5] 读取板块评分报告...
  [2/5] 查询板块成分股...
    ✅ 半导体: 10 只成分股 [http_mapping]
    ...
  [3/5] 获取成分股行情...
  [4/5] 获取资金流数据...
  [5/5] 计算板块关联度...
  ✅ 桥接完成
  📊 Step 2: 个股量化评分
  📁 Step 3: 生成报告

📁 报告路径: reports/unified/2026-07-04/unified_report.json

──────────────────────────────────────────────────────
  运行摘要
──────────────────────────────────────────────────────
⚠️ 健康门禁: WARN
    - 全部成分股来源于离线映射 (http_mapping)，EM 可能不可用
  成分股来源: {"http_mapping": 10, ...}
  量化评分来源: {"http_enhanced": 44}

⚠️ 健康门禁 WARN — 数据可能降级，请检查报告
✅ 每日运行完成
```

## 报告文件

| 文件 | 路径 |
|------|------|
| JSON 报告 | `reports/unified/{date}/unified_report.json` |
| Markdown 报告 | `reports/unified/{date}/unified_report.md` |
| 桥接结果 | `reports/bridge/{date}/bridge_result.json` |

## 健康门禁状态

| 状态 | 含义 | 操作 |
|------|------|------|
| **PASS** | 数据源正常 | 无需操作 |
| **WARN** | 数据源降级（如离线映射、少量缺失） | 检查报告，关注降级原因 |
| **FAIL** | 数据源严重不足 | 检查 StockDB/API/网络，等待恢复后重跑 |

## 定时任务 (Windows)

在任务计划程序中创建每日 15:30 盘后任务：

```powershell
# 创建任务（需管理员）
$Action = New-ScheduledTaskAction -Execute "python" `
  -Argument "scripts/run_daily_unified_pipeline.py --fail-on-health-fail" `
  -WorkingDirectory "E:\liaohua\01_projects\theme-sector-radar-dev"

$Trigger = New-ScheduledTaskTrigger -Daily -At "15:30"

Register-ScheduledTask -TaskName "ThemeSectorRadarDaily" `
  -Action $Action -Trigger $Trigger -Description "每日板块雷达联合选股"
```

## 故障排除

| 症状 | 可能原因 | 解决 |
|------|---------|------|
| API 不可达 | market_data_service 未启动 | 启动 API server |
| StockDB 不可达 | stockdb.exe 未运行 | 启动 StockDB |
| 全部 http_mapping (WARN) | Eastmoney EM 被代理封锁 | 预期行为，mapping 数据已覆盖 107 板块 |
| 多个 unavailable (FAIL) | 板块不在 mapping 中 | 扩充 constituents_mapping.json |
| fallback quant > 50% (FAIL) | StockDB 无数据 | 检查 StockDB 和网络 |
