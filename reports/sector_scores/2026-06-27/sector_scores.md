# 板块综合评分

**分析日期**: 2026-06-27
**更新时间**: 2026-07-02T14:49:25.170554

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。

## 数据来源

- **板块类型**: industry
- **历史数据范围**: None ~ None
- **基准模式**: sector_median (行业样本中位数)
- **历史数据来源**: sector_history_cache (完整板块指数历史)

**市场基准**: 无 (使用 sector_median)

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
- **trend_only**: 趋势强但短线不热，中长期趋势观察价值较高
- **burst_without_trend_confirmation**: 短线强但趋势未确认，需谨慎
- **weak_or_cooling**: 趋势和短线都弱，正向观察强度有限

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

**趋势窗口**: 10 个交易日窗口

趋势持续评分使用最近 10 个有效交易日计算动量、持续性、回撤等指标。

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
| 重点观察 | strong_watch | >= 80 | 趋势强劲，可列入重点观察样本 |
| 观察 | watch | >= 65 | 趋势良好，可继续观察 |
| 中性 | neutral | >= 50 | 表现中性，可作为备选观察 |
| 降温 | cooling | >= 35 | 板块降温，谨慎观察 |
| 偏弱 | avoid | < 35 | 板块弱势，正向观察强度有限 |

### 短线爆发等级

| 等级 | 分数范围 | 说明 |
|------|----------|------|
| 短线强势 | burst_hot | >= 80 | 短线爆发强劲 |
| 短线活跃 | burst_watch | >= 65 | 短线表现活跃 |
| 短线中性 | burst_neutral | >= 50 | 短线表现中性 |
| 短线降温 | burst_fading | >= 35 | 短线动能减弱 |
| 短线偏弱 | burst_avoid | < 35 | 短线表现偏弱 |

## 趋势持续 Top 10

| 排名 | 板块 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 电子化学品 | 64.2 | 中性 | 49.8 | 短线降温 | neutral |
| 2 | 光学光电子 | 47.2 | 降温 | 35.8 | 短线降温 | weak_or_cooling |
| 3 | 元件 | 45.6 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 4 | IT服务 | 33.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 5 | 光伏设备 | 31.2 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 6 | 互联网电商 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 7 | 保险 | 25.6 | 偏弱 | 36.3 | 短线降温 | weak_or_cooling |
| 8 | 教育 | 24.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 9 | 公路铁路运输 | 22.1 | 偏弱 | 32.3 | 短线偏弱 | weak_or_cooling |
| 10 | 中药 | 21.4 | 偏弱 | 33.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 10

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 电子化学品 | 49.8 | 短线降温 | 64.2 | 中性 | neutral |
| 2 | 教育 | 39.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 3 | 保险 | 36.3 | 短线降温 | 25.6 | 偏弱 | weak_or_cooling |
| 4 | 光学光电子 | 35.8 | 短线降温 | 47.2 | 降温 | weak_or_cooling |
| 5 | 中药 | 33.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 6 | 公路铁路运输 | 32.3 | 短线偏弱 | 22.1 | 偏弱 | weak_or_cooling |
| 7 | 光伏设备 | 28.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 8 | IT服务 | 25.3 | 短线偏弱 | 33.2 | 偏弱 | weak_or_cooling |
| 9 | 互联网电商 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 10 | 元件 | 21.3 | 短线偏弱 | 45.6 | 降温 | weak_or_cooling |

## 分歧板块

当前无明显分歧板块。

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 电子化学品

**趋势持续评分**:
- 趋势分: 64.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 20.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 0.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 10.0

**短线爆发评分**:
- 短线分: 49.8
- 短线等级: 短线降温
- 短线 breakdown:
  - radar_today_component: 10.8
  - one_day_change_component: 12.0
  - three_day_momentum_component: 9.0
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

### 2. 光学光电子

**趋势持续评分**:
- 趋势分: 47.2
- 趋势等级: 降温
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 10.0
  - drawdown_component: 0.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 12.0

**短线爆发评分**:
- 短线分: 35.8
- 短线等级: 短线降温
- 短线 breakdown:
  - radar_today_component: 10.8
  - one_day_change_component: 4.0
  - three_day_momentum_component: 3.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 8.0
  - burst_risk_penalty: 0.0

**解读**:
- Profile: weak_or_cooling
- Summary: 趋势和短线都弱，建议回避
- Watch points:
  - 板块整体表现疲弱
  - 等待明确的反转信号

### 3. 元件

**趋势持续评分**:
- 趋势分: 45.6
- 趋势等级: 降温
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 0.0
  - volatility_component: 1.6
  - data_quality_component: 6.4
  - risk_penalty: 14.0

**短线爆发评分**:
- 短线分: 21.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 3.3
  - one_day_change_component: 0.0
  - three_day_momentum_component: 0.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 8.0
  - burst_risk_penalty: 0.0

**解读**:
- Profile: weak_or_cooling
- Summary: 趋势和短线都弱，建议回避
- Watch points:
  - 板块整体表现疲弱
  - 等待明确的反转信号

### 4. IT服务

**趋势持续评分**:
- 趋势分: 33.2
- 趋势等级: 偏弱
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 10.0
  - relative_strength_component: 14.0
  - persistence_component: 10.0
  - drawdown_component: 0.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 12.0

**短线爆发评分**:
- 短线分: 25.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 3.3
  - one_day_change_component: 4.0
  - three_day_momentum_component: 0.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 8.0
  - burst_risk_penalty: 0.0

**解读**:
- Profile: weak_or_cooling
- Summary: 趋势和短线都弱，建议回避
- Watch points:
  - 板块整体表现疲弱
  - 等待明确的反转信号

### 5. 光伏设备

**趋势持续评分**:
- 趋势分: 31.2
- 趋势等级: 偏弱
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 10.0
  - relative_strength_component: 17.0
  - persistence_component: 5.0
  - drawdown_component: 0.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 12.0

**短线爆发评分**:
- 短线分: 28.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 3.3
  - one_day_change_component: 4.0
  - three_day_momentum_component: 3.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 8.0
  - burst_risk_penalty: 0.0

**解读**:
- Profile: weak_or_cooling
- Summary: 趋势和短线都弱，建议回避
- Watch points:
  - 板块整体表现疲弱
  - 等待明确的反转信号

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
