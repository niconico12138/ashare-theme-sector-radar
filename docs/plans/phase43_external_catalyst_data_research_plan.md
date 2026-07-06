# Phase 43: External Catalyst Data Research

## 本阶段目标

研究并验证可用于板块/概念催化事件识别的外部数据源。

## 坚持原则

- 本阶段是数据源研究，不是 Agent 实现
- 外部数据必须先验证稳定性、字段质量、历史可回溯能力
- 网络测试要可选，默认离线测试不能依赖外网
- 不修改生产决策规则

## 候选数据源

1. AkShare 资讯/新闻接口
2. AkShare 公告接口
3. AkShare 概念/行业信息接口
4. 公开政策/宏观事件源

## 输出

- catalyst_data_source_research.py 模块
- CLI --research-catalyst-sources
- 数据源可用性评估报告
