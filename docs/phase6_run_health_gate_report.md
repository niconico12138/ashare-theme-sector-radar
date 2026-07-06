# Phase 6: 每日运行健康门禁 验收报告

**日期**: 2026-07-04  
**验收人**: Claude Code  
**项目**: theme-sector-radar-dev

---

## 1. 新增功能

### `evaluate_run_health(data_source) -> dict`

判断当天 unified_pipeline 输出是否适合日常观察。

**判定规则**:

| 级别 | 条件 |
|------|------|
| **FAIL** | unavailable 占比 ≥ 30% |
| | emergency fallback 占比 ≥ 50% |
| | fallback quant 占比 ≥ 50% |
| **WARN** | 有 unavailable (< 30%) |
| | 有 emergency fallback (< 50%) |
| | 有 fallback quant (< 50%) |
| | 全部 http_mapping 且无 EM（离线映射依赖） |
| **PASS** | 无 unavailable, 无 emergency, quant 主要为 http_enhanced |

**输出结构**:
```json
{
  "status": "pass" | "warn" | "fail",
  "reasons": ["..."],
  "metrics": {
    "total_constituent_sectors": 10,
    "unavailable_sectors": 0,
    "emergency_fallback_sectors": 0,
    "http_enhanced_stocks": 44,
    "fallback_quant_stocks": 0
  }
}
```

## 2. 集成点

| 位置 | 展示 |
|------|------|
| `result["run_health"]` | 完整 health 结构 |
| `unified_report.json` | `run_health` 字段 |
| `unified_report.md` | `**⚠️ 数据健康门禁**: WARN` + reason 列表 |
| CLI 摘要 | `⚠️ 健康门禁: WARN` + reason 列表 |

## 3. 当前 Smoke 状态

```
⚠️ 健康门禁: WARN
  - 全部成分股来源于离线映射 (http_mapping)，EM 可能不可用
```

**解释**: EM 被代理封锁，所有 10 个板块通过 market_data_service offline mapping 获取 — 属于 WARN 级别。

## 4. 测试结果

| 命令 | 结果 |
|------|------|
| `pytest tests/.../test_unified_bridge.py -v -q` | **55 passed** (+10 Phase 6) |
| `pytest tests/theme_sector_radar/ -q` | **925 passed，零回归** |
| `unified_pipeline.py --as-of 2026-07-02 --mode quick` | ✅ WARN, 报告含 health |

### 新增测试 (10 个)
- `test_pass_all_healthy` — 全部健康 → PASS
- `test_pass_with_http_em` — 有 EM 有 mapping → PASS
- `test_warn_all_http_mapping_no_em` — 全部 mapping → WARN
- `test_warn_some_unavailable` — 少量 unavailable → WARN
- `test_warn_some_emergency` — 少量 emergency → WARN
- `test_warn_some_fallback_quant` — 少量 fallback quant → WARN
- `test_fail_unavailable_over_threshold` — unavailable ≥ 30% → FAIL
- `test_fail_emergency_over_threshold` — emergency ≥ 50% → FAIL
- `test_fail_fallback_quant_over_threshold` — fallback quant ≥ 50% → FAIL
- `test_health_metrics_fields` — metrics 字段完整

## 5. 各种场景预期行为

| 场景 | 门禁结果 |
|------|---------|
| EM 正常，部分 mapping | PASS |
| EM 完全不可用，全部 mapping (当前) | WARN |
| 少量板块无数据 | WARN |
| 1/3 板块无数据 | FAIL |
| market_data_service 不可达，本地 emergency | WARN (少量) / FAIL (≥50%) |
| StockDB 不可用，fallback quant 为主 | FAIL (≥50%) |
