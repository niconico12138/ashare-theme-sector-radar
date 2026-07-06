# Phase 47: Catalyst Event Historical Data Collection

## 本阶段目标

扩展 catalyst event downloader，支持按日期区间批量采集历史事件缓存，提高 catalyst cache 覆盖率。

## 坚持原则

- 网络采集可选，失败要可追踪
- 默认离线测试不依赖网络
- 事件仍然只用于研究和报告解释
- 不修改 CatalystEventAgent vote

## 实现内容

1. 支持 --start-date / --end-date 批量采集
2. 支持自动选 symbols
3. 每天生成 events.json 和 source_status.json
4. 生成历史采集覆盖率报告

## 输出

- historical_collector.py 模块
- 扩展 CLI 参数
- 覆盖率报告
