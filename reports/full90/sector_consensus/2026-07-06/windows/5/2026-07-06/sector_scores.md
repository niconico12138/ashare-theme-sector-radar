# 板块综合评分

**分析日期**: 2026-07-06
**更新时间**: 2026-07-06T14:47:45.097815

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。

## 数据来源

- **板块类型**: industry
- **历史数据范围**: 2026-05-20 ~ 2026-07-06
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

## 趋势持续 Top 90

| 排名 | 板块 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 贵金属 | 88.5 | 重点观察 | 75.3 | 短线活跃 | trend_and_burst_aligned |
| 2 | 工程机械 | 84.0 | 重点观察 | 66.8 | 短线活跃 | trend_and_burst_aligned |
| 3 | 汽车零部件 | 84.0 | 重点观察 | 66.8 | 短线活跃 | trend_and_burst_aligned |
| 4 | 家居用品 | 81.8 | 重点观察 | 58.8 | 短线中性 | neutral |
| 5 | 汽车整车 | 81.8 | 重点观察 | 58.8 | 短线中性 | neutral |
| 6 | 电机 | 81.5 | 重点观察 | 72.3 | 短线活跃 | trend_and_burst_aligned |
| 7 | 小家电 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 8 | 服装家纺 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 9 | 燃气 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 10 | 物流 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 11 | 白色家电 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 12 | 造纸 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 13 | 养殖业 | 78.2 | 观察 | 58.8 | 短线中性 | neutral |
| 14 | 化学制药 | 78.2 | 观察 | 58.8 | 短线中性 | neutral |
| 15 | 农产品加工 | 78.0 | 观察 | 48.8 | 短线降温 | trend_only |
| 16 | 影视院线 | 78.0 | 观察 | 48.8 | 短线降温 | trend_only |
| 17 | 美容护理 | 78.0 | 观察 | 48.8 | 短线降温 | trend_only |
| 18 | 厨卫电器 | 76.8 | 观察 | 52.8 | 短线中性 | neutral |
| 19 | 中药 | 76.2 | 观察 | 58.8 | 短线中性 | neutral |
| 20 | 医药商业 | 76.2 | 观察 | 58.8 | 短线中性 | neutral |
| 21 | 军工装备 | 74.2 | 观察 | 63.8 | 短线中性 | neutral |
| 22 | 风电设备 | 74.0 | 观察 | 63.8 | 短线中性 | neutral |
| 23 | 医疗器械 | 74.0 | 观察 | 58.8 | 短线中性 | neutral |
| 24 | 纺织制造 | 74.0 | 观察 | 58.8 | 短线中性 | neutral |
| 25 | 通用设备 | 74.0 | 观察 | 55.8 | 短线中性 | neutral |
| 26 | 公路铁路运输 | 73.0 | 观察 | 55.8 | 短线中性 | neutral |
| 27 | 旅游及酒店 | 73.0 | 观察 | 55.8 | 短线中性 | neutral |
| 28 | 环保设备 | 73.0 | 观察 | 55.8 | 短线中性 | neutral |
| 29 | 食品加工制造 | 73.0 | 观察 | 58.8 | 短线中性 | neutral |
| 30 | 饮料制造 | 73.0 | 观察 | 55.8 | 短线中性 | neutral |
| 31 | 自动化设备 | 72.2 | 观察 | 63.8 | 短线中性 | neutral |
| 32 | 教育 | 71.2 | 观察 | 58.8 | 短线中性 | neutral |
| 33 | 生物制品 | 71.2 | 观察 | 58.8 | 短线中性 | neutral |
| 34 | 专用设备 | 71.0 | 观察 | 55.8 | 短线中性 | neutral |
| 35 | 煤炭开采加工 | 71.0 | 观察 | 58.8 | 短线中性 | neutral |
| 36 | 石油加工贸易 | 71.0 | 观察 | 55.8 | 短线中性 | neutral |
| 37 | 军工电子 | 69.2 | 观察 | 55.8 | 短线中性 | neutral |
| 38 | 医疗服务 | 68.4 | 观察 | 55.8 | 短线中性 | neutral |
| 39 | 塑料制品 | 68.0 | 观察 | 45.8 | 短线降温 | trend_only |
| 40 | 种植业与林业 | 68.0 | 观察 | 48.8 | 短线降温 | trend_only |
| 41 | 汽车服务及其他 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 42 | 油气开采及服务 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 43 | 环境治理 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 44 | 轨交设备 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 45 | 零售 | 66.0 | 观察 | 45.8 | 短线降温 | trend_only |
| 46 | 黑色家电 | 66.0 | 观察 | 39.8 | 短线降温 | trend_only |
| 47 | 多元金融 | 64.0 | 中性 | 58.8 | 短线中性 | neutral |
| 48 | 计算机设备 | 64.0 | 中性 | 52.8 | 短线中性 | neutral |
| 49 | 工业金属 | 63.8 | 中性 | 55.8 | 短线中性 | neutral |
| 50 | 保险 | 63.4 | 中性 | 48.8 | 短线降温 | neutral |
| 51 | 电网设备 | 63.0 | 中性 | 55.8 | 短线中性 | neutral |
| 52 | IT服务 | 63.0 | 中性 | 42.8 | 短线降温 | neutral |
| 53 | 白酒 | 63.0 | 中性 | 45.8 | 短线降温 | neutral |
| 54 | 软件开发 | 63.0 | 中性 | 45.8 | 短线降温 | neutral |
| 55 | 港口航运 | 61.0 | 中性 | 55.8 | 短线中性 | neutral |
| 56 | 银行 | 61.0 | 中性 | 45.8 | 短线降温 | neutral |
| 57 | 其他社会服务 | 60.0 | 中性 | 45.8 | 短线降温 | neutral |
| 58 | 农化制品 | 60.0 | 中性 | 45.8 | 短线降温 | neutral |
| 59 | 包装印刷 | 60.0 | 中性 | 45.8 | 短线降温 | neutral |
| 60 | 电池 | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 61 | 综合 | 60.0 | 中性 | 45.8 | 短线降温 | neutral |
| 62 | 建筑装饰 | 59.8 | 中性 | 55.8 | 短线中性 | neutral |
| 63 | 钢铁 | 59.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 64 | 建筑材料 | 59.0 | 中性 | 52.8 | 短线中性 | neutral |
| 65 | 证券 | 58.2 | 中性 | 45.8 | 短线降温 | neutral |
| 66 | 金属新材料 | 58.0 | 中性 | 45.8 | 短线降温 | neutral |
| 67 | 化学制品 | 56.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 68 | 化学原料 | 56.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 69 | 文化传媒 | 56.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 70 | 房地产 | 56.0 | 中性 | 55.8 | 短线中性 | neutral |
| 71 | 通信服务 | 55.2 | 中性 | 42.8 | 短线降温 | neutral |
| 72 | 电力 | 53.0 | 中性 | 42.8 | 短线降温 | neutral |
| 73 | 贸易 | 53.0 | 中性 | 45.8 | 短线降温 | neutral |
| 74 | 橡胶制品 | 52.2 | 中性 | 40.3 | 短线降温 | neutral |
| 75 | 互联网电商 | 52.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 76 | 游戏 | 51.2 | 中性 | 28.3 | 短线偏弱 | neutral |
| 77 | 能源金属 | 49.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 78 | 化学纤维 | 47.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 79 | 消费电子 | 45.2 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 80 | 小金属 | 41.2 | 降温 | 24.3 | 短线偏弱 | weak_or_cooling |
| 81 | 光伏设备 | 36.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 82 | 其他电源设备 | 36.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 83 | 光学光电子 | 30.6 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 84 | 通信设备 | 30.4 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 85 | 电子化学品 | 29.6 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 86 | 其他电子 | 29.2 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 87 | 半导体 | 26.6 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 88 | 机场航运 | 25.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 89 | 元件 | 22.4 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 90 | 非金属材料 | 17.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 90

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 贵金属 | 75.3 | 短线活跃 | 88.5 | 重点观察 | trend_and_burst_aligned |
| 2 | 电机 | 72.3 | 短线活跃 | 81.5 | 重点观察 | trend_and_burst_aligned |
| 3 | 工程机械 | 66.8 | 短线活跃 | 84.0 | 重点观察 | trend_and_burst_aligned |
| 4 | 汽车零部件 | 66.8 | 短线活跃 | 84.0 | 重点观察 | trend_and_burst_aligned |
| 5 | 军工装备 | 63.8 | 短线中性 | 74.2 | 观察 | neutral |
| 6 | 风电设备 | 63.8 | 短线中性 | 74.0 | 观察 | neutral |
| 7 | 自动化设备 | 63.8 | 短线中性 | 72.2 | 观察 | neutral |
| 8 | 家居用品 | 58.8 | 短线中性 | 81.8 | 重点观察 | neutral |
| 9 | 汽车整车 | 58.8 | 短线中性 | 81.8 | 重点观察 | neutral |
| 10 | 小家电 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 11 | 服装家纺 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 12 | 燃气 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 13 | 物流 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 14 | 白色家电 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 15 | 造纸 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 16 | 养殖业 | 58.8 | 短线中性 | 78.2 | 观察 | neutral |
| 17 | 化学制药 | 58.8 | 短线中性 | 78.2 | 观察 | neutral |
| 18 | 中药 | 58.8 | 短线中性 | 76.2 | 观察 | neutral |
| 19 | 医药商业 | 58.8 | 短线中性 | 76.2 | 观察 | neutral |
| 20 | 医疗器械 | 58.8 | 短线中性 | 74.0 | 观察 | neutral |
| 21 | 纺织制造 | 58.8 | 短线中性 | 74.0 | 观察 | neutral |
| 22 | 食品加工制造 | 58.8 | 短线中性 | 73.0 | 观察 | neutral |
| 23 | 教育 | 58.8 | 短线中性 | 71.2 | 观察 | neutral |
| 24 | 生物制品 | 58.8 | 短线中性 | 71.2 | 观察 | neutral |
| 25 | 煤炭开采加工 | 58.8 | 短线中性 | 71.0 | 观察 | neutral |
| 26 | 多元金融 | 58.8 | 短线中性 | 64.0 | 中性 | neutral |
| 27 | 通用设备 | 55.8 | 短线中性 | 74.0 | 观察 | neutral |
| 28 | 公路铁路运输 | 55.8 | 短线中性 | 73.0 | 观察 | neutral |
| 29 | 旅游及酒店 | 55.8 | 短线中性 | 73.0 | 观察 | neutral |
| 30 | 环保设备 | 55.8 | 短线中性 | 73.0 | 观察 | neutral |
| 31 | 饮料制造 | 55.8 | 短线中性 | 73.0 | 观察 | neutral |
| 32 | 专用设备 | 55.8 | 短线中性 | 71.0 | 观察 | neutral |
| 33 | 石油加工贸易 | 55.8 | 短线中性 | 71.0 | 观察 | neutral |
| 34 | 军工电子 | 55.8 | 短线中性 | 69.2 | 观察 | neutral |
| 35 | 医疗服务 | 55.8 | 短线中性 | 68.4 | 观察 | neutral |
| 36 | 汽车服务及其他 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 37 | 油气开采及服务 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 38 | 环境治理 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 39 | 轨交设备 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 40 | 工业金属 | 55.8 | 短线中性 | 63.8 | 中性 | neutral |
| 41 | 电网设备 | 55.8 | 短线中性 | 63.0 | 中性 | neutral |
| 42 | 港口航运 | 55.8 | 短线中性 | 61.0 | 中性 | neutral |
| 43 | 建筑装饰 | 55.8 | 短线中性 | 59.8 | 中性 | neutral |
| 44 | 房地产 | 55.8 | 短线中性 | 56.0 | 中性 | neutral |
| 45 | 厨卫电器 | 52.8 | 短线中性 | 76.8 | 观察 | neutral |
| 46 | 计算机设备 | 52.8 | 短线中性 | 64.0 | 中性 | neutral |
| 47 | 建筑材料 | 52.8 | 短线中性 | 59.0 | 中性 | neutral |
| 48 | 消费电子 | 49.8 | 短线降温 | 45.2 | 降温 | weak_or_cooling |
| 49 | 农产品加工 | 48.8 | 短线降温 | 78.0 | 观察 | trend_only |
| 50 | 影视院线 | 48.8 | 短线降温 | 78.0 | 观察 | trend_only |
| 51 | 美容护理 | 48.8 | 短线降温 | 78.0 | 观察 | trend_only |
| 52 | 种植业与林业 | 48.8 | 短线降温 | 68.0 | 观察 | trend_only |
| 53 | 保险 | 48.8 | 短线降温 | 63.4 | 中性 | neutral |
| 54 | 塑料制品 | 45.8 | 短线降温 | 68.0 | 观察 | trend_only |
| 55 | 零售 | 45.8 | 短线降温 | 66.0 | 观察 | trend_only |
| 56 | 白酒 | 45.8 | 短线降温 | 63.0 | 中性 | neutral |
| 57 | 软件开发 | 45.8 | 短线降温 | 63.0 | 中性 | neutral |
| 58 | 银行 | 45.8 | 短线降温 | 61.0 | 中性 | neutral |
| 59 | 其他社会服务 | 45.8 | 短线降温 | 60.0 | 中性 | neutral |
| 60 | 农化制品 | 45.8 | 短线降温 | 60.0 | 中性 | neutral |
| 61 | 包装印刷 | 45.8 | 短线降温 | 60.0 | 中性 | neutral |
| 62 | 综合 | 45.8 | 短线降温 | 60.0 | 中性 | neutral |
| 63 | 证券 | 45.8 | 短线降温 | 58.2 | 中性 | neutral |
| 64 | 金属新材料 | 45.8 | 短线降温 | 58.0 | 中性 | neutral |
| 65 | 贸易 | 45.8 | 短线降温 | 53.0 | 中性 | neutral |
| 66 | IT服务 | 42.8 | 短线降温 | 63.0 | 中性 | neutral |
| 67 | 电池 | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 68 | 通信服务 | 42.8 | 短线降温 | 55.2 | 中性 | neutral |
| 69 | 电力 | 42.8 | 短线降温 | 53.0 | 中性 | neutral |
| 70 | 橡胶制品 | 40.3 | 短线降温 | 52.2 | 中性 | neutral |
| 71 | 黑色家电 | 39.8 | 短线降温 | 66.0 | 观察 | trend_only |
| 72 | 其他电源设备 | 36.8 | 短线降温 | 36.0 | 降温 | weak_or_cooling |
| 73 | 通信设备 | 36.8 | 短线降温 | 30.4 | 偏弱 | weak_or_cooling |
| 74 | 其他电子 | 36.8 | 短线降温 | 29.2 | 偏弱 | weak_or_cooling |
| 75 | 元件 | 36.8 | 短线降温 | 22.4 | 偏弱 | weak_or_cooling |
| 76 | 钢铁 | 34.3 | 短线偏弱 | 59.2 | 中性 | neutral |
| 77 | 化学制品 | 34.3 | 短线偏弱 | 56.2 | 中性 | neutral |
| 78 | 化学原料 | 34.3 | 短线偏弱 | 56.2 | 中性 | neutral |
| 79 | 文化传媒 | 34.3 | 短线偏弱 | 56.2 | 中性 | neutral |
| 80 | 互联网电商 | 34.3 | 短线偏弱 | 52.2 | 中性 | neutral |
| 81 | 化学纤维 | 34.3 | 短线偏弱 | 47.2 | 降温 | weak_or_cooling |
| 82 | 机场航运 | 34.3 | 短线偏弱 | 25.2 | 偏弱 | weak_or_cooling |
| 83 | 游戏 | 28.3 | 短线偏弱 | 51.2 | 中性 | neutral |
| 84 | 能源金属 | 28.3 | 短线偏弱 | 49.2 | 降温 | weak_or_cooling |
| 85 | 光伏设备 | 28.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 86 | 光学光电子 | 25.3 | 短线偏弱 | 30.6 | 偏弱 | weak_or_cooling |
| 87 | 非金属材料 | 25.3 | 短线偏弱 | 17.2 | 偏弱 | weak_or_cooling |
| 88 | 小金属 | 24.3 | 短线偏弱 | 41.2 | 降温 | weak_or_cooling |
| 89 | 电子化学品 | 21.3 | 短线偏弱 | 29.6 | 偏弱 | weak_or_cooling |
| 90 | 半导体 | 21.3 | 短线偏弱 | 26.6 | 偏弱 | weak_or_cooling |

## 分歧板块

### 趋势强但短线不热

| 板块 | 趋势分 | 短线分 | 说明 |
|------|--------|--------|------|
| 农产品加工 | 78.0 | 48.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 影视院线 | 78.0 | 48.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 美容护理 | 78.0 | 48.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 塑料制品 | 68.0 | 45.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 种植业与林业 | 68.0 | 48.8 | 趋势强但短线不热，中长期趋势观察价值较高 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 贵金属

**趋势持续评分**:
- 趋势分: 88.5
- 趋势等级: 重点观察
- 趋势 breakdown:
  - radar_score_component: 13.7
  - momentum_component: 20.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 2.0

**短线爆发评分**:
- 短线分: 75.3
- 短线等级: 短线活跃
- 短线 breakdown:
  - radar_today_component: 27.3
  - one_day_change_component: 20.0
  - three_day_momentum_component: 15.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 8.0
  - burst_risk_penalty: 5.0

**解读**:
- Profile: trend_and_burst_aligned
- Summary: 趋势和短线都强，双重确认
- Watch points:
  - 趋势和短线双重确认，可重点关注
  - 观察是否能持续保持双强态势

### 2. 工程机械

**趋势持续评分**:
- 趋势分: 84.0
- 趋势等级: 重点观察
- 趋势 breakdown:
  - radar_score_component: 11.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 0.0

**短线爆发评分**:
- 短线分: 66.8
- 短线等级: 短线活跃
- 短线 breakdown:
  - radar_today_component: 22.8
  - one_day_change_component: 16.0
  - three_day_momentum_component: 12.0
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

### 3. 汽车零部件

**趋势持续评分**:
- 趋势分: 84.0
- 趋势等级: 重点观察
- 趋势 breakdown:
  - radar_score_component: 11.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 0.0

**短线爆发评分**:
- 短线分: 66.8
- 短线等级: 短线活跃
- 短线 breakdown:
  - radar_today_component: 22.8
  - one_day_change_component: 16.0
  - three_day_momentum_component: 12.0
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

### 4. 家居用品

**趋势持续评分**:
- 趋势分: 81.8
- 趋势等级: 重点观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 4.0
  - data_quality_component: 6.4
  - risk_penalty: 0.0

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

### 5. 汽车整车

**趋势持续评分**:
- 趋势分: 81.8
- 趋势等级: 重点观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 4.0
  - data_quality_component: 6.4
  - risk_penalty: 0.0

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

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
