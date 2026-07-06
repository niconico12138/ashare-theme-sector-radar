# 板块综合评分

**分析日期**: 2026-06-30
**更新时间**: 2026-06-30T21:31:08.206455

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不构成个股推荐、买卖建议或自动交易指令。

## 数据来源

- **板块类型**: industry
- **历史数据范围**: 2026-05-20 ~ 2026-06-30
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

**趋势窗口**: 20 个交易日窗口

趋势持续评分使用最近 20 个有效交易日计算动量、持续性、回撤等指标。

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

## 趋势持续 Top 20

| 排名 | 板块 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 光学光电子 | 44.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 2 | 其他电子 | 41.5 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 3 | 元件 | 38.6 | 降温 | 27.3 | 短线偏弱 | weak_or_cooling |
| 4 | 军工电子 | 38.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 5 | 化学制品 | 36.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 6 | 保险 | 33.5 | 回避 | 42.3 | 短线回落 | weak_or_cooling |
| 7 | 化学原料 | 23.2 | 回避 | 31.3 | 短线偏弱 | weak_or_cooling |
| 8 | 化学制药 | 20.4 | 回避 | 45.3 | 短线回落 | weak_or_cooling |
| 9 | IT服务 | 19.2 | 回避 | 31.3 | 短线偏弱 | weak_or_cooling |
| 10 | 其他社会服务 | 19.2 | 回避 | 31.3 | 短线偏弱 | weak_or_cooling |
| 11 | 包装印刷 | 19.2 | 回避 | 31.3 | 短线偏弱 | weak_or_cooling |
| 12 | 其他电源设备 | 16.4 | 回避 | 31.3 | 短线偏弱 | weak_or_cooling |
| 13 | 光伏设备 | 14.2 | 回避 | 34.3 | 短线偏弱 | weak_or_cooling |
| 14 | 公路铁路运输 | 14.2 | 回避 | 38.3 | 短线回落 | weak_or_cooling |
| 15 | 养殖业 | 14.2 | 回避 | 42.3 | 短线回落 | weak_or_cooling |
| 16 | 农产品加工 | 14.2 | 回避 | 42.3 | 短线回落 | weak_or_cooling |
| 17 | 农化制品 | 14.2 | 回避 | 31.3 | 短线偏弱 | weak_or_cooling |
| 18 | 中药 | 13.4 | 回避 | 39.3 | 短线回落 | weak_or_cooling |
| 19 | 互联网电商 | 12.2 | 回避 | 31.3 | 短线偏弱 | weak_or_cooling |
| 20 | 军工装备 | 12.2 | 回避 | 31.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 20

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 化学制药 | 45.3 | 短线回落 | 20.4 | 回避 | weak_or_cooling |
| 2 | 保险 | 42.3 | 短线回落 | 33.5 | 回避 | weak_or_cooling |
| 3 | 养殖业 | 42.3 | 短线回落 | 14.2 | 回避 | weak_or_cooling |
| 4 | 农产品加工 | 42.3 | 短线回落 | 14.2 | 回避 | weak_or_cooling |
| 5 | 中药 | 39.3 | 短线回落 | 13.4 | 回避 | weak_or_cooling |
| 6 | 公路铁路运输 | 38.3 | 短线回落 | 14.2 | 回避 | weak_or_cooling |
| 7 | 光学光电子 | 34.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 8 | 军工电子 | 34.3 | 短线偏弱 | 38.2 | 降温 | weak_or_cooling |
| 9 | 光伏设备 | 34.3 | 短线偏弱 | 14.2 | 回避 | weak_or_cooling |
| 10 | 其他电子 | 31.3 | 短线偏弱 | 41.5 | 降温 | weak_or_cooling |
| 11 | 化学制品 | 31.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 12 | 化学原料 | 31.3 | 短线偏弱 | 23.2 | 回避 | weak_or_cooling |
| 13 | IT服务 | 31.3 | 短线偏弱 | 19.2 | 回避 | weak_or_cooling |
| 14 | 其他社会服务 | 31.3 | 短线偏弱 | 19.2 | 回避 | weak_or_cooling |
| 15 | 包装印刷 | 31.3 | 短线偏弱 | 19.2 | 回避 | weak_or_cooling |
| 16 | 其他电源设备 | 31.3 | 短线偏弱 | 16.4 | 回避 | weak_or_cooling |
| 17 | 农化制品 | 31.3 | 短线偏弱 | 14.2 | 回避 | weak_or_cooling |
| 18 | 互联网电商 | 31.3 | 短线偏弱 | 12.2 | 回避 | weak_or_cooling |
| 19 | 军工装备 | 31.3 | 短线偏弱 | 12.2 | 回避 | weak_or_cooling |
| 20 | 元件 | 27.3 | 短线偏弱 | 38.6 | 降温 | weak_or_cooling |

## 分歧板块

当前无明显分歧板块。

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，不构成推荐
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 光学光电子

**趋势持续评分**:
- 趋势分: 44.2
- 趋势等级: 降温
- 趋势 breakdown:
  - radar_score_component: 4.7
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 10.0
  - drawdown_component: 0.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 10.0

**短线爆发评分**:
- 短线分: 34.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 9.3
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

### 2. 其他电子

**趋势持续评分**:
- 趋势分: 41.5
- 趋势等级: 降温
- 趋势 breakdown:
  - radar_score_component: 4.7
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 10.0
  - drawdown_component: 0.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 12.0

**短线爆发评分**:
- 短线分: 31.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 9.3
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

### 3. 元件

**趋势持续评分**:
- 趋势分: 38.6
- 趋势等级: 降温
- 趋势 breakdown:
  - radar_score_component: 4.7
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 10.0
  - drawdown_component: 0.0
  - volatility_component: 1.6
  - data_quality_component: 6.4
  - risk_penalty: 14.0

**短线爆发评分**:
- 短线分: 27.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 9.3
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

### 4. 军工电子

**趋势持续评分**:
- 趋势分: 38.2
- 趋势等级: 降温
- 趋势 breakdown:
  - radar_score_component: 4.7
  - momentum_component: 10.0
  - relative_strength_component: 14.0
  - persistence_component: 10.0
  - drawdown_component: 0.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 10.0

**短线爆发评分**:
- 短线分: 34.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 9.3
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

### 5. 化学制品

**趋势持续评分**:
- 趋势分: 36.2
- 趋势等级: 降温
- 趋势 breakdown:
  - radar_score_component: 4.7
  - momentum_component: 10.0
  - relative_strength_component: 14.0
  - persistence_component: 10.0
  - drawdown_component: 0.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 12.0

**短线爆发评分**:
- 短线分: 31.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 9.3
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

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不构成个股推荐、买卖建议或自动交易指令。
