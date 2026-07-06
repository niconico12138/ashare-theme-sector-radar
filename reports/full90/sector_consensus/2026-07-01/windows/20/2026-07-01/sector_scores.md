# 板块综合评分

**分析日期**: 2026-07-01
**更新时间**: 2026-07-05T18:21:34.338348

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。

## 数据来源

- **板块类型**: industry
- **历史数据范围**: 2026-05-20 ~ 2026-07-01
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
| 1 | 电子化学品 | 71.4 | 观察 | 58.8 | 短线中性 | neutral |
| 2 | 半导体 | 58.5 | 中性 | 37.3 | 短线降温 | neutral |
| 3 | 证券 | 56.2 | 中性 | 66.8 | 短线活跃 | neutral |
| 4 | 军工电子 | 55.0 | 中性 | 58.8 | 短线中性 | neutral |
| 5 | 小金属 | 52.4 | 中性 | 45.8 | 短线降温 | neutral |
| 6 | 金属新材料 | 51.2 | 中性 | 55.8 | 短线中性 | neutral |
| 7 | 光学光电子 | 50.2 | 中性 | 45.8 | 短线降温 | neutral |
| 8 | 塑料制品 | 50.0 | 中性 | 55.8 | 短线中性 | neutral |
| 9 | 医疗服务 | 48.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 10 | 保险 | 47.6 | 降温 | 72.3 | 短线活跃 | burst_without_trend_confirmation |
| 11 | 自动化设备 | 47.2 | 降温 | 55.8 | 短线中性 | neutral |
| 12 | 化学制品 | 45.0 | 降温 | 63.8 | 短线中性 | neutral |
| 13 | 元件 | 43.6 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 14 | 其他电子 | 43.6 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 15 | 化学制药 | 42.5 | 降温 | 75.3 | 短线活跃 | burst_without_trend_confirmation |
| 16 | 通用设备 | 42.0 | 降温 | 55.8 | 短线中性 | neutral |
| 17 | 化学原料 | 41.0 | 降温 | 63.8 | 短线中性 | neutral |
| 18 | 非金属材料 | 40.5 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 19 | 生物制品 | 39.2 | 降温 | 64.8 | 短线中性 | neutral |
| 20 | 环保设备 | 38.0 | 降温 | 55.8 | 短线中性 | neutral |
| 21 | 白色家电 | 38.0 | 降温 | 58.8 | 短线中性 | neutral |
| 22 | 其他社会服务 | 36.0 | 降温 | 63.8 | 短线中性 | neutral |
| 23 | 医疗器械 | 35.0 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 24 | 游戏 | 35.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 25 | 互联网电商 | 34.0 | 偏弱 | 61.8 | 短线中性 | neutral |
| 26 | 橡胶制品 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 27 | 计算机设备 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 28 | 轨交设备 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 29 | 养殖业 | 32.2 | 偏弱 | 67.3 | 短线活跃 | burst_without_trend_confirmation |
| 30 | 专用设备 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 31 | 包装印刷 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 32 | 化学纤维 | 31.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 33 | 建筑材料 | 31.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 34 | 纺织制造 | 31.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 35 | 物流 | 30.0 | 偏弱 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 36 | 零售 | 30.0 | 偏弱 | 63.8 | 短线中性 | neutral |
| 37 | 教育 | 28.2 | 偏弱 | 69.3 | 短线活跃 | burst_without_trend_confirmation |
| 38 | 能源金属 | 27.4 | 偏弱 | 55.8 | 短线中性 | neutral |
| 39 | 汽车零部件 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 40 | 环境治理 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 41 | 软件开发 | 27.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 42 | 消费电子 | 26.4 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 43 | 军工装备 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 44 | 工程机械 | 26.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 45 | 汽车服务及其他 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 46 | 中药 | 25.0 | 偏弱 | 61.8 | 短线中性 | neutral |
| 47 | 医药商业 | 25.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 48 | 服装家纺 | 25.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 49 | 综合 | 25.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 50 | 美容护理 | 25.0 | 偏弱 | 61.8 | 短线中性 | neutral |
| 51 | 黑色家电 | 24.2 | 偏弱 | 37.3 | 短线降温 | weak_or_cooling |
| 52 | IT服务 | 24.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 53 | 工业金属 | 24.2 | 偏弱 | 52.8 | 短线中性 | neutral |
| 54 | 通信服务 | 24.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 55 | 厨卫电器 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 56 | 银行 | 24.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 57 | 影视院线 | 23.2 | 偏弱 | 63.8 | 短线中性 | neutral |
| 58 | 机场航运 | 23.2 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 59 | 油气开采及服务 | 23.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 60 | 光伏设备 | 23.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 61 | 多元金融 | 22.2 | 偏弱 | 58.8 | 短线中性 | neutral |
| 62 | 公路铁路运输 | 22.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 63 | 农化制品 | 22.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 64 | 建筑装饰 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 65 | 文化传媒 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 66 | 旅游及酒店 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 67 | 港口航运 | 22.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 68 | 白酒 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 69 | 石油加工贸易 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 70 | 造纸 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 71 | 钢铁 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 72 | 风电设备 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 73 | 食品加工制造 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 74 | 其他电源设备 | 21.4 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 75 | 电池 | 21.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 76 | 农产品加工 | 21.0 | 偏弱 | 61.8 | 短线中性 | neutral |
| 77 | 种植业与林业 | 21.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 78 | 家居用品 | 20.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 79 | 电网设备 | 20.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 80 | 小家电 | 19.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 81 | 燃气 | 19.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 82 | 煤炭开采加工 | 18.2 | 偏弱 | 58.8 | 短线中性 | neutral |
| 83 | 汽车整车 | 18.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 84 | 电力 | 18.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 85 | 电机 | 18.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 86 | 饮料制造 | 18.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 87 | 通信设备 | 17.4 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 88 | 房地产 | 16.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 89 | 贵金属 | 14.4 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 90 | 贸易 | 13.2 | 偏弱 | 52.8 | 短线中性 | neutral |

## 短线爆发 Top 90

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 化学制药 | 75.3 | 短线活跃 | 42.5 | 降温 | burst_without_trend_confirmation |
| 2 | 保险 | 72.3 | 短线活跃 | 47.6 | 降温 | burst_without_trend_confirmation |
| 3 | 教育 | 69.3 | 短线活跃 | 28.2 | 偏弱 | burst_without_trend_confirmation |
| 4 | 养殖业 | 67.3 | 短线活跃 | 32.2 | 偏弱 | burst_without_trend_confirmation |
| 5 | 证券 | 66.8 | 短线活跃 | 56.2 | 中性 | neutral |
| 6 | 医疗服务 | 66.8 | 短线活跃 | 48.2 | 降温 | burst_without_trend_confirmation |
| 7 | 医疗器械 | 66.8 | 短线活跃 | 35.0 | 降温 | burst_without_trend_confirmation |
| 8 | 物流 | 66.8 | 短线活跃 | 30.0 | 偏弱 | burst_without_trend_confirmation |
| 9 | 生物制品 | 64.8 | 短线中性 | 39.2 | 降温 | neutral |
| 10 | 化学制品 | 63.8 | 短线中性 | 45.0 | 降温 | neutral |
| 11 | 化学原料 | 63.8 | 短线中性 | 41.0 | 降温 | neutral |
| 12 | 其他社会服务 | 63.8 | 短线中性 | 36.0 | 降温 | neutral |
| 13 | 零售 | 63.8 | 短线中性 | 30.0 | 偏弱 | neutral |
| 14 | 影视院线 | 63.8 | 短线中性 | 23.2 | 偏弱 | neutral |
| 15 | 互联网电商 | 61.8 | 短线中性 | 34.0 | 偏弱 | neutral |
| 16 | 中药 | 61.8 | 短线中性 | 25.0 | 偏弱 | neutral |
| 17 | 美容护理 | 61.8 | 短线中性 | 25.0 | 偏弱 | neutral |
| 18 | 农产品加工 | 61.8 | 短线中性 | 21.0 | 偏弱 | neutral |
| 19 | 电子化学品 | 58.8 | 短线中性 | 71.4 | 观察 | neutral |
| 20 | 军工电子 | 58.8 | 短线中性 | 55.0 | 中性 | neutral |
| 21 | 白色家电 | 58.8 | 短线中性 | 38.0 | 降温 | neutral |
| 22 | 软件开发 | 58.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 23 | 医药商业 | 58.8 | 短线中性 | 25.0 | 偏弱 | neutral |
| 24 | 服装家纺 | 58.8 | 短线中性 | 25.0 | 偏弱 | neutral |
| 25 | 综合 | 58.8 | 短线中性 | 25.0 | 偏弱 | neutral |
| 26 | 多元金融 | 58.8 | 短线中性 | 22.2 | 偏弱 | neutral |
| 27 | 种植业与林业 | 58.8 | 短线中性 | 21.0 | 偏弱 | neutral |
| 28 | 小家电 | 58.8 | 短线中性 | 19.0 | 偏弱 | neutral |
| 29 | 燃气 | 58.8 | 短线中性 | 19.0 | 偏弱 | neutral |
| 30 | 煤炭开采加工 | 58.8 | 短线中性 | 18.2 | 偏弱 | neutral |
| 31 | 金属新材料 | 55.8 | 短线中性 | 51.2 | 中性 | neutral |
| 32 | 塑料制品 | 55.8 | 短线中性 | 50.0 | 中性 | neutral |
| 33 | 自动化设备 | 55.8 | 短线中性 | 47.2 | 降温 | neutral |
| 34 | 通用设备 | 55.8 | 短线中性 | 42.0 | 降温 | neutral |
| 35 | 环保设备 | 55.8 | 短线中性 | 38.0 | 降温 | neutral |
| 36 | 橡胶制品 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 37 | 计算机设备 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 38 | 轨交设备 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 39 | 专用设备 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 40 | 包装印刷 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 41 | 能源金属 | 55.8 | 短线中性 | 27.4 | 偏弱 | neutral |
| 42 | 汽车零部件 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 43 | 环境治理 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 44 | 军工装备 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 45 | 汽车服务及其他 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 46 | IT服务 | 55.8 | 短线中性 | 24.2 | 偏弱 | neutral |
| 47 | 通信服务 | 55.8 | 短线中性 | 24.2 | 偏弱 | neutral |
| 48 | 油气开采及服务 | 55.8 | 短线中性 | 23.0 | 偏弱 | neutral |
| 49 | 建筑装饰 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 50 | 文化传媒 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 51 | 旅游及酒店 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 52 | 白酒 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 53 | 石油加工贸易 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 54 | 造纸 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 55 | 钢铁 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 56 | 风电设备 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 57 | 食品加工制造 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 58 | 家居用品 | 55.8 | 短线中性 | 20.0 | 偏弱 | neutral |
| 59 | 汽车整车 | 55.8 | 短线中性 | 18.0 | 偏弱 | neutral |
| 60 | 电力 | 55.8 | 短线中性 | 18.0 | 偏弱 | neutral |
| 61 | 电机 | 55.8 | 短线中性 | 18.0 | 偏弱 | neutral |
| 62 | 饮料制造 | 55.8 | 短线中性 | 18.0 | 偏弱 | neutral |
| 63 | 房地产 | 55.8 | 短线中性 | 16.0 | 偏弱 | neutral |
| 64 | 建筑材料 | 52.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 65 | 纺织制造 | 52.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 66 | 工程机械 | 52.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 67 | 工业金属 | 52.8 | 短线中性 | 24.2 | 偏弱 | neutral |
| 68 | 公路铁路运输 | 52.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 69 | 农化制品 | 52.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 70 | 贸易 | 52.8 | 短线中性 | 13.2 | 偏弱 | neutral |
| 71 | 化学纤维 | 49.8 | 短线降温 | 31.0 | 偏弱 | weak_or_cooling |
| 72 | 机场航运 | 49.8 | 短线降温 | 23.2 | 偏弱 | weak_or_cooling |
| 73 | 港口航运 | 49.8 | 短线降温 | 22.0 | 偏弱 | weak_or_cooling |
| 74 | 小金属 | 45.8 | 短线降温 | 52.4 | 中性 | neutral |
| 75 | 光学光电子 | 45.8 | 短线降温 | 50.2 | 中性 | neutral |
| 76 | 游戏 | 45.8 | 短线降温 | 35.0 | 降温 | weak_or_cooling |
| 77 | 厨卫电器 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 78 | 光伏设备 | 45.8 | 短线降温 | 23.0 | 偏弱 | weak_or_cooling |
| 79 | 电池 | 45.8 | 短线降温 | 21.2 | 偏弱 | weak_or_cooling |
| 80 | 电网设备 | 42.8 | 短线降温 | 20.0 | 偏弱 | weak_or_cooling |
| 81 | 银行 | 39.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 82 | 贵金属 | 39.8 | 短线降温 | 14.4 | 偏弱 | weak_or_cooling |
| 83 | 半导体 | 37.3 | 短线降温 | 58.5 | 中性 | neutral |
| 84 | 黑色家电 | 37.3 | 短线降温 | 24.2 | 偏弱 | weak_or_cooling |
| 85 | 其他电子 | 34.3 | 短线偏弱 | 43.6 | 降温 | weak_or_cooling |
| 86 | 消费电子 | 31.3 | 短线偏弱 | 26.4 | 偏弱 | weak_or_cooling |
| 87 | 其他电源设备 | 31.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 88 | 通信设备 | 31.3 | 短线偏弱 | 17.4 | 偏弱 | weak_or_cooling |
| 89 | 元件 | 28.3 | 短线偏弱 | 43.6 | 降温 | weak_or_cooling |
| 90 | 非金属材料 | 25.3 | 短线偏弱 | 40.5 | 降温 | weak_or_cooling |

## 分歧板块

### 短线强但趋势未确认

| 板块 | 短线分 | 趋势分 | 说明 |
|------|--------|--------|------|
| 医疗服务 | 66.8 | 48.2 | 短线强但趋势未确认，需谨慎 |
| 保险 | 72.3 | 47.6 | 短线强但趋势未确认，需谨慎 |
| 化学制药 | 75.3 | 42.5 | 短线强但趋势未确认，需谨慎 |
| 医疗器械 | 66.8 | 35.0 | 短线强但趋势未确认，需谨慎 |
| 养殖业 | 67.3 | 32.2 | 短线强但趋势未确认，需谨慎 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 电子化学品

**趋势持续评分**:
- 趋势分: 71.4
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 6.0
  - volatility_component: 1.6
  - data_quality_component: 6.4
  - risk_penalty: 6.0

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

### 2. 半导体

**趋势持续评分**:
- 趋势分: 58.5
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 4.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 6.0

**短线爆发评分**:
- 短线分: 37.3
- 短线等级: 短线降温
- 短线 breakdown:
  - radar_today_component: 3.3
  - one_day_change_component: 4.0
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

### 3. 证券

**趋势持续评分**:
- 趋势分: 56.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 11.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 10.0
  - drawdown_component: 4.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 8.0

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
- Profile: neutral
- Summary: 表现中性，可作为备选观察
- Watch points:
  - 等待更多确认信号
  - 关注后续表现

### 4. 军工电子

**趋势持续评分**:
- 趋势分: 55.0
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 10.0
  - relative_strength_component: 14.0
  - persistence_component: 15.0
  - drawdown_component: 4.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 6.0

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

### 5. 小金属

**趋势持续评分**:
- 趋势分: 52.4
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 4.0
  - volatility_component: 1.6
  - data_quality_component: 6.4
  - risk_penalty: 10.0

**短线爆发评分**:
- 短线分: 45.8
- 短线等级: 短线降温
- 短线 breakdown:
  - radar_today_component: 10.8
  - one_day_change_component: 8.0
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

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
