# Phase 5: 数据来源透明化与报告标记 验收报告

**日期**: 2026-07-04  
**验收人**: Claude Code  
**项目**: theme-sector-radar-dev

---

## 1. 改动范围

| 文件 | 改动 |
|------|------|
| `sector_stock_bridge.py` | 新增 `constituent_source_summary` 到桥接输出，Step 2 中按 source 标签计数 |
| `unified_pipeline.py` | 新增 `data_source` 字段到 result 和 JSON 报告；新增 "数据来源状态" 小节到 Markdown |
| `tests/test_unified_bridge.py` | 新增 6 个 Phase 5 测试（TestSourceTransparency） |

## 2. 新增输出结构

### JSON 报告 (`unified_report.json`)
```json
{
  "data_source": {
    "constituent_sources": {
      "http_em": 0,
      "http_stale": 0,
      "http_mapping": 10,
      "local_emergency_mapping": 0,
      "unavailable": 0
    },
    "quant_score_sources": {
      "http_enhanced": 44
    },
    "has_unavailable_sectors": false,
    "has_emergency_fallback": false
  },
  "bridge_summary": {
    "constituent_source_summary": { ... }
  }
}
```

### Markdown 报告 — 新增"数据来源状态"小节
```markdown
## 数据来源状态

| 来源 | 板块数 |
|------|--------|
| ✅ http_em | 0 |
| ✅ http_stale | 0 |
| ✅ http_mapping | 10 |
| ⚠️ local_emergency_mapping | 0 |
| ❌ unavailable | 0 |

✅ 所有板块成分股数据正常获取。

| 量化评分来源 | 个股数 |
|-------------|--------|
| ✅ http_enhanced | 44 |
```

### 桥接 CLI 摘要
```
成分股来源: {"http_em": 0, "http_stale": 0, "http_mapping": 10, "local_emergency_mapping": 0, "unavailable": 0}
```

## 3. 支持的 5 种来源标签

| 标签 | 含义 |
|------|------|
| `http_em` | HTTP API → market_data_service → Eastmoney EM 直接成功 |
| `http_stale` | HTTP API → market_data_service → stale cache (EM 过期缓存) |
| `http_mapping` | HTTP API → market_data_service → offline mapping |
| `local_emergency_mapping` | HTTP API 不可达 → 本地 SECTOR_STOCK_MAPPING |
| `unavailable` | 所有来源均无数据 |

## 4. Smoke 验证

| 检查项 | 结果 |
|--------|------|
| `sector_stock_bridge.py` CLI 摘要输出 source summary | ✅ `{"http_mapping": 10, ...}` |
| `unified_report.json` 含 `data_source` 字段 | ✅ 含 constituent_sources + quant_score_sources |
| `bridge_summary.constituent_source_summary` | ✅ 与 bridge 输出一致 |
| `unified_report.md` 含 "数据来源状态" 小节 | ✅ 含来源表格 + 量化评分表格 |
| `has_unavailable_sectors` | ✅ false (本次 0 unavailable) |
| `has_emergency_fallback` | ✅ false (本次 0 emergency) |

## 5. 测试结果

| 命令 | 结果 |
|------|------|
| `pytest tests/.../test_unified_bridge.py -v -q` | **45 passed** |
| `pytest tests/.../test_market_data_http_client.py tests/.../test_unified_bridge.py -q` | **71 passed** |
| `pytest tests/theme_sector_radar/ -q` | **915 passed，零回归** |
| `sector_stock_bridge.py --as-of 2026-07-02` | ✅ 成功，source summary 输出 |
| `unified_pipeline.py --as-of 2026-07-02 --mode quick` | ✅ 成功，报告含源追踪 |

### 新增测试覆盖
- `test_bridge_output_has_constituent_source_summary` — bridge 输出含 source summary
- `test_source_summary_fields_are_valid` — 所有 key 是已知标签
- `test_unified_json_has_data_source_field` — JSON 报告含 data_source
- `test_unified_json_has_bridge_source_summary` — bridge summary 透传
- `test_markdown_report_has_data_source_section` — Markdown 含"数据来源状态"
- `test_run_log_json_structure` — run_log 可包含来源追踪字段

## 6. run_log 扩展建议

当前 run_log 由 `pipeline.py` 中的 `run_pipeline()` 生成。如需记录 source summary，可在调用 `run_pipeline()` 后，在 CLI 层将 `result["data_source"]` 写入 run_log。已通过测试 `test_run_log_json_structure` 验证 JSON 结构兼容。
