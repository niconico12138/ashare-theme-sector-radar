# 板块综合评分

**分析日期**: 2026-07-01
**更新时间**: 2026-07-05T18:21:34.311040

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

## 趋势持续 Top 90

| 排名 | 板块 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 电子化学品 | 76.2 | 观察 | 58.8 | 短线中性 | neutral |
| 2 | 半导体 | 71.5 | 观察 | 37.3 | 短线降温 | trend_only |
| 3 | 医疗服务 | 70.2 | 观察 | 66.8 | 短线活跃 | trend_and_burst_aligned |
| 4 | 化学制药 | 57.6 | 中性 | 75.3 | 短线活跃 | neutral |
| 5 | 生物制品 | 56.4 | 中性 | 69.8 | 短线活跃 | neutral |
| 6 | 证券 | 54.4 | 中性 | 66.8 | 短线活跃 | neutral |
| 7 | 游戏 | 52.0 | 中性 | 45.8 | 短线降温 | neutral |
| 8 | 光学光电子 | 48.2 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 9 | 军工电子 | 46.0 | 降温 | 58.8 | 短线中性 | neutral |
| 10 | 环保设备 | 46.0 | 降温 | 55.8 | 短线中性 | neutral |
| 11 | 化学制品 | 43.0 | 降温 | 63.8 | 短线中性 | neutral |
| 12 | 互联网电商 | 42.0 | 降温 | 61.8 | 短线中性 | neutral |
| 13 | 自动化设备 | 42.0 | 降温 | 55.8 | 短线中性 | neutral |
| 14 | 其他电子 | 41.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 15 | 医疗器械 | 40.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 16 | 保险 | 39.6 | 降温 | 72.3 | 短线活跃 | burst_without_trend_confirmation |
| 17 | 物流 | 39.0 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 18 | 养殖业 | 38.5 | 降温 | 72.3 | 短线活跃 | burst_without_trend_confirmation |
| 19 | 小金属 | 38.4 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 20 | 白色家电 | 38.0 | 降温 | 58.8 | 短线中性 | neutral |
| 21 | 计算机设备 | 38.0 | 降温 | 55.8 | 短线中性 | neutral |
| 22 | 化学原料 | 36.2 | 降温 | 63.8 | 短线中性 | neutral |
| 23 | 橡胶制品 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 24 | 通用设备 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 25 | 其他社会服务 | 34.0 | 偏弱 | 63.8 | 短线中性 | neutral |
| 26 | 燃气 | 34.0 | 偏弱 | 63.8 | 短线中性 | neutral |
| 27 | 美容护理 | 34.0 | 偏弱 | 61.8 | 短线中性 | neutral |
| 28 | 零售 | 34.0 | 偏弱 | 63.8 | 短线中性 | neutral |
| 29 | 轨交设备 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 30 | 元件 | 32.6 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 31 | 中药 | 31.2 | 偏弱 | 61.8 | 短线中性 | neutral |
| 32 | 农产品加工 | 31.2 | 偏弱 | 61.8 | 短线中性 | neutral |
| 33 | 专用设备 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 34 | 包装印刷 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 35 | 塑料制品 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 36 | 建筑材料 | 31.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 37 | 汽车服务及其他 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 38 | 油气开采及服务 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 39 | 港口航运 | 31.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 40 | 环境治理 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 41 | 白酒 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 42 | 纺织制造 | 31.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 43 | 造纸 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 44 | 钢铁 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 45 | 食品加工制造 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 46 | 饮料制造 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 47 | 服装家纺 | 29.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 48 | 综合 | 29.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 49 | 光伏设备 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 50 | 厨卫电器 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 51 | 银行 | 28.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 52 | 能源金属 | 27.4 | 偏弱 | 55.8 | 短线中性 | neutral |
| 53 | 影视院线 | 27.2 | 偏弱 | 63.8 | 短线中性 | neutral |
| 54 | 小家电 | 27.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 55 | 医药商业 | 26.2 | 偏弱 | 58.8 | 短线中性 | neutral |
| 56 | 公路铁路运输 | 26.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 57 | 化学纤维 | 26.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 58 | 家居用品 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 59 | 工程机械 | 26.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 60 | 文化传媒 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 61 | 旅游及酒店 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 62 | 石油加工贸易 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 63 | 风电设备 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 64 | 种植业与林业 | 25.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 65 | 教育 | 24.4 | 偏弱 | 64.3 | 短线中性 | neutral |
| 66 | 黑色家电 | 24.2 | 偏弱 | 37.3 | 短线降温 | weak_or_cooling |
| 67 | 多元金融 | 24.2 | 偏弱 | 58.8 | 短线中性 | neutral |
| 68 | IT服务 | 24.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 69 | 通信服务 | 24.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 70 | 金属新材料 | 24.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 71 | 军工装备 | 24.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 72 | 建筑装饰 | 24.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 73 | 房地产 | 24.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 74 | 贸易 | 24.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 75 | 电网设备 | 23.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 76 | 非金属材料 | 22.6 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 77 | 煤炭开采加工 | 22.2 | 偏弱 | 58.8 | 短线中性 | neutral |
| 78 | 汽车零部件 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 79 | 电机 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 80 | 消费电子 | 21.4 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 81 | 农化制品 | 21.2 | 偏弱 | 52.8 | 短线中性 | neutral |
| 82 | 机场航运 | 21.2 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 83 | 汽车整车 | 20.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 84 | 电力 | 20.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 85 | 其他电源设备 | 19.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 86 | 工业金属 | 19.2 | 偏弱 | 52.8 | 短线中性 | neutral |
| 87 | 软件开发 | 19.2 | 偏弱 | 58.8 | 短线中性 | neutral |
| 88 | 通信设备 | 17.4 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 89 | 贵金属 | 16.4 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 90 | 电池 | 16.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |

## 短线爆发 Top 90

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 化学制药 | 75.3 | 短线活跃 | 57.6 | 中性 | neutral |
| 2 | 保险 | 72.3 | 短线活跃 | 39.6 | 降温 | burst_without_trend_confirmation |
| 3 | 养殖业 | 72.3 | 短线活跃 | 38.5 | 降温 | burst_without_trend_confirmation |
| 4 | 生物制品 | 69.8 | 短线活跃 | 56.4 | 中性 | neutral |
| 5 | 医疗服务 | 66.8 | 短线活跃 | 70.2 | 观察 | trend_and_burst_aligned |
| 6 | 证券 | 66.8 | 短线活跃 | 54.4 | 中性 | neutral |
| 7 | 医疗器械 | 66.8 | 短线活跃 | 40.2 | 降温 | burst_without_trend_confirmation |
| 8 | 物流 | 66.8 | 短线活跃 | 39.0 | 降温 | burst_without_trend_confirmation |
| 9 | 教育 | 64.3 | 短线中性 | 24.4 | 偏弱 | neutral |
| 10 | 化学制品 | 63.8 | 短线中性 | 43.0 | 降温 | neutral |
| 11 | 化学原料 | 63.8 | 短线中性 | 36.2 | 降温 | neutral |
| 12 | 其他社会服务 | 63.8 | 短线中性 | 34.0 | 偏弱 | neutral |
| 13 | 燃气 | 63.8 | 短线中性 | 34.0 | 偏弱 | neutral |
| 14 | 零售 | 63.8 | 短线中性 | 34.0 | 偏弱 | neutral |
| 15 | 影视院线 | 63.8 | 短线中性 | 27.2 | 偏弱 | neutral |
| 16 | 互联网电商 | 61.8 | 短线中性 | 42.0 | 降温 | neutral |
| 17 | 美容护理 | 61.8 | 短线中性 | 34.0 | 偏弱 | neutral |
| 18 | 中药 | 61.8 | 短线中性 | 31.2 | 偏弱 | neutral |
| 19 | 农产品加工 | 61.8 | 短线中性 | 31.2 | 偏弱 | neutral |
| 20 | 电子化学品 | 58.8 | 短线中性 | 76.2 | 观察 | neutral |
| 21 | 军工电子 | 58.8 | 短线中性 | 46.0 | 降温 | neutral |
| 22 | 白色家电 | 58.8 | 短线中性 | 38.0 | 降温 | neutral |
| 23 | 服装家纺 | 58.8 | 短线中性 | 29.0 | 偏弱 | neutral |
| 24 | 综合 | 58.8 | 短线中性 | 29.0 | 偏弱 | neutral |
| 25 | 小家电 | 58.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 26 | 医药商业 | 58.8 | 短线中性 | 26.2 | 偏弱 | neutral |
| 27 | 种植业与林业 | 58.8 | 短线中性 | 25.0 | 偏弱 | neutral |
| 28 | 多元金融 | 58.8 | 短线中性 | 24.2 | 偏弱 | neutral |
| 29 | 煤炭开采加工 | 58.8 | 短线中性 | 22.2 | 偏弱 | neutral |
| 30 | 软件开发 | 58.8 | 短线中性 | 19.2 | 偏弱 | neutral |
| 31 | 环保设备 | 55.8 | 短线中性 | 46.0 | 降温 | neutral |
| 32 | 自动化设备 | 55.8 | 短线中性 | 42.0 | 降温 | neutral |
| 33 | 计算机设备 | 55.8 | 短线中性 | 38.0 | 降温 | neutral |
| 34 | 橡胶制品 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 35 | 通用设备 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 36 | 轨交设备 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 37 | 专用设备 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 38 | 包装印刷 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 39 | 塑料制品 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 40 | 汽车服务及其他 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 41 | 油气开采及服务 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 42 | 环境治理 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 43 | 白酒 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 44 | 造纸 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 45 | 钢铁 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 46 | 食品加工制造 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 47 | 饮料制造 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 48 | 能源金属 | 55.8 | 短线中性 | 27.4 | 偏弱 | neutral |
| 49 | 家居用品 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 50 | 文化传媒 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 51 | 旅游及酒店 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 52 | 石油加工贸易 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 53 | 风电设备 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 54 | IT服务 | 55.8 | 短线中性 | 24.2 | 偏弱 | neutral |
| 55 | 通信服务 | 55.8 | 短线中性 | 24.2 | 偏弱 | neutral |
| 56 | 金属新材料 | 55.8 | 短线中性 | 24.2 | 偏弱 | neutral |
| 57 | 军工装备 | 55.8 | 短线中性 | 24.0 | 偏弱 | neutral |
| 58 | 建筑装饰 | 55.8 | 短线中性 | 24.0 | 偏弱 | neutral |
| 59 | 房地产 | 55.8 | 短线中性 | 24.0 | 偏弱 | neutral |
| 60 | 汽车零部件 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 61 | 电机 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 62 | 汽车整车 | 55.8 | 短线中性 | 20.0 | 偏弱 | neutral |
| 63 | 电力 | 55.8 | 短线中性 | 20.0 | 偏弱 | neutral |
| 64 | 建筑材料 | 52.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 65 | 纺织制造 | 52.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 66 | 公路铁路运输 | 52.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 67 | 工程机械 | 52.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 68 | 贸易 | 52.8 | 短线中性 | 24.0 | 偏弱 | neutral |
| 69 | 农化制品 | 52.8 | 短线中性 | 21.2 | 偏弱 | neutral |
| 70 | 工业金属 | 52.8 | 短线中性 | 19.2 | 偏弱 | neutral |
| 71 | 港口航运 | 49.8 | 短线降温 | 31.0 | 偏弱 | weak_or_cooling |
| 72 | 化学纤维 | 49.8 | 短线降温 | 26.0 | 偏弱 | weak_or_cooling |
| 73 | 机场航运 | 49.8 | 短线降温 | 21.2 | 偏弱 | weak_or_cooling |
| 74 | 游戏 | 45.8 | 短线降温 | 52.0 | 中性 | neutral |
| 75 | 光学光电子 | 45.8 | 短线降温 | 48.2 | 降温 | weak_or_cooling |
| 76 | 小金属 | 45.8 | 短线降温 | 38.4 | 降温 | weak_or_cooling |
| 77 | 光伏设备 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 78 | 厨卫电器 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 79 | 电池 | 45.8 | 短线降温 | 16.2 | 偏弱 | weak_or_cooling |
| 80 | 电网设备 | 42.8 | 短线降温 | 23.0 | 偏弱 | weak_or_cooling |
| 81 | 银行 | 39.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 82 | 贵金属 | 39.8 | 短线降温 | 16.4 | 偏弱 | weak_or_cooling |
| 83 | 半导体 | 37.3 | 短线降温 | 71.5 | 观察 | trend_only |
| 84 | 黑色家电 | 37.3 | 短线降温 | 24.2 | 偏弱 | weak_or_cooling |
| 85 | 其他电子 | 34.3 | 短线偏弱 | 41.5 | 降温 | weak_or_cooling |
| 86 | 消费电子 | 31.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 87 | 其他电源设备 | 31.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 88 | 通信设备 | 31.3 | 短线偏弱 | 17.4 | 偏弱 | weak_or_cooling |
| 89 | 元件 | 28.3 | 短线偏弱 | 32.6 | 偏弱 | weak_or_cooling |
| 90 | 非金属材料 | 25.3 | 短线偏弱 | 22.6 | 偏弱 | weak_or_cooling |

## 分歧板块

### 短线强但趋势未确认

| 板块 | 短线分 | 趋势分 | 说明 |
|------|--------|--------|------|
| 医疗器械 | 66.8 | 40.2 | 短线强但趋势未确认，需谨慎 |
| 保险 | 72.3 | 39.6 | 短线强但趋势未确认，需谨慎 |
| 物流 | 66.8 | 39.0 | 短线强但趋势未确认，需谨慎 |
| 养殖业 | 72.3 | 38.5 | 短线强但趋势未确认，需谨慎 |

### 趋势强但短线不热

| 板块 | 趋势分 | 短线分 | 说明 |
|------|--------|--------|------|
| 半导体 | 71.5 | 37.3 | 趋势强但短线不热，中长期趋势观察价值较高 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 电子化学品

**趋势持续评分**:
- 趋势分: 76.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 6.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 2.0

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
- 趋势分: 71.5
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 2.0

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
- Profile: trend_only
- Summary: 趋势强但短线不热，中长期趋势观察价值较高
- Watch points:
  - 趋势持续性好，但短线缺乏爆发力
  - 观察是否有催化剂推动短线表现

### 3. 医疗服务

**趋势持续评分**:
- 趋势分: 70.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 11.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 6.0

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

### 4. 化学制药

**趋势持续评分**:
- 趋势分: 57.6
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 13.7
  - momentum_component: 15.0
  - relative_strength_component: 17.0
  - persistence_component: 10.0
  - drawdown_component: 4.0
  - volatility_component: 1.6
  - data_quality_component: 6.4
  - risk_penalty: 10.0

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
- Profile: neutral
- Summary: 表现中性，可作为备选观察
- Watch points:
  - 等待更多确认信号
  - 关注后续表现

### 5. 生物制品

**趋势持续评分**:
- 趋势分: 56.4
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 11.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 10.0
  - drawdown_component: 4.0
  - volatility_component: 1.6
  - data_quality_component: 6.4
  - risk_penalty: 12.0

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
- Profile: neutral
- Summary: 表现中性，可作为备选观察
- Watch points:
  - 等待更多确认信号
  - 关注后续表现

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
