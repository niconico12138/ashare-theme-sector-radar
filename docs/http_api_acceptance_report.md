# market_data_service HTTP API 联调验收报告

**日期**: 2026-07-04  
**验收人**: Claude Code  
**项目**: theme-sector-radar-dev ←→ market_data_service HTTP API

---

## 1. 环境状态

| 组件 | 状态 | 详情 |
|------|------|------|
| StockDB | ✅ ok | host=127.0.0.1:7899, latest_daily_date=20260702 |
| AkShare THS | ✅ ok | 90 industries, 374 concepts |
| Eastmoney EM | ❌ unavailable | push2 DNS/network blocked by Clash proxy |
| market_data_service API | ✅ running | http://127.0.0.1:8000 |
| market_data_service /health | ✅ ok | 返回 stockdb+akshare_ths+eastmoney_em 三字段 |

---

## 2. API 端点测试结果

| 端点 | HTTP 状态 | 数据质量 | 备注 |
|------|-----------|----------|------|
| `GET /health` | 200 ✅ | 完整 | 三数据源状态正确返回 |
| `GET /stocks/600633/bars?start=20260701&end=20260702` | 200 ✅ | 完整 | 返回 date/open/high/low/close/volume/amount/pct_chg |
| `GET /boards/industry/半导体/constituents` | 503 ⚠️ | 空 | Eastmoney EM 被代理封锁，返回 BoardConstituentsUnavailableError |
| `GET /boards/industry-summary` | 200 ✅ | 完整 | 返回 90 个行业，含 pct_chg/amount/net_inflow/up_count/down_count |

---

## 3. sector_stock_bridge.py 联调结果

**命令**: `python sector_stock_bridge.py --as-of 2026-07-02`

**结果**: ✅ 成功完成

**数据来源链路**:
```
HTTP API constituents (/boards/{type}/{name}/constituents)
  → ❌ 503 (Eastmoney EM blocked)
  → AkShare stock_board_industry_cons_em
    → ❌ (proxy blocks push2.eastmoney.com)
    → SECTOR_STOCK_MAPPING (内置映射)
      → ✅ 9/10 板块获取到成分股
```

**source 字段分布**:
| source | 板块数 | 示例 |
|--------|--------|------|
| `mapping` | 9 | 电子化学品(7只)、半导体(8只)、证券(15只)、... |
| `unknown` | 1 | 元件(0只) — 不在 SECTOR_STOCK_MAPPING 中 |

**API 状态**:
- `akshare_constituents`: degraded
- `tencent_quotes`: ok (获取 70 只股票实时行情)
- `fund_flow`: degraded (使用中性值)

**输出**:
- 趋势板块: 22 只高关联度个股
- 短线板块: 23 只高关联度个股
- JSON 报告: `reports/bridge/2026-07-02/bridge_result.json`

**中断检查**: 否 — 流程未中断，degraded 板块正常标记

---

## 4. unified_pipeline.py 联调结果

**命令**: `python unified_pipeline.py --as-of 2026-07-02 --mode quick`

**结果**: ✅ 成功完成

**量化评分数据来源**:
```
HTTP API stock bars (/stocks/{code}/bars)
  → ✅ 成功获取 22 只股票的日 K 线数据
  → quant_source = "http_enhanced"
  → 使用增强 7 因子评分（5日涨幅 + 10日涨幅 + 20日最大回撤 + 5日均成交额 + 涨幅 + 市值 + PE）
```

**scoring_method** (来自 JSON 报告):
```json
{
  "quant_source": "http_enhanced",
  "weights": {"quant": 0.6, "relevance": 0.4},
  "min_relevance": 0.6
}
```

**最终输出**:
- 趋势板块 Top10: 22 只个股
- 短线板块 Top10: 19 只个股
- JSON 报告: `reports/unified/2026-07-02/unified_report.json`
- Markdown 报告: `reports/unified/2026-07-02/unified_report.md`（标记为 "HTTP 增强多因子"）

**最终综合分公式保持**: `final_score = quant_score × 0.6 + relevance_score × 0.4`

---

## 5. 实际使用的数据来源汇总

| 数据 | 来源 | 状态 |
|------|------|------|
| 板块评分 | reports/sector_scores/ 缓存 | ✅ |
| 板块成分股 | SECTOR_STOCK_MAPPING (内置映射) | ⚠️ 降级（HTTP 503 → AkShare ❌ → mapping） |
| 个股行情 | 腾讯 API qt.gtimg.cn | ✅ |
| 板块资金流 | neutral (降级) | ⚠️ Eastmoney blocked |
| 个股资金流 | neutral (降级) | ⚠️ Eastmoney blocked |
| 个股 K 线 | **HTTP API** `/stocks/{code}/bars` | ✅ http_enhanced |
| 个股量化评分 | **HTTP 增强 7 因子** | ✅ http_enhanced |

---

## 6. Bug 修复记录

| Bug | 严重性 | 修复 |
|-----|--------|------|
| Windows GBK 控制台打印 emoji (✅⚠️❌📁) 导致 `UnicodeEncodeError` | P1 | 在 `sector_stock_bridge.py` 和 `unified_pipeline.py` 顶部添加 `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` |
| `test_market_data_http_client.py` 中 `_mock_response` 空列表被 `or {}` 吞掉 | P3 | 改为 `json_data if json_data is not None else {}` |
| `test_enhanced_score_min_bars` 变量名错误 (`d` 未定义) | P3 | 修正为 `i` |

---

## 7. 待改进 (TODO)

1. **SECTOR_STOCK_MAPPING 覆盖不足**: "元件" 板块不在映射中，导致 0 只成分股。建议扩展映射到 50+ 板块。
2. **market_data_service 成分股 stale cache**: 当 EM 不可用时返回 503 而非 stale 数据。可后续给 market_data_service 加 stale cache 支持。
3. **资金流数据**: 所有板块和个股资金流都降级为 neutral。需要替代数据源。
4. **HTTP 重试过多**: urllib3 retry 对每个 503 做 2 次重试，10 个板块 = 20 次无意义重试。可优化重试策略或添加短路径快速失败。

---

## 8. 结论

**HTTP API 集成验收通过** ✅

- StockDB ✅ (本机可用)
- market_data_service /health ✅
- /stocks/{code}/bars ✅ (HTTP 增强量化评分成功启用)
- /boards/{type}/{name}/constituents ⚠️ (503 降级到 mapping, 流程不中断)
- sector_stock_bridge.py ✅ (成功完成, 降级路径正常工作)
- unified_pipeline.py ✅ (成功完成, quant_source=http_enhanced)
- source 标记清晰: mapping 用于成分股, http_enhanced 用于 K 线量化评分

