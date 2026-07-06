# 板块综合评分

**分析日期**: 2026-06-19
**更新时间**: 2026-07-01T22:35:02.988577

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不构成个股推荐、买卖建议或自动交易指令。

## 数据来源

- **板块类型**: industry
- **历史数据范围**: 2026-05-20 ~ 2026-06-19
- **基准模式**: sector_median (行业样本中位数)
- **历史数据来源**: sector_history_cache (完整板块指数历史)

**市场基准**: 沪深300 (hs300)
  - 使用真实市场基准计算相对强度

## 双评分说明

本报告包含两个并列评分：

1. **趋势持续分 (trend_continuation_score)**: 判断板块是否已经形成持续趋势
   - 更看重 5/10 日动量、连续性、相对强弱、回撤控制、波动稳定
   - 适合判断趋势是否持续

2. **短线爆发分 (short_term_burst_score)**: 判断板块是否正在短线爆发
   - 更看重当日雷达、1日涨幅、资金流、热度变化
   - 适合捕捉短线机会

**Profile 解读**:
- **trend_and_burst_aligned**: 趋势和短线都强，双重确认
- **trend_only**: 趋势强但短线不热，适合中长期持有
- **burst_without_trend_confirmation**: 短线强但趋势未确认，需谨慎
- **weak_or_cooling**: 趋势和短线都弱，建议回避

## 趋势权重方案

**当前使用的权重方案**: trend_confirmation (趋势确认型)

| 组件 | 权重 | 说明 |
|------|------|------|
| radar_score_component | 15 分 | 日报雷达分 |
| momentum_component | 25 分 | 动量 |
| relative_strength_component | 20 分 | 相对强度 |
| persistence_component | 20 分 | 持续性 |
| drawdown_component | 8 分 | 回撤 |
| volatility_component | 4 分 | 波动率 |
| data_quality_component | 8 分 | 数据质量 |
| risk_penalty | 0-20 分 | 风险扣分 |

**趋势确认型权重特点**: 更重视动量、相对强度和持续性，降低雷达分和数据质量权重，适合判断趋势是否真正形成。

## 趋势窗口

**趋势窗口**: 5 个交易日窗口

趋势持续评分使用最近 5 个有效交易日计算动量、持续性、回撤等指标。

**注意**: 如果历史数据不足窗口大小，趋势分可靠性会下降。

## 短线爆发评分权重

| 组件 | 权重 | 说明 |
|------|------|------|
| radar_today_component | 30 分 | 当日雷达分 |
| one_day_change_component | 20 分 | 单日涨幅 |
| three_day_momentum_component | 15 分 | 3日动量 |
| volume_or_heat_component | 10 分 | 成交额或热度 |
| rank_jump_component | 10 分 | 排名跳升 |
| data_quality_component | 10 分 | 数据质量 |
| burst_risk_penalty | 0-20 分 | 风险扣分 |

## 等级规则

### 趋势持续等级

| 等级 | 分数范围 | 说明 |
|------|----------|------|
| strong_watch | >= 80 | 趋势强劲，建议重点关注 |
| watch | >= 65 | 趋势良好，建议观察 |
| neutral | >= 50 | 表现中性，可作为备选观察 |
| cooling | >= 35 | 板块降温，谨慎观察 |
| avoid | < 35 | 板块弱势，建议回避 |

### 短线爆发等级

| 等级 | 分数范围 | 说明 |
|------|----------|------|
| burst_hot | >= 80 | 短线爆发强劲 |
| burst_watch | >= 65 | 短线表现活跃 |
| burst_neutral | >= 50 | 短线表现中性 |
| burst_fading | >= 35 | 短线动能减弱 |
| burst_avoid | < 35 | 短线表现疲弱 |

## 趋势持续 Top 10

| 排名 | 板块 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 消费电子 | 70.0 | 观察 | 58.8 | 短线中性 | neutral |
| 2 | 元件 | 67.2 | 观察 | 61.8 | 短线中性 | neutral |
| 3 | 非金属材料 | 65.2 | 观察 | 69.8 | 短线活跃 | trend_and_burst_aligned |
| 4 | 其他电子 | 62.2 | 中性 | 58.8 | 短线中性 | neutral |
| 5 | 半导体 | 62.2 | 中性 | 58.8 | 短线中性 | neutral |
| 6 | 小金属 | 62.2 | 中性 | 55.8 | 短线中性 | neutral |
| 7 | 通信设备 | 62.0 | 中性 | 58.8 | 短线中性 | neutral |
| 8 | 通信服务 | 46.0 | 降温 | 52.8 | 短线中性 | neutral |
| 9 | 医疗服务 | 32.0 | 回避 | 52.8 | 短线中性 | neutral |
| 10 | 生物制品 | 32.0 | 回避 | 52.8 | 短线中性 | neutral |

## 短线爆发 Top 10

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 非金属材料 | 69.8 | 短线活跃 | 65.2 | 观察 | trend_and_burst_aligned |
| 2 | 元件 | 61.8 | 短线中性 | 67.2 | 观察 | neutral |
| 3 | 消费电子 | 58.8 | 短线中性 | 70.0 | 观察 | neutral |
| 4 | 其他电子 | 58.8 | 短线中性 | 62.2 | 中性 | neutral |
| 5 | 半导体 | 58.8 | 短线中性 | 62.2 | 中性 | neutral |
| 6 | 通信设备 | 58.8 | 短线中性 | 62.0 | 中性 | neutral |
| 7 | 小金属 | 55.8 | 短线中性 | 62.2 | 中性 | neutral |
| 8 | 通信服务 | 52.8 | 短线中性 | 46.0 | 降温 | neutral |
| 9 | 医疗服务 | 52.8 | 短线中性 | 32.0 | 回避 | neutral |
| 10 | 生物制品 | 52.8 | 短线中性 | 32.0 | 回避 | neutral |

## 分歧板块

当前无明显分歧板块。

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，不构成推荐
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 消费电子

**趋势持续评分**:
- 趋势分: 70.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 17.0
  - persistence_component: 20.0
  - drawdown_component: 4.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 4.0

**短线爆发评分**:
- 短线分: 58.8
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 16.8
  - one_day_change_component: 12.0
  - three_day_momentum_component: 12.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 8.0
  - burst_risk_penalty: 0.0

**解读**:
- Profile: neutral
- Summary: 表现中性，可作为备选观察
- Watch points:
  - 等待更多确认信号
  - 关注后续表现

### 2. 元件

**趋势持续评分**:
- 趋势分: 67.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 20.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 0.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 10.0

**短线爆发评分**:
- 短线分: 61.8
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 16.8
  - one_day_change_component: 12.0
  - three_day_momentum_component: 15.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 8.0
  - burst_risk_penalty: 0.0

**解读**:
- Profile: neutral
- Summary: 表现中性，可作为备选观察
- Watch points:
  - 等待更多确认信号
  - 关注后续表现

### 3. 非金属材料

**趋势持续评分**:
- 趋势分: 65.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 11.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 0.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 10.0

**短线爆发评分**:
- 短线分: 69.8
- 短线等级: 短线活跃
- 短线 breakdown:
  - radar_today_component: 22.8
  - one_day_change_component: 16.0
  - three_day_momentum_component: 15.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 8.0
  - burst_risk_penalty: 2.0

**解读**:
- Profile: trend_and_burst_aligned
- Summary: 趋势和短线都强，双重确认
- Watch points:
  - 趋势和短线双重确认，可重点关注
  - 观察是否能持续保持双强态势

### 4. 其他电子

**趋势持续评分**:
- 趋势分: 62.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 0.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 10.0

**短线爆发评分**:
- 短线分: 58.8
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 16.8
  - one_day_change_component: 12.0
  - three_day_momentum_component: 12.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 8.0
  - burst_risk_penalty: 0.0

**解读**:
- Profile: neutral
- Summary: 表现中性，可作为备选观察
- Watch points:
  - 等待更多确认信号
  - 关注后续表现

### 5. 半导体

**趋势持续评分**:
- 趋势分: 62.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 0.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 10.0

**短线爆发评分**:
- 短线分: 58.8
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 16.8
  - one_day_change_component: 12.0
  - three_day_momentum_component: 12.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 8.0
  - burst_risk_penalty: 0.0

**解读**:
- Profile: neutral
- Summary: 表现中性，可作为备选观察
- Watch points:
  - 等待更多确认信号
  - 关注后续表现

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不构成个股推荐、买卖建议或自动交易指令。
