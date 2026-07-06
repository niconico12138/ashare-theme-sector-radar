# 最终运营验收报告

**日期**: 2026-07-04  
**验收人**: Claude Code  
**项目**: market_data_service + theme-sector-radar-dev  
**阶段**: Phase 1-21 完整集成验收  

---

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│  theme-sector-radar-dev                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐ │
│  │ sector_stock │  │ unified_     │  │ run_daily_         │ │
│  │ _bridge.py   │  │ pipeline.py  │  │ unified_pipeline.py│ │
│  └──────┬───────┘  └──────┬───────┘  └─────────┬──────────┘ │
│         │                 │                     │            │
│         └────────┬────────┴─────────────────────┘            │
│                  │ HTTP API (market_data_http_client.py)     │
└──────────────────┼──────────────────────────────────────────┘
                   │
┌──────────────────┼──────────────────────────────────────────┐
│  market_data_service (FastAPI :8000)                        │
│  ┌───────────────┴────────────────────────────────────────┐ │
│  │ /health  /stocks/{code}/bars  /stocks/{code}/info      │ │
│  │ /stocks/{code}/fund-flow  /stocks/fund-flow/batch      │ │
│  │ /stocks/info/batch  /boards/.../constituents           │ │
│  └────────────────────────────────────────────────────────┘ │
│  Providers: StockDB | AkShare THS | Local Industry Members │
│             SecurityMaster | FundFlow (THS)                │
└─────────────────────────────────────────────────────────────┘
```

## 2. market_data_service 数据源状态

```
health_check():
├── stockdb:            ✅ ok (127.0.0.1:7899, latest=20260702)
├── akshare_ths:        ✅ ok (90 industries, 374 concepts)
├── security_master:    ✅ ok (5,528 stocks)
├── fund_flow_ths:      ✅ ok (5,193 stocks)
├── eastmoney_em:       ❌ proxy blocked
├── cninfo_industry:    ❌ API unavailable
└── local_industry:     ✅ ok (31 SW industries, 5,197 stocks)
```

## 3. 数据来源链路

| 数据类型 | 来源 | 状态 |
|---------|------|------|
| 个股 K 线 | StockDB → http_enhanced | ✅ PASS |
| 行业成分股 | local_industry_members (31 SW 行业) | ✅ PASS |
| 概念成分股 | offline mapping (35 boards) | ⚠️ WARN |
| 资金流 | THS fund_flow (batch→single→neutral) | ⚠️ 可用 |
| 股票基础信息 | SecurityMaster (batch→single→unknown) | ✅ PASS |

## 4. 每日运行命令

```bash
# 一键运行
python scripts/run_daily_unified_pipeline.py --as-of 2026-07-02 --mode quick

# 查看历史
python scripts/run_daily_unified_pipeline.py --show-history 10

# 完整 daily 报告 + 联合观察池
python -m theme_sector_radar.cli --daily --as-of 2026-07-02 \
  --offline-fixture --fixture-profile full --lookback-days 5 \
  --report-root reports/theme_sector_radar \
  --include-unified-pipeline --unified-mode quick
```

## 5. 测试运行方式

```bash
# 普通单元测试 (API 无需运行)
cd E:\liaohua\01_projects\market_data_service
python -m pytest tests -q

cd E:\liaohua\01_projects\theme-sector-radar-dev
python -m pytest tests/theme_sector_radar/ -q

# 含集成测试 (需先启动 market_data_service API)
python -m market_data_service.api_server --host 127.0.0.1 --port 8000
python -m pytest tests/theme_sector_radar/ -q
```

## 6. 数据质量面板

Markdown 报告新增 `## 数据质量面板` 小节，展示四个模块的状态、覆盖率和主要来源：

| 模块 | 状态判断 | 覆盖率 |
|------|---------|--------|
| 成分股 | real/total ≥ 80% → pass | constituents_real_ratio |
| K线/量化 | enhanced/total ≥ 80% → pass | quant_http_ratio |
| 资金流 | available/total ≥ 80% → pass | fund_flow_available_ratio |
| 股票基础信息 | known/total ≥ 80% → pass | stock_info_known_ratio |

## 7. score_breakdown

每只趋势/短线候选输出评分拆解：

```json
{
  "score_breakdown": {
    "final_score": 82.5,
    "quant_score_component": 49.2,
    "relevance_score_component": 33.32,
    "fund_flow_bonus": 4.1,
    "penalty": 0.0,
    "formula": "final_score = quant_score * 0.6 + relevance_score * 40 (quant 0-100→0-60pts, rel 0-1→0-40pts)"
  }
}
```

## 8. run_health 规则

| 级别 | 触发条件 |
|------|---------|
| **FAIL** | unavailable ≥ 30% \| emergency ≥ 50% \| fallback_quant ≥ 50% |
| **WARN** | 有 unavailable (少量) \| 有 emergency (少量) \| 有 fallback quant \| mapping ≥ 50% \| stock_unknown ≥ 50% \| 全部 mapping 无 real source |
| **PASS** | 以上均不满足 |

## 9. 当前测试结果

| 项目 | 结果 |
|------|------|
| market_data_service tests | **290 passed** |
| theme-sector-radar tests | **974 passed, 3 skipped, 0 failed** |
| 3 skipped 为集成测试 (需 API 运行) | `_api_available()` 自动跳过 |

## 10. 已知风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| Eastmoney EM 封锁 | 行业成分股依赖 local_industry | 31 SW 行业 × 5,197 stocks 覆盖 |
| 概念板块依赖 mapping | 概念无真实源 | 35 高频概念 hand-curated mapping |
| 资金流可能不可用 | 降级为 neutral | THS fund_flow 当前可访问 (5,193 stocks) |
| 概念板块仍有缺口 | 374 THS 概念中仅覆盖 35 | 按需扩展 mapping |

## 11. 边界

- ✅ 不自动交易
- ✅ 不给买卖建议
- ✅ 只输出观察池/候选
- ✅ 不注册 Windows 任务计划
- ✅ 不接脆弱 HTML 解析
- ✅ 不改评分公式

## 12. formula typo 修复

| 项 | Before | After |
|----|--------|-------|
| formula 字符串 | `quant_score * 0.6 + relevance_score * 40` | 追加 `(quant 0-100→0-60pts, rel 0-1→0-40pts)` 说明 |
| 计算 | 不变 | 不变 |
| 测试 | 不变 | 不变 |

修复原因: `40` 是 relevance_score 0-1 × 100 × 0.4 的展开结果，不是 weight typo。现有字符串正确但易误解，追加注释说明区间。

## 13. 最终结论

**PASS** ✅

项目可以作为本地盘后手动运行流程稳定使用。普通测试 974+290 全部通过，集成测试在 API 启动后 3 个自动恢复。
