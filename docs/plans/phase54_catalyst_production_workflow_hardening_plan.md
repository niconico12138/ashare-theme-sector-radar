# Phase 54 Catalyst Production Workflow Hardening Plan

## 背景

Phase 52/53 已验证真实 Catalyst 事件可以通过 AkShare `stock_news_em` 下载，并可稳定写入 `data_cache/catalyst_events/YYYY-MM-DD/`。但多日真实采集暴露出几个生产链路问题：

- PowerShell 中未给 `--symbols` 加引号时，`000001`、`002594` 等前导零容易丢失。
- 历史采集汇总中的 `date_count` 曾被错误写成 0。
- 部分报告生成器仍保留容易被误读为操作结论的措辞。
- CatalystEventAgent 仍处于 report-only 阶段，本阶段不得改变投票、veto、评分或共识标签。

## 目标

1. 修复历史 Catalyst 采集汇总的 `date_count` 计算。
2. 在 CLI 帮助文本中明确提示 PowerShell 需要给 `--symbols` 参数加引号。
3. 清理生产代码生成器中的交易语义措辞，统一改为研究复盘、观察信号、操作依据边界。
4. 保持 CatalystEventAgent report-only，不接入决策。
5. 运行专项测试和全量测试验证。

## 非目标

- 不校准 CatalystEventAgent vote。
- 不修改 ConsensusDecisionAgent。
- 不修改评分公式。
- 不新增真实数据源。
- 不修改 `ai-hedge-fund` 项目。

## 验收标准

- `date_count` 对单日区间为 1，对 2026-06-25 至 2026-06-29 为 5。
- 生产代码范围不再生成交易动作类措辞或容易被误读为操作结论的语义词。
- CatalystEventAgent 的 `vote` 仍为 `neutral`，`veto` 仍为 `false`，`decision_impact` 仍为 `report_only`。
- 专项测试通过。
- 全量测试通过。
