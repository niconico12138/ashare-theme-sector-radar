# Phase 32: Replay Daily Market Breadth Enhancement Plan

## 本阶段目标

增强 replay daily 数据生成，使 `theme_sector_radar.json` 包含更真实的市场温度、行业广度和涨跌分布。

## 坚持原则

- 只增强 replay daily 数据生成
- 不修改 Agent 生产标签规则
- 所有计算必须 no-lookahead，只使用 signal_date 当日及之前数据
- 目标是让 Phase 31 的 market_regime 分层更可信

## 当前问题

- `market_temperature` 硬编码为 `score=50, label=neutral`
- `industry_top` 的 `price_change_pct` 全部为 0.0
- `advance_count=0, decline_count=0`

## 增强方案

在 `_generate_daily_report` 中新增 `_compute_market_breadth` 方法，扫描所有 sector_history 文件，计算：
- up/down/flat 计数和比例
- 平均/中位数涨跌幅
- strong/weak 计数和比例
- breadth_label 和 temperature score/label

## 输出

增强后重新生成的 `theme_sector_radar.json` 将包含 `market_breadth` 字段。
