# Release Snapshot 2026-06-29

> **冻结日期**: 2026-06-29
> **版本状态**: 可运行版本，真实日报 status=ok
> **数据源**: AkShare + THS fallback

---

## 1. 当前版本状态

| 指标 | 值 |
|------|-----|
| **CLI 状态** | ✅ ok |
| **日报模式** | 可运行 |
| **测试结果** | 289 passed |
| **数据来源** | AkShare (THS fallback) |

---

## 2. 当前有效数据源

### 东方财富 (EM) — 不可用

- **失败原因**: 服务器出口 IP 被拒绝
- **错误类型**: `RemoteDisconnected` / `ProxyError`
- **具体表现**: TLS 握手成功，但 HTTP 请求被服务器关闭连接
- **受影响接口**: `push2.eastmoney.com` (行业/概念/成分股/资金流)

### 同花顺 (THS) — 可用

- **行业板块**: `stock_board_industry_summary_ths` ✅ 有涨跌幅
- **概念板块**: `stock_board_concept_name_ths` ⚠️ 无涨跌幅
- **成分股**: 无 THS 接口，使用 EM 接口（当前不可用）

---

## 3. THS Fallback 能力边界

| 数据类型 | 涨跌幅 | 成交额 | 资金流 | 成分股 |
|----------|--------|--------|--------|--------|
| **行业板块** | ✅ 可用 | ✅ 可用 | ✅ 可用 | ❌ 不可用 |
| **概念板块** | ❌ 不可用 | ❌ 不可用 | ❌ 不可用 | ❌ 不可用 |

### 关键行为

1. **行业板块**: 可获取完整数据，评分可信
2. **概念板块**: 缺少涨跌幅，`concept_price_change_available=false`
3. **概念评分**: 基于成交额、资金流和成分股联动等可用指标，热度爆发和催化剂维度评分偏保守
4. **Focus 等级**: 涨跌幅不可用时，即使正向评分高也不能输出 FOCUS，自动降级

---

## 4. 当前报告路径

```
reports/theme_sector_radar/2026-06-29/
├── run_log.json           # 运行日志
├── theme_sector_radar.json # JSON 报告
├── theme_sector_radar.md   # Markdown 报告
└── raw_snapshot.json       # 原始数据快照
```

### 缓存路径

```
data_cache/2026-06-29/
└── raw_snapshot.json       # 缓存数据
```

---

## 5. 核心字段说明

### Provider Status 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `effective_provider` | string | 实际数据提供者 (`akshare` / `ths` / `mixed`) |
| `industry_source` | string | 行业数据来源 (`akshare/eastmoney_industry` / `akshare/ths_industry`) |
| `concept_source` | string | 概念数据来源 (`akshare/eastmoney_concept` / `akshare/ths_concept`) |
| `fallback_used` | bool | 是否使用了 fallback |
| `fallback_provider` | string | fallback 提供者 (`ths`) |
| `fallback_reason` | string | fallback 原因摘要 |
| `concept_price_change_available` | bool | 概念涨跌幅是否可用 |
| `em_industry_error` | string | EM 行业接口错误信息 |
| `em_concept_error` | string | EM 概念接口错误信息 |

### Score Breakdown 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `price_change_available` | bool | 涨跌幅是否可用 |
| `data_quality_warning` | string | 数据质量警告（涨跌幅不可用时） |
| `heat_burst` | float | 热度爆发得分 (0-25) |
| `fund_confirmation` | float | 资金确认得分 (0-20) |
| `constituent_linkage` | float | 成分股联动得分 (0-20) |
| `phase_score` | float | 阶段判断得分 (0-20) |
| `catalyst` | float | 催化剂得分 (0-10) |
| `data_quality` | float | 数据质量得分 (0-5) |

---

## 6. 已知限制

1. **EM 接口在当前服务器不可用**: `push2.eastmoney.com` 对数据中心/云服务器 IP 进行访问控制
2. **THS 概念评分解释力弱于行业**: 缺少涨跌幅数据，热度爆发和催化剂维度评分偏保守
3. **后续真实多日权重实验仍需要更多缓存数据**: 当前仅有单日缓存，多日实验需要积累
4. **成分股数据不可用**: THS 无成分股接口，EM 接口不可用

---

## 7. 常用运行命令

### PowerShell 脚本

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_daily.ps1
```

### CLI 命令

```bash
python -m theme_sector_radar.cli \
  --daily \
  --as-of YYYY-MM-DD \
  --provider akshare \
  --refresh \
  --fallback-cache-days 7 \
  --lookback-days 5 \
  --report-root reports/theme_sector_radar
```

### 测试命令

```bash
python -m pytest tests/theme_sector_radar/ -v
```

---

## 8. 下一阶段建议

### 短期 (1-2 周)

1. **多日真实日报观察**: 运行 5-10 天日报，观察 THS 数据稳定性
2. **THS 概念字段增强**: 调研是否可通过 `concept_info_ths` 逐个获取概念涨跌幅（需评估性能）
3. **成分股数据补充**: 调研 THS 成分股接口或替代方案

### 中期 (1 个月)

4. **权重实验基于多日缓存再判断**: 积累足够缓存数据后进行权重对比实验
5. **EM 接口恢复监控**: 定期检测 EM 接口是否恢复
6. **数据质量评估**: 基于多日数据评估 THS vs EM 数据质量差异

### 长期

7. **多数据源融合**: 支持同时使用多个数据源，取并集或加权
8. **实时数据支持**: 支持盘中实时数据更新
9. **回测框架**: 基于历史数据进行策略回测

---

## 9. 版本历史

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-06-29 | v0.1.0 | 初始版本，支持 THS fallback，概念涨跌幅不可用标记 |

---

*本文档由 Theme Sector Radar 自动生成，用于冻结当前可运行版本状态。*
