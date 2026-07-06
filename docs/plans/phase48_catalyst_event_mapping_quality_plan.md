# Phase 48: Catalyst Event Mapping Quality Improvement

## 本阶段目标

提升 catalyst event 从个股新闻到行业/概念板块的映射质量。

## 坚持原则

- 不修改 CatalystEventAgent vote
- 不依赖网络
- 输出映射质量和 unmapped 诊断

## 实现内容

1. symbol 标准化（SH/SZ/后缀）
2. name 标准化（去后缀、简称匹配）
3. 多来源映射索引
4. 映射诊断
5. mapping quality report

## 输出

- 增强 mapper.py
- 新增 mapping_quality.py
- 覆盖率报告
