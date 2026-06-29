# Phase 4.5 评分语义审计报告

日期：2026-06-29  
状态：发现问题，需要修复

## 1. 审计发现

### 1.1 当前实现（有问题）

```python
# risk_score.py
overheat_penalty = -18.5  # 负数
divergence_penalty = -12.0  # 负数
total_penalty = -30.5  # 负数

# sector_ranking_agent.py
final_score = positive_score + risk_penalty  # 加法
# 例如: 89.0 + (-3.0) = 86.0
```

### 1.2 设计文档要求

```
raw_score = positive_score - risk_penalty
# 例如: 89.0 - 3.0 = 86.0
```

### 1.3 问题总结

| 项目 | 当前实现 | 设计要求 | 状态 |
|------|---------|---------|------|
| risk_penalty 符号 | 负数 (-3.0) | 正数 (3.0) | ❌ 需修复 |
| final_score 公式 | positive_score + risk_penalty | positive_score - risk_penalty | ❌ 需修复 |
| 风险分项符号 | 负数 | 正数 | ❌ 需修复 |

## 2. 影响范围

### 2.1 需要修改的文件
1. `scoring/risk_score.py` - 风险扣分改为正数
2. `agents/ranking_report/sector_ranking_agent.py` - final_score 公式改为减法
3. `reports/json_report.py` - 确保展示正数
4. `reports/markdown_report.py` - 确保展示"扣 X 分"

### 2.2 需要更新的测试
1. `test_risk_score.py` - 更新断言
2. `test_scoring_semantics.py` - 新增语义测试

## 3. 修复方案

### 3.1 risk_score.py
```python
# 改为正数
overheat_penalty = abs(overheat_penalty)
divergence_penalty = abs(divergence_penalty)
quality_penalty = abs(quality_penalty)
total_penalty = abs(total_penalty)
```

### 3.2 sector_ranking_agent.py
```python
# 改为减法
final_score = positive_score - risk_penalty
```

### 3.3 报告展示
```json
// JSON
"risk_penalty": 3.0,  // 正数

// Markdown
"风险扣分: 3.0 分"  // 不显示负号
```
