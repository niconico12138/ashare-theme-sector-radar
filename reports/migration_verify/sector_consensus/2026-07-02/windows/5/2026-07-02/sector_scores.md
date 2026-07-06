# 板块综合评分

**分析日期**: 2026-07-02
**更新时间**: 2026-07-03T20:51:54.961324

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。

## 数据来源

- **板块类型**: both
- **历史数据范围**: 2026-05-20 ~ 2026-07-02
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

## 趋势持续 Top 20

| 排名 | 板块 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 服装家纺 | 73.0 | 观察 | 52.7 | 短线中性 | neutral |
| 2 | 丙烯酸 | 72.4 | 观察 | 34.9 | 短线偏弱 | trend_only |
| 3 | 美容护理 | 71.0 | 观察 | 52.7 | 短线中性 | neutral |
| 4 | 养殖业 | 70.2 | 观察 | 55.7 | 短线中性 | neutral |
| 5 | 中药 | 66.2 | 观察 | 52.7 | 短线中性 | neutral |
| 6 | 工程机械 | 66.0 | 观察 | 52.7 | 短线中性 | neutral |
| 7 | 造纸 | 66.0 | 观察 | 52.7 | 短线中性 | neutral |
| 8 | 银行 | 64.0 | 中性 | 46.7 | 短线降温 | neutral |
| 9 | 纺织制造 | 62.0 | 中性 | 52.7 | 短线中性 | neutral |
| 10 | 贵金属 | 61.9 | 中性 | 55.9 | 短线中性 | neutral |
| 11 | 化学纤维 | 57.0 | 中性 | 52.7 | 短线中性 | neutral |
| 12 | 阿尔茨海默概念 | 55.8 | 中性 | 34.9 | 短线偏弱 | neutral |
| 13 | 白酒概念 | 51.4 | 中性 | 27.9 | 短线偏弱 | neutral |
| 14 | 阿里巴巴概念 | 46.6 | 降温 | 30.9 | 短线偏弱 | weak_or_cooling |
| 15 | 安防 | 46.6 | 降温 | 26.9 | 短线偏弱 | weak_or_cooling |
| 16 | 百度概念 | 46.6 | 降温 | 30.9 | 短线偏弱 | weak_or_cooling |
| 17 | AI语料 | 42.6 | 降温 | 30.9 | 短线偏弱 | weak_or_cooling |
| 18 | BC电池 | 41.6 | 降温 | 23.9 | 短线偏弱 | weak_or_cooling |
| 19 | AI PC | 31.8 | 偏弱 | 26.9 | 短线偏弱 | weak_or_cooling |
| 20 | AI手机 | 24.8 | 偏弱 | 23.9 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 20

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 贵金属 | 55.9 | 短线中性 | 61.9 | 中性 | neutral |
| 2 | 养殖业 | 55.7 | 短线中性 | 70.2 | 观察 | neutral |
| 3 | 服装家纺 | 52.7 | 短线中性 | 73.0 | 观察 | neutral |
| 4 | 美容护理 | 52.7 | 短线中性 | 71.0 | 观察 | neutral |
| 5 | 中药 | 52.7 | 短线中性 | 66.2 | 观察 | neutral |
| 6 | 工程机械 | 52.7 | 短线中性 | 66.0 | 观察 | neutral |
| 7 | 造纸 | 52.7 | 短线中性 | 66.0 | 观察 | neutral |
| 8 | 纺织制造 | 52.7 | 短线中性 | 62.0 | 中性 | neutral |
| 9 | 化学纤维 | 52.7 | 短线中性 | 57.0 | 中性 | neutral |
| 10 | 银行 | 46.7 | 短线降温 | 64.0 | 中性 | neutral |
| 11 | 丙烯酸 | 34.9 | 短线偏弱 | 72.4 | 观察 | trend_only |
| 12 | 阿尔茨海默概念 | 34.9 | 短线偏弱 | 55.8 | 中性 | neutral |
| 13 | 阿里巴巴概念 | 30.9 | 短线偏弱 | 46.6 | 降温 | weak_or_cooling |
| 14 | 百度概念 | 30.9 | 短线偏弱 | 46.6 | 降温 | weak_or_cooling |
| 15 | AI语料 | 30.9 | 短线偏弱 | 42.6 | 降温 | weak_or_cooling |
| 16 | 白酒概念 | 27.9 | 短线偏弱 | 51.4 | 中性 | neutral |
| 17 | 安防 | 26.9 | 短线偏弱 | 46.6 | 降温 | weak_or_cooling |
| 18 | AI PC | 26.9 | 短线偏弱 | 31.8 | 偏弱 | weak_or_cooling |
| 19 | BC电池 | 23.9 | 短线偏弱 | 41.6 | 降温 | weak_or_cooling |
| 20 | AI手机 | 23.9 | 短线偏弱 | 24.8 | 偏弱 | weak_or_cooling |

## 分歧板块

### 趋势强但短线不热

| 板块 | 趋势分 | 短线分 | 说明 |
|------|--------|--------|------|
| 丙烯酸 | 72.4 | 34.9 | 趋势强但短线不热，中长期趋势观察价值较高 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 服装家纺

**趋势持续评分**:
- 趋势分: 73.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.8
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 8.0
  - risk_penalty: 2.0

**短线爆发评分**:
- 短线分: 52.7
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 11.7
  - one_day_change_component: 12.0
  - three_day_momentum_component: 9.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 10.0
  - burst_risk_penalty: 0.0

**解读**:
- Profile: neutral
- Summary: 表现中性，可作为备选观察
- Watch points:
  - 等待更多确认信号
  - 关注后续表现

### 2. 丙烯酸

**趋势持续评分**:
- 趋势分: 72.4
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 2.9
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 3.4
  - risk_penalty: 0.0

**短线爆发评分**:
- 短线分: 34.9
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 5.7
  - one_day_change_component: 8.0
  - three_day_momentum_component: 9.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 4.2
  - burst_risk_penalty: 2.0

**解读**:
- Profile: trend_only
- Summary: 趋势强但短线不热，中长期趋势观察价值较高
- Watch points:
  - 趋势持续性好，但短线缺乏爆发力
  - 观察是否有催化剂推动短线表现

### 3. 美容护理

**趋势持续评分**:
- 趋势分: 71.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.8
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 3.2
  - data_quality_component: 8.0
  - risk_penalty: 2.0

**短线爆发评分**:
- 短线分: 52.7
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 11.7
  - one_day_change_component: 12.0
  - three_day_momentum_component: 9.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 10.0
  - burst_risk_penalty: 0.0

**解读**:
- Profile: neutral
- Summary: 表现中性，可作为备选观察
- Watch points:
  - 等待更多确认信号
  - 关注后续表现

### 4. 养殖业

**趋势持续评分**:
- 趋势分: 70.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.8
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 2.4
  - data_quality_component: 8.0
  - risk_penalty: 4.0

**短线爆发评分**:
- 短线分: 55.7
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 11.7
  - one_day_change_component: 12.0
  - three_day_momentum_component: 12.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 10.0
  - burst_risk_penalty: 0.0

**解读**:
- Profile: neutral
- Summary: 表现中性，可作为备选观察
- Watch points:
  - 等待更多确认信号
  - 关注后续表现

### 5. 中药

**趋势持续评分**:
- 趋势分: 66.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.8
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 2.4
  - data_quality_component: 8.0
  - risk_penalty: 6.0

**短线爆发评分**:
- 短线分: 52.7
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 11.7
  - one_day_change_component: 12.0
  - three_day_momentum_component: 9.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 10.0
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

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
