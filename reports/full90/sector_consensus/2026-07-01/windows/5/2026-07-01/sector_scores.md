# 板块综合评分

**分析日期**: 2026-07-01
**更新时间**: 2026-07-05T18:21:34.282631

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
| 1 | 电子化学品 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 2 | 证券 | 67.2 | 观察 | 66.8 | 短线活跃 | trend_and_burst_aligned |
| 3 | 半导体 | 64.5 | 中性 | 37.3 | 短线降温 | neutral |
| 4 | 保险 | 62.6 | 中性 | 72.3 | 短线活跃 | neutral |
| 5 | 教育 | 62.5 | 中性 | 69.3 | 短线活跃 | neutral |
| 6 | 物流 | 62.2 | 中性 | 66.8 | 短线活跃 | neutral |
| 7 | 养殖业 | 61.5 | 中性 | 72.3 | 短线活跃 | neutral |
| 8 | 游戏 | 61.0 | 中性 | 45.8 | 短线降温 | neutral |
| 9 | 生物制品 | 60.4 | 中性 | 69.8 | 短线活跃 | neutral |
| 10 | 光学光电子 | 60.2 | 中性 | 45.8 | 短线降温 | neutral |
| 11 | 医疗服务 | 57.4 | 中性 | 66.8 | 短线活跃 | neutral |
| 12 | 农产品加工 | 57.2 | 中性 | 66.8 | 短线活跃 | neutral |
| 13 | 白色家电 | 57.2 | 中性 | 58.8 | 短线中性 | neutral |
| 14 | 军工电子 | 56.2 | 中性 | 58.8 | 短线中性 | neutral |
| 15 | 互联网电商 | 53.2 | 中性 | 66.8 | 短线活跃 | neutral |
| 16 | 化学制药 | 52.6 | 中性 | 75.3 | 短线活跃 | neutral |
| 17 | 白酒 | 52.2 | 中性 | 55.8 | 短线中性 | neutral |
| 18 | 环保设备 | 51.0 | 中性 | 55.8 | 短线中性 | neutral |
| 19 | 小金属 | 50.0 | 中性 | 45.8 | 短线降温 | neutral |
| 20 | 光伏设备 | 49.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 21 | 黑色家电 | 47.5 | 降温 | 37.3 | 短线降温 | weak_or_cooling |
| 22 | 化学制品 | 47.0 | 降温 | 63.8 | 短线中性 | neutral |
| 23 | 造纸 | 46.0 | 降温 | 55.8 | 短线中性 | neutral |
| 24 | 厨卫电器 | 45.2 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 25 | 化学原料 | 44.2 | 降温 | 63.8 | 短线中性 | neutral |
| 26 | 影视院线 | 44.2 | 降温 | 63.8 | 短线中性 | neutral |
| 27 | 美容护理 | 44.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 28 | 零售 | 44.2 | 降温 | 63.8 | 短线中性 | neutral |
| 29 | 军工装备 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 30 | 旅游及酒店 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 31 | 汽车服务及其他 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 32 | 服装家纺 | 43.0 | 降温 | 63.8 | 短线中性 | neutral |
| 33 | 医疗器械 | 42.4 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 34 | 中药 | 41.4 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 35 | 专用设备 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 36 | 包装印刷 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 37 | 家居用品 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 38 | 工程机械 | 40.0 | 降温 | 52.8 | 短线中性 | neutral |
| 39 | 建筑材料 | 40.0 | 降温 | 52.8 | 短线中性 | neutral |
| 40 | 橡胶制品 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 41 | 汽车整车 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 42 | 轨交设备 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 43 | 钢铁 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 44 | 风电设备 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 45 | 饮料制造 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 46 | 其他社会服务 | 39.0 | 降温 | 63.8 | 短线中性 | neutral |
| 47 | 综合 | 39.0 | 降温 | 63.8 | 短线中性 | neutral |
| 48 | 能源金属 | 37.4 | 降温 | 55.8 | 短线中性 | neutral |
| 49 | 多元金融 | 37.2 | 降温 | 58.8 | 短线中性 | neutral |
| 50 | 机场航运 | 37.2 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 51 | 自动化设备 | 37.2 | 降温 | 55.8 | 短线中性 | neutral |
| 52 | 通用设备 | 37.2 | 降温 | 55.8 | 短线中性 | neutral |
| 53 | 医药商业 | 36.2 | 降温 | 63.8 | 短线中性 | neutral |
| 54 | 小家电 | 36.2 | 降温 | 63.8 | 短线中性 | neutral |
| 55 | 煤炭开采加工 | 36.2 | 降温 | 63.8 | 短线中性 | neutral |
| 56 | 燃气 | 36.2 | 降温 | 63.8 | 短线中性 | neutral |
| 57 | 种植业与林业 | 36.2 | 降温 | 63.8 | 短线中性 | neutral |
| 58 | 文化传媒 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 59 | 环境治理 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 60 | 食品加工制造 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 61 | 公路铁路运输 | 35.0 | 降温 | 52.8 | 短线中性 | neutral |
| 62 | IT服务 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 63 | 塑料制品 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 64 | 汽车零部件 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 65 | 油气开采及服务 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 66 | 电机 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 67 | 计算机设备 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 68 | 软件开发 | 33.2 | 偏弱 | 58.8 | 短线中性 | neutral |
| 69 | 通信服务 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 70 | 金属新材料 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 71 | 建筑装饰 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 72 | 房地产 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 73 | 电力 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 74 | 纺织制造 | 33.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 75 | 贸易 | 33.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 76 | 银行 | 32.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 77 | 其他电子 | 30.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 78 | 电池 | 30.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 79 | 农化制品 | 29.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 80 | 石油加工贸易 | 29.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 81 | 工业金属 | 28.2 | 偏弱 | 52.8 | 短线中性 | neutral |
| 82 | 电网设备 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 83 | 贵金属 | 25.2 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 84 | 化学纤维 | 24.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 85 | 港口航运 | 24.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 86 | 元件 | 22.6 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 87 | 非金属材料 | 17.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 88 | 其他电源设备 | 14.4 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 89 | 消费电子 | 14.4 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 90 | 通信设备 | 11.7 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 90

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 化学制药 | 75.3 | 短线活跃 | 52.6 | 中性 | neutral |
| 2 | 保险 | 72.3 | 短线活跃 | 62.6 | 中性 | neutral |
| 3 | 养殖业 | 72.3 | 短线活跃 | 61.5 | 中性 | neutral |
| 4 | 生物制品 | 69.8 | 短线活跃 | 60.4 | 中性 | neutral |
| 5 | 教育 | 69.3 | 短线活跃 | 62.5 | 中性 | neutral |
| 6 | 证券 | 66.8 | 短线活跃 | 67.2 | 观察 | trend_and_burst_aligned |
| 7 | 物流 | 66.8 | 短线活跃 | 62.2 | 中性 | neutral |
| 8 | 医疗服务 | 66.8 | 短线活跃 | 57.4 | 中性 | neutral |
| 9 | 农产品加工 | 66.8 | 短线活跃 | 57.2 | 中性 | neutral |
| 10 | 互联网电商 | 66.8 | 短线活跃 | 53.2 | 中性 | neutral |
| 11 | 美容护理 | 66.8 | 短线活跃 | 44.2 | 降温 | burst_without_trend_confirmation |
| 12 | 医疗器械 | 66.8 | 短线活跃 | 42.4 | 降温 | burst_without_trend_confirmation |
| 13 | 中药 | 66.8 | 短线活跃 | 41.4 | 降温 | burst_without_trend_confirmation |
| 14 | 化学制品 | 63.8 | 短线中性 | 47.0 | 降温 | neutral |
| 15 | 化学原料 | 63.8 | 短线中性 | 44.2 | 降温 | neutral |
| 16 | 影视院线 | 63.8 | 短线中性 | 44.2 | 降温 | neutral |
| 17 | 零售 | 63.8 | 短线中性 | 44.2 | 降温 | neutral |
| 18 | 服装家纺 | 63.8 | 短线中性 | 43.0 | 降温 | neutral |
| 19 | 其他社会服务 | 63.8 | 短线中性 | 39.0 | 降温 | neutral |
| 20 | 综合 | 63.8 | 短线中性 | 39.0 | 降温 | neutral |
| 21 | 医药商业 | 63.8 | 短线中性 | 36.2 | 降温 | neutral |
| 22 | 小家电 | 63.8 | 短线中性 | 36.2 | 降温 | neutral |
| 23 | 煤炭开采加工 | 63.8 | 短线中性 | 36.2 | 降温 | neutral |
| 24 | 燃气 | 63.8 | 短线中性 | 36.2 | 降温 | neutral |
| 25 | 种植业与林业 | 63.8 | 短线中性 | 36.2 | 降温 | neutral |
| 26 | 电子化学品 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 27 | 白色家电 | 58.8 | 短线中性 | 57.2 | 中性 | neutral |
| 28 | 军工电子 | 58.8 | 短线中性 | 56.2 | 中性 | neutral |
| 29 | 多元金融 | 58.8 | 短线中性 | 37.2 | 降温 | neutral |
| 30 | 软件开发 | 58.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 31 | 白酒 | 55.8 | 短线中性 | 52.2 | 中性 | neutral |
| 32 | 环保设备 | 55.8 | 短线中性 | 51.0 | 中性 | neutral |
| 33 | 造纸 | 55.8 | 短线中性 | 46.0 | 降温 | neutral |
| 34 | 军工装备 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 35 | 旅游及酒店 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 36 | 汽车服务及其他 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 37 | 专用设备 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 38 | 包装印刷 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 39 | 家居用品 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 40 | 橡胶制品 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 41 | 汽车整车 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 42 | 轨交设备 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 43 | 钢铁 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 44 | 风电设备 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 45 | 饮料制造 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 46 | 能源金属 | 55.8 | 短线中性 | 37.4 | 降温 | neutral |
| 47 | 自动化设备 | 55.8 | 短线中性 | 37.2 | 降温 | neutral |
| 48 | 通用设备 | 55.8 | 短线中性 | 37.2 | 降温 | neutral |
| 49 | 文化传媒 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 50 | 环境治理 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 51 | 食品加工制造 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 52 | IT服务 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 53 | 塑料制品 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 54 | 汽车零部件 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 55 | 油气开采及服务 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 56 | 电机 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 57 | 计算机设备 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 58 | 通信服务 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 59 | 金属新材料 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 60 | 建筑装饰 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 61 | 房地产 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 62 | 电力 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 63 | 石油加工贸易 | 55.8 | 短线中性 | 29.0 | 偏弱 | neutral |
| 64 | 工程机械 | 52.8 | 短线中性 | 40.0 | 降温 | neutral |
| 65 | 建筑材料 | 52.8 | 短线中性 | 40.0 | 降温 | neutral |
| 66 | 公路铁路运输 | 52.8 | 短线中性 | 35.0 | 降温 | neutral |
| 67 | 纺织制造 | 52.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 68 | 贸易 | 52.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 69 | 农化制品 | 52.8 | 短线中性 | 29.0 | 偏弱 | neutral |
| 70 | 工业金属 | 52.8 | 短线中性 | 28.2 | 偏弱 | neutral |
| 71 | 机场航运 | 49.8 | 短线降温 | 37.2 | 降温 | weak_or_cooling |
| 72 | 化学纤维 | 49.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 73 | 港口航运 | 49.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 74 | 游戏 | 45.8 | 短线降温 | 61.0 | 中性 | neutral |
| 75 | 光学光电子 | 45.8 | 短线降温 | 60.2 | 中性 | neutral |
| 76 | 小金属 | 45.8 | 短线降温 | 50.0 | 中性 | neutral |
| 77 | 光伏设备 | 45.8 | 短线降温 | 49.0 | 降温 | weak_or_cooling |
| 78 | 厨卫电器 | 45.8 | 短线降温 | 45.2 | 降温 | weak_or_cooling |
| 79 | 电池 | 45.8 | 短线降温 | 30.2 | 偏弱 | weak_or_cooling |
| 80 | 电网设备 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 81 | 银行 | 39.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 82 | 贵金属 | 39.8 | 短线降温 | 25.2 | 偏弱 | weak_or_cooling |
| 83 | 半导体 | 37.3 | 短线降温 | 64.5 | 中性 | neutral |
| 84 | 黑色家电 | 37.3 | 短线降温 | 47.5 | 降温 | weak_or_cooling |
| 85 | 其他电子 | 34.3 | 短线偏弱 | 30.4 | 偏弱 | weak_or_cooling |
| 86 | 其他电源设备 | 31.3 | 短线偏弱 | 14.4 | 偏弱 | weak_or_cooling |
| 87 | 消费电子 | 31.3 | 短线偏弱 | 14.4 | 偏弱 | weak_or_cooling |
| 88 | 通信设备 | 31.3 | 短线偏弱 | 11.7 | 偏弱 | weak_or_cooling |
| 89 | 元件 | 28.3 | 短线偏弱 | 22.6 | 偏弱 | weak_or_cooling |
| 90 | 非金属材料 | 25.3 | 短线偏弱 | 17.2 | 偏弱 | weak_or_cooling |

## 分歧板块

### 短线强但趋势未确认

| 板块 | 短线分 | 趋势分 | 说明 |
|------|--------|--------|------|
| 美容护理 | 66.8 | 44.2 | 短线强但趋势未确认，需谨慎 |
| 医疗器械 | 66.8 | 42.4 | 短线强但趋势未确认，需谨慎 |
| 中药 | 66.8 | 41.4 | 短线强但趋势未确认，需谨慎 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 电子化学品

**趋势持续评分**:
- 趋势分: 81.0
- 趋势等级: 重点观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
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

### 2. 证券

**趋势持续评分**:
- 趋势分: 67.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 11.4
  - momentum_component: 15.0
  - relative_strength_component: 17.0
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

### 3. 半导体

**趋势持续评分**:
- 趋势分: 64.5
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 4.0

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

### 4. 保险

**趋势持续评分**:
- 趋势分: 62.6
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 13.7
  - momentum_component: 15.0
  - relative_strength_component: 17.0
  - persistence_component: 15.0
  - drawdown_component: 4.0
  - volatility_component: 1.6
  - data_quality_component: 6.4
  - risk_penalty: 10.0

**短线爆发评分**:
- 短线分: 72.3
- 短线等级: 短线活跃
- 短线 breakdown:
  - radar_today_component: 27.3
  - one_day_change_component: 20.0
  - three_day_momentum_component: 12.0
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

### 5. 教育

**趋势持续评分**:
- 趋势分: 62.5
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 13.7
  - momentum_component: 15.0
  - relative_strength_component: 10.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 6.0

**短线爆发评分**:
- 短线分: 69.3
- 短线等级: 短线活跃
- 短线 breakdown:
  - radar_today_component: 27.3
  - one_day_change_component: 20.0
  - three_day_momentum_component: 9.0
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

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
