# Phase 6.5 日报工作流语义审计

日期：2026-06-29  
状态：发现问题，需要修复

## 1. 审计发现

### 1.1 问题确认：fixture / AkShare / 旧报告串台

**问题 1：replay-cache 覆盖了 daily 输出**
- daily 模式输出到 `reports/theme_sector_radar/2026-06-28/`
- replay-cache 也输出到同一目录，覆盖了 daily 的输出
- run_log 显示 `provider: "replay-cache"`，不是 `fixture`

**问题 2：报告使用了 AkShare 数据**
- `concept_top` 包含 "昨日首板"、"昨日涨停_含一字" 等 AkShare 概念
- 这些不是 rotation-day2 fixture 定义的内容
- `data_sources` 显示 `["akshare/eastmoney_concept"]`

**问题 3：run_log 缺少数据来源信息**
- 没有记录 `offline_fixture`、`fixture_profile`、`data_source_mode`
- 无法追踪数据来源

**问题 4：index_report 扫描了所有目录**
- index 扫描了 `2026-06-28` 目录，但该目录被 replay 覆盖
- 没有区分 daily 正式目录和 experiments 临时目录

### 1.2 根因分析

1. daily 模式和 replay-cache 模式输出到同一目录，导致覆盖
2. replay-cache 读取了旧的 AkShare 缓存数据
3. run_log 没有记录足够的数据来源信息
4. index_report 没有区分标准日报目录和实验目录

## 2. 修复方案

### 2.1 数据来源可追踪性
- JSON 报告添加 `run_mode`、`provider`、`offline_fixture`、`fixture_profile`、`data_source_mode` 字段
- run_log 添加相应字段

### 2.2 index_report 扫描规则
- 默认只扫描 `YYYY-MM-DD` 标准目录
- 不扫描 `YYYY-MM-DD-phase*`、`YYYY-MM-DD-rotation*` 等实验目录
- 添加 `--include-experiments` 参数

### 2.3 daily fixture_profile 传递
- 确保 `--fixture-profile rotation-day2` 正确传递到报告
- 验证 Top 概念来自 rotation-day2 fixture

### 2.4 replay-cache 语义
- 不访问网络
- 只读取明确的缓存/报告来源
- 每日输出 run_log
- 找不到数据时生成 failed run_log，不用其他日期伪装
