# 权重实验对比报告

## 1. 实验输入

- **分析日期**: 2026-06-28
- **生成时间**: 2026-06-29T14:47:00.743178
- **输入快照**: `reports/experiments/weights/2026-06-28-fixture-v2\input_snapshot.json`
- **快照哈希**: `ea43bf8e73b5...`
- **快照来源**: fixture

## 2. 权重方案

### baseline
- 当前默认权重配置
- capital_flow: 0.25
- trend_strength: 0.25

### capital_focused
- 资金流权重提高的配置
- capital_flow: 0.35
- trend_strength: 0.2

### trend_focused
- 趋势强度权重提高的配置
- capital_flow: 0.2
- trend_strength: 0.35

## 3. 行业 Top N 对比

| 排名 | baseline | capital_focused | trend_focused |
|------|----------|-----------------|---------------|
| 1 | 人工智能 | 人工智能 | 人工智能 |
| 2 | 半导体 | 半导体 | 半导体 |
| 3 | 芯片 | 芯片 | 芯片 |
| 4 | 锂电池 | 锂电池 | 锂电池 |
| 5 | 新能源汽车 | 新能源汽车 | 新能源汽车 |

## 4. 概念 Top N 对比

| 排名 | baseline | capital_focused | trend_focused |
|------|----------|-----------------|---------------|
| 1 | CPO概念 | CPO概念 | CPO概念 |
| 2 | ChatGPT概念 | ChatGPT概念 | ChatGPT概念 |
| 3 | 人工智能概念 | 人工智能概念 | 人工智能概念 |
| 4 | 机器人概念 | 机器人概念 | 机器人概念 |
| 5 | 芯片概念 | 芯片概念 | 芯片概念 |

## 5. Top N 重合率

- **capital_focused vs baseline**: 行业 100%, 概念 100%

## 6. Focus Level 变化

- 无变化

## 7. 初步结论

- **推荐**: need_more_data
- 单日 fixture 实验数据量不足
- 建议使用多日真实缓存数据进行对比
- 当前默认权重保持不变

## 8. 声明

**本报告仅用于板块评分研究，不构成个股推荐或买卖建议。**
