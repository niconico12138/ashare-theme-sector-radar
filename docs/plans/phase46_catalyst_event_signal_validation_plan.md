# Phase 46: CatalystEventAgent Signal Validation

## 本阶段目标

验证 CatalystEventAgent 的事件信号是否有解释力。

## 坚持原则

- 只做信号验证
- CatalystEventAgent 仍然 report-only
- 不修改投票和决策
- 需要区分 fixture 数据和真实网络数据
- 如果只有 fixture 数据，结论必须标记为 limited_fixture_validation

## 验证内容

1. catalyst_label 表现
2. event_count bucket 表现
3. freshness / confidence 分层
4. catalyst x short_term_heat 叠加
5. catalyst x persistence_strength 叠加
6. catalyst x market_regime 分层

## 输出

- catalyst_event_backtest.py 模块
- catalyst_event_backtest_report.py 模块
- CLI --backtest-catalyst-events
