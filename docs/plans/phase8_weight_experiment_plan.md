# Phase 8 真实 AkShare 多日人工验收与评分权重实验计划

日期：2026-06-29  
目标：真实数据质量评估、权重实验和报告可读性改进

## 1. 真实数据质量评估

### 1.1 目标
- 评估 AkShare 数据在不同日期的稳定性
- 识别数据缺失和异常情况
- 验证 fallback cache 机制

### 1.2 评估维度
- 数据源完整性
- 字段覆盖率
- 数据新鲜度
- 异常值检测

## 2. 评分权重实验

### 2.1 当前权重配置
```json
{
  "industry_weights": {
    "trend_strength": 0.25,
    "capital_flow": 0.25,
    "sector_breadth": 0.20,
    "continuity": 0.15,
    "market_fit": 0.10,
    "data_quality": 0.05
  },
  "concept_weights": {
    "heat_burst": 0.25,
    "capital_confirm": 0.20,
    "constituent_synergy": 0.20,
    "phase_judgment": 0.20,
    "catalyst": 0.10,
    "data_quality": 0.05
  }
}
```

### 2.2 实验方案
- 保存当前权重为 baseline
- 创建 alternative 配置进行对比
- 输出权重对比报告

## 3. 报告可读性改进

### 3.1 改进方向
- Markdown 报告结构优化
- 关键信息突出显示
- 风险提示更清晰

### 3.2 具体改进
- 添加板块评分 breakdown 摘要
- 优化表格格式
- 改进轮动章节展示

## 4. 测试与验收

### 4.1 测试命令
```bash
# 默认测试
python -m pytest tests/theme_sector_radar/ -v

# 评分权重实验
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --offline-fixture --fixture-profile full --lookback-days 5 --report-root reports/theme_sector_radar
```

### 4.2 验收标准
- 所有测试通过
- 报告可读性提升
- 权重实验可复现
