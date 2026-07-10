# Phase 1-13 完整集成测试验收报告

**测试时间**: 2026-07-04 15:30-15:50  
**测试人**: Claude Code  
**项目**: market_data_service + theme-sector-radar-dev  
**测试类型**: 完整手动回归  

---

## 1. 测试环境

| 组件 | 状态 | 详情 |
|------|------|------|
| StockDB (127.0.0.1:7899) | ✅ 运行中 | PID 3988, latest_daily_date=20260702 |
| market_data_service API | ✅ 运行中 | http://127.0.0.1:8000 |
| Eastmoney EM | ❌ 不可用 | ProxyError: push2.eastmoney.com blocked |
| AkShare THS | ✅ 可用 | 90 industries, 374 concepts |
| local_industry_members | ✅ 可用 | 31 SW industries, 5,197 stocks |

## 2. API 端点测试

| 端点 | 状态 | 详情 |
|------|------|------|
| `GET /health` | 200 ✅ | stockdb=ok, akshare_ths=ok, eastmoney_em=unavailable |
| `GET /stocks/600633/bars?start=20260701&end=20260702` | 200 ✅ | 2 bars |
| `GET /boards/industry/半导体/constituents` | 200 ✅ | X-Data-Source: local_industry_members, 481 stocks |
| `GET /boards/concept/人工智能/constituents` | 200 ✅ | X-Data-Source: mapping, 8 stocks |
| 是否仍有 503 | 0 个 | ✅ 所有测试端点均返回 200 |

## 3. 测试套件结果

| 项目 | 测试数 | 结果 |
|------|--------|------|
| market_data_service | **290 passed** | ✅ 0 failures |
| theme-sector-radar-dev | **966 passed** | ✅ 0 failures, 零回归 |

## 4. 桥接与联合管线 Smoke

### sector_stock_bridge.py
```
成分股来源: {
  "http_em": 0,
  "http_stale": 0,
  "http_mapping": 0,
  "http_local_industry": 10,    ← 全部真实本地数据
  "local_emergency_mapping": 0,
  "unavailable": 0              ← 零 unavailable
}
```

### unified_pipeline.py
- 10/10 行业 `http_local_industry` ✅
- 趋势 973 stocks, 短线 959 stocks ✅
- 量化评分: 411 trend + 340 burst stocks ✅
- **健康门禁: PASS** ✅

### 数据来源 Markdown
- "数据来源状态" 小节 ✅
- "数据健康门禁" ✅
- http_local_industry 正确展示 ✅

## 5. Daily + Unified 集成报告

| 检查项 | 结果 |
|--------|------|
| JSON 含 `unified_observation_pool` | ✅ |
| JSON 含 `unified_data_source` | ✅ |
| JSON 含 `unified_run_health` | ✅ |
| Markdown 含 "联合观察池" 小节 | ✅ |
| Markdown 含 "趋势观察候选" | ✅ |
| Markdown 含 "短线观察候选" | ✅ |
| 用词为 "观察池/候选" (非推荐) | ✅ |
| 用词含免责声明 | ✅ |

## 6. 一键运行脚本

| 检查项 | 结果 |
|--------|------|
| 前置检查 | ✅ StockDB + API |
| Pipeline 执行 | ✅ |
| **健康门禁: PASS** | ✅ |
| 索引追加 | ✅ unified_runs_index.jsonl |
| 报告路径输出 | ✅ |

### --show-history 10
```
健康分布: PASS=10  WARN=0  FAIL=0
最新状态: ✅ PASS
成分股来源汇总: http_local_industry=100, mapping=0
(NO "离线映射" warning)
```
- 不再误报"全部依赖离线 mapping" ✅
- 连续上榜候选正常显示 ✅
- source summary 使用 `local_ind` 短标签 ✅

## 7. 当前健康状态

| 维度 | 状态 | 备注 |
|------|------|------|
| 行业成分股 | ✅ PASS | local_industry_members (真实本地数据) |
| 概念成分股 | ⚠️ mapping | 无稳定真实源，依靠离线映射 |
| 个股 K 线 | ✅ PASS | http_enhanced (StockDB) |
| 健康门禁 | ✅ PASS | 行业主导，无 unavailable |

## 8. 剩余风险

| 风险 | 级别 | 说明 |
|------|------|------|
| EM 不可用 | ⚠️ 中 | Eastmoney 封锁，行业已由 local_industry 弥补 |
| 概念板块 mapping 依赖 | ⚠️ 中低 | 概念板块无真实源，依赖 hand-curated mapping |
| 资金流数据不可用 | ⚠️ 低 | 全部降级为 neutral |
| 暂无 unavailable 板块 | ✅ | 所有 Top 行业板块均被 local_industry 覆盖 |

## 9. 最终结论

**PASS** ✅

当前系统可以作为本地盘后手动运行流程使用：

```bash
# 一键运行（推荐）
cd <path-to-a-share-theme-sector-radar>
python scripts/run_daily_unified_pipeline.py --as-of 2026-07-02 --mode quick

# 查看历史
python scripts/run_daily_unified_pipeline.py --show-history 10

# Daily + 联合观察池（完整报告）
python -m theme_sector_radar.cli --daily --as-of 2026-07-02 \
  --offline-fixture --fixture-profile full --lookback-days 5 \
  --report-root reports/theme_sector_radar \
  --include-unified-pipeline --unified-mode quick
```

