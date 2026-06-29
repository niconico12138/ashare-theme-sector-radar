# Phase 9 真实数据积累与人工验收准备计划

日期：2026-06-29  
目标：为真实数据积累和人工验收做好准备

## 1. 目标

### 1.1 核心目标
- 建立真实数据积累流程
- 建立人工验收机制
- 为多日权重实验做准备

### 1.2 不做的事
- 不新增复杂功能
- 不切换默认权重
- 不接入 LangGraph
- 不做个股推荐
- 不自动交易

## 2. 文档交付物

### 2.1 计划文档
- docs/plans/phase9_real_data_validation_plan.md

### 2.2 操作手册
- docs/runbooks/real_data_validation.md

### 2.3 人工验收模板
- docs/templates/daily_manual_review_template.md

## 3. 真实数据积累流程

### 3.1 每日盘后运行
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_daily.ps1
```

### 3.2 确认成功
1. 检查 run_log.json 状态
2. 检查 data_cache/YYYY-MM-DD/raw_snapshot.json
3. 检查 reports/theme_sector_radar/YYYY-MM-DD/theme_sector_radar.md

### 3.3 人工观察
- 使用 daily_manual_review_template.md
- 记录每日观察结论

## 4. 多日权重实验准备

### 4.1 前提条件
- 连续 3-5 个真实交易日成功运行
- data_cache 中有足够数据

### 4.2 运行命令
```bash
python -m theme_sector_radar.experiments.weight_comparison \
  --start-date YYYY-MM-DD \
  --end-date YYYY-MM-DD \
  --use-cache \
  --output reports/experiments/weights/YYYY-MM-DD_to_YYYY-MM-DD-cache
```

## 5. 验收命令

```bash
# 运行测试
python -m pytest tests/theme_sector_radar/ -v
```
