# Phase 49: Catalyst Coverage Rebuild and Signal Revalidation

## 本阶段目标

基于 Phase 48 增强后的映射能力，重新构建 catalyst cache 覆盖，并重新运行 CatalystEventAgent 信号验证。

## 坚持原则

- 不修改 CatalystEventAgent vote
- 明确区分 fixture 和 real 数据
- 如果 real 数据不足，必须保持 report-only
- 需要比较 Phase 46 与 Phase 49 的覆盖率变化

## 执行内容

1. 重新跑历史 catalyst collection（fixture）
2. 重新生成 research range
3. 重新运行 catalyst event backtest
4. 产出 Phase 46 vs Phase 49 对比报告
