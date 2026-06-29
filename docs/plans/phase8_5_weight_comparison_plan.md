# Phase 8.5 权重实验对比报告计划

日期：2026-06-29  
目标：用同一份数据对三套权重做可复现对比

## 1. 同源数据输入策略

### 1.1 实验流程
1. 先生成一次 raw_snapshot
2. 三套权重都从同一个 raw_snapshot 读取
3. 不允许每套权重单独重新拉 AkShare

### 1.2 数据完整性
- 报告必须记录 input_snapshot_path
- 报告必须记录 input_snapshot_hash
- 如果 input_snapshot 不一致，实验失败

## 2. 三套权重运行方式

### 2.1 权重配置
- baseline: weights_baseline.json
- capital_focused: weights_capital_focused.json
- trend_focused: weights_trend_focused.json

### 2.2 运行命令
```bash
python -m theme_sector_radar.experiments.weight_comparison \
  --as-of 2026-06-28 \
  --offline-fixture \
  --fixture-profile full \
  --output reports/experiments/weights/2026-06-28-fixture
```

## 3. 对比指标

### 3.1 comparison.json 字段
- as_of_date
- input_snapshot_path
- input_snapshot_hash
- weight_configs[]
- results (baseline / capital_focused / trend_focused)
- diff (industry_top_changes / concept_top_changes / focus_level_changes)
- recommendation

### 3.2 comparison.md 章节
1. 实验输入
2. 权重方案
3. 行业 Top N 对比
4. 概念 Top N 对比
5. 新晋/掉出差异
6. 风险等级差异
7. 共振板块差异
8. 初步结论
9. 声明

## 4. Top N 差异分析

### 4.1 对比指标
- Top N 重合率
- 排名平均变化
- 新增进入 Top N 的板块
- 掉出 Top N 的板块

## 5. 结论规则

### 5.1 默认结论
- 单日 fixture 实验默认结论: need_more_data

### 5.2 切换建议
- 只有多日真实缓存对比稳定优于 baseline，才建议切换
- 如果某权重明显推高高风险板块，提示风险
