# Phase 52: Real Catalyst Network Validation Plan

**日期**: 2026-07-01
**阶段**: Phase 52
**目标**: 验证真实 Catalyst 外部事件采集链路
**状态**: ✅ 已完成

---

## 1. 背景

Phase 43-49 建立了完整的 Catalyst 事件体系，但所有 145+ 个事件均为 fixture 数据。Phase 52 使用真实 AkShare 网络接口验证 `--download-catalyst-events --network` 采集链路。

### 1.1 关键约束

- CatalystEventAgent 保持 report-only，不参与 vote/veto/scoring
- 不修改 ConsensusDecisionAgent/scoring/vote/veto 生产规则
- 不修改 ai-hedge-fund 项目
- 不使用交易建议词

---

## 2. 修改内容

### 2.1 CLI 参数修复 (cli.py)

**问题**: `--network` 参数未在 argparse 中定义。
**修复**: 在 `--download-catalyst-events` 后添加 `--network` 参数定义。

### 2.2 辅助脚本

| 脚本 | 用途 |
|------|------|
| `scripts/network_smoke_test.py` | 网络连通性验证，支持 `--symbols` / `--output` |
| `scripts/check_cache.py` | 缓存输出检查，支持日期参数 (默认 2026-06-29) |

---

## 3. 验证结果

| 验证项 | 结果 |
|--------|------|
| CLI `--network` 参数 | ✅ 出现在 --help |
| 网络 smoke test | ✅ network_available, AkShare 1.18.64 |
| 真实网络下载 | ✅ 22 events, 0 failed, source=akshare_stock_news_em |
| mapping_rate | ✅ 1.0 (22/22) |
| source_status | ✅ 均为 ok |
| Backtest 覆盖率 | ✅ cache_coverage=1.0, real=10, fixture=80 |
| Catalyst report-only | ✅ 保持 |
| 决策逻辑未修改 | ✅ 无变更 |
| ai-hedge-fund 未修改 | ✅ 无变更 |

---

## 4. Backtest 注意事项

⚠️ 正确的 backtest 命令必须使用 `--report-root reports`，不是 `reports\theme_sector_radar`:
```
python -m theme_sector_radar.cli --backtest-catalyst-events --start-date 2026-06-21 --end-date 2026-06-29 --report-root reports
```

---

*本计划由 Phase 52 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
