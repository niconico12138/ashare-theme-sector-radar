# 板块综合评分

**分析日期**: 2026-06-29
**更新时间**: 2026-07-05T22:02:00.851629

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。

## 数据来源

- **板块类型**: industry
- **历史数据范围**: 2026-06-01 ~ 2026-06-29
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

## 趋势持续 Top 90

| 排名 | 板块 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 半导体 | 81.0 | 重点观察 | 55.8 | 短线中性 | neutral |
| 2 | 电子化学品 | 76.2 | 观察 | 55.8 | 短线中性 | neutral |
| 3 | 医疗服务 | 67.5 | 观察 | 69.3 | 短线活跃 | trend_and_burst_aligned |
| 4 | 游戏 | 60.0 | 中性 | 52.8 | 短线中性 | neutral |
| 5 | 证券 | 59.2 | 中性 | 39.8 | 短线降温 | neutral |
| 6 | 化学制药 | 58.5 | 中性 | 63.3 | 短线中性 | neutral |
| 7 | 医疗器械 | 52.0 | 中性 | 57.8 | 短线中性 | neutral |
| 8 | 环保设备 | 52.0 | 中性 | 39.8 | 短线降温 | neutral |
| 9 | 生物制品 | 51.5 | 中性 | 64.3 | 短线中性 | neutral |
| 10 | 白色家电 | 51.0 | 中性 | 46.8 | 短线降温 | neutral |
| 11 | 计算机设备 | 49.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 12 | 黑色家电 | 49.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 13 | 其他电子 | 48.5 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 14 | 小金属 | 47.4 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 15 | 中药 | 47.0 | 降温 | 52.8 | 短线中性 | neutral |
| 16 | 养殖业 | 46.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 17 | 白酒 | 46.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 18 | 光学光电子 | 45.5 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 19 | 军工电子 | 44.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 20 | 轨交设备 | 44.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 21 | 元件 | 43.6 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 22 | 保险 | 43.4 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 23 | 专用设备 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 24 | 其他社会服务 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 25 | 包装印刷 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 26 | 化学制品 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 27 | 化学纤维 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 28 | 塑料制品 | 42.2 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 29 | 建筑材料 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 30 | 橡胶制品 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 31 | 港口航运 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 32 | 纺织制造 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 33 | 通用设备 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 34 | 零售 | 42.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 35 | 汽车服务及其他 | 41.8 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 36 | 消费电子 | 41.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 37 | 自动化设备 | 41.5 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 38 | 医药商业 | 41.0 | 降温 | 46.8 | 短线降温 | weak_or_cooling |
| 39 | 钢铁 | 40.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 40 | 其他电源设备 | 39.5 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 41 | 互联网电商 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 42 | 环境治理 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 43 | 物流 | 38.8 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 44 | 美容护理 | 38.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 45 | 饮料制造 | 38.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 46 | 服装家纺 | 38.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 47 | 通信设备 | 37.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 48 | 能源金属 | 37.4 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 49 | 光伏设备 | 37.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 50 | 公路铁路运输 | 36.8 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 51 | 厨卫电器 | 36.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 52 | 教育 | 36.0 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 53 | 金属新材料 | 35.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 54 | IT服务 | 35.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 55 | 建筑装饰 | 35.0 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 56 | 造纸 | 35.0 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 57 | 银行 | 35.0 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 58 | 食品加工制造 | 35.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 59 | 非金属材料 | 34.6 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 60 | 化学原料 | 34.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 61 | 电网设备 | 34.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 62 | 家居用品 | 33.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 63 | 多元金融 | 32.5 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 64 | 机场航运 | 32.5 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 65 | 通信服务 | 32.5 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 66 | 农产品加工 | 32.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 67 | 贵金属 | 31.4 | 偏弱 | 46.8 | 短线降温 | weak_or_cooling |
| 68 | 石油加工贸易 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 69 | 风电设备 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 70 | 工业金属 | 31.2 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 71 | 电池 | 30.4 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 72 | 农化制品 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 73 | 工程机械 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 74 | 文化传媒 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 75 | 综合 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 76 | 小家电 | 28.0 | 偏弱 | 46.8 | 短线降温 | weak_or_cooling |
| 77 | 汽车零部件 | 27.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 78 | 电机 | 27.2 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 79 | 软件开发 | 27.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 80 | 贸易 | 25.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 81 | 军工装备 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 82 | 旅游及酒店 | 23.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 83 | 油气开采及服务 | 23.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 84 | 房地产 | 21.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 85 | 汽车整车 | 21.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 86 | 种植业与林业 | 21.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 87 | 影视院线 | 19.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 88 | 电力 | 19.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 89 | 燃气 | 17.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 90 | 煤炭开采加工 | 16.0 | 偏弱 | 46.8 | 短线降温 | weak_or_cooling |

## 短线爆发 Top 90

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 医疗服务 | 69.3 | 短线活跃 | 67.5 | 观察 | trend_and_burst_aligned |
| 2 | 生物制品 | 64.3 | 短线中性 | 51.5 | 中性 | neutral |
| 3 | 化学制药 | 63.3 | 短线中性 | 58.5 | 中性 | neutral |
| 4 | 医疗器械 | 57.8 | 短线中性 | 52.0 | 中性 | neutral |
| 5 | 半导体 | 55.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 6 | 电子化学品 | 55.8 | 短线中性 | 76.2 | 观察 | neutral |
| 7 | 游戏 | 52.8 | 短线中性 | 60.0 | 中性 | neutral |
| 8 | 中药 | 52.8 | 短线中性 | 47.0 | 降温 | neutral |
| 9 | 黑色家电 | 49.8 | 短线降温 | 49.0 | 降温 | weak_or_cooling |
| 10 | 养殖业 | 49.8 | 短线降温 | 46.0 | 降温 | weak_or_cooling |
| 11 | 白酒 | 49.8 | 短线降温 | 46.0 | 降温 | weak_or_cooling |
| 12 | 保险 | 49.8 | 短线降温 | 43.4 | 降温 | weak_or_cooling |
| 13 | 美容护理 | 49.8 | 短线降温 | 38.0 | 降温 | weak_or_cooling |
| 14 | 饮料制造 | 49.8 | 短线降温 | 38.0 | 降温 | weak_or_cooling |
| 15 | 厨卫电器 | 49.8 | 短线降温 | 36.0 | 降温 | weak_or_cooling |
| 16 | 农产品加工 | 49.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 17 | 白色家电 | 46.8 | 短线降温 | 51.0 | 中性 | neutral |
| 18 | 医药商业 | 46.8 | 短线降温 | 41.0 | 降温 | weak_or_cooling |
| 19 | 贵金属 | 46.8 | 短线降温 | 31.4 | 偏弱 | weak_or_cooling |
| 20 | 小家电 | 46.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 21 | 煤炭开采加工 | 46.8 | 短线降温 | 16.0 | 偏弱 | weak_or_cooling |
| 22 | 证券 | 39.8 | 短线降温 | 59.2 | 中性 | neutral |
| 23 | 环保设备 | 39.8 | 短线降温 | 52.0 | 中性 | neutral |
| 24 | 小金属 | 39.8 | 短线降温 | 47.4 | 降温 | weak_or_cooling |
| 25 | 汽车服务及其他 | 39.8 | 短线降温 | 41.8 | 降温 | weak_or_cooling |
| 26 | 物流 | 39.8 | 短线降温 | 38.8 | 降温 | weak_or_cooling |
| 27 | 公路铁路运输 | 39.8 | 短线降温 | 36.8 | 降温 | weak_or_cooling |
| 28 | 教育 | 39.8 | 短线降温 | 36.0 | 降温 | weak_or_cooling |
| 29 | 造纸 | 39.8 | 短线降温 | 35.0 | 降温 | weak_or_cooling |
| 30 | 银行 | 39.8 | 短线降温 | 35.0 | 降温 | weak_or_cooling |
| 31 | 旅游及酒店 | 39.8 | 短线降温 | 23.0 | 偏弱 | weak_or_cooling |
| 32 | 零售 | 36.8 | 短线降温 | 42.0 | 降温 | weak_or_cooling |
| 33 | 钢铁 | 36.8 | 短线降温 | 40.0 | 降温 | weak_or_cooling |
| 34 | 服装家纺 | 36.8 | 短线降温 | 38.0 | 降温 | weak_or_cooling |
| 35 | 能源金属 | 36.8 | 短线降温 | 37.4 | 降温 | weak_or_cooling |
| 36 | 食品加工制造 | 36.8 | 短线降温 | 35.0 | 降温 | weak_or_cooling |
| 37 | 家居用品 | 36.8 | 短线降温 | 33.0 | 偏弱 | weak_or_cooling |
| 38 | 工业金属 | 36.8 | 短线降温 | 31.2 | 偏弱 | weak_or_cooling |
| 39 | 油气开采及服务 | 36.8 | 短线降温 | 23.0 | 偏弱 | weak_or_cooling |
| 40 | 汽车整车 | 36.8 | 短线降温 | 21.0 | 偏弱 | weak_or_cooling |
| 41 | 种植业与林业 | 36.8 | 短线降温 | 21.0 | 偏弱 | weak_or_cooling |
| 42 | 机场航运 | 31.3 | 短线偏弱 | 32.5 | 偏弱 | weak_or_cooling |
| 43 | 光学光电子 | 28.3 | 短线偏弱 | 45.5 | 降温 | weak_or_cooling |
| 44 | 军工电子 | 28.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 45 | 光伏设备 | 28.3 | 短线偏弱 | 37.2 | 降温 | weak_or_cooling |
| 46 | 计算机设备 | 25.3 | 短线偏弱 | 49.2 | 降温 | weak_or_cooling |
| 47 | 其他电子 | 25.3 | 短线偏弱 | 48.5 | 降温 | weak_or_cooling |
| 48 | 轨交设备 | 25.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 49 | 专用设备 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 50 | 其他社会服务 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 51 | 包装印刷 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 52 | 化学制品 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 53 | 化学纤维 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 54 | 建筑材料 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 55 | 橡胶制品 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 56 | 港口航运 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 57 | 纺织制造 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 58 | 通用设备 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 59 | 自动化设备 | 25.3 | 短线偏弱 | 41.5 | 降温 | weak_or_cooling |
| 60 | 其他电源设备 | 25.3 | 短线偏弱 | 39.5 | 降温 | weak_or_cooling |
| 61 | 互联网电商 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 62 | 环境治理 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 63 | IT服务 | 25.3 | 短线偏弱 | 35.2 | 降温 | weak_or_cooling |
| 64 | 建筑装饰 | 25.3 | 短线偏弱 | 35.0 | 降温 | weak_or_cooling |
| 65 | 化学原料 | 25.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |
| 66 | 电网设备 | 25.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |
| 67 | 多元金融 | 25.3 | 短线偏弱 | 32.5 | 偏弱 | weak_or_cooling |
| 68 | 石油加工贸易 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 69 | 风电设备 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 70 | 电池 | 25.3 | 短线偏弱 | 30.4 | 偏弱 | weak_or_cooling |
| 71 | 农化制品 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 72 | 工程机械 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 73 | 文化传媒 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 74 | 综合 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 75 | 汽车零部件 | 25.3 | 短线偏弱 | 27.2 | 偏弱 | weak_or_cooling |
| 76 | 软件开发 | 25.3 | 短线偏弱 | 27.2 | 偏弱 | weak_or_cooling |
| 77 | 贸易 | 25.3 | 短线偏弱 | 25.2 | 偏弱 | weak_or_cooling |
| 78 | 军工装备 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 79 | 房地产 | 25.3 | 短线偏弱 | 21.2 | 偏弱 | weak_or_cooling |
| 80 | 影视院线 | 25.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 81 | 电力 | 25.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 82 | 燃气 | 25.3 | 短线偏弱 | 17.2 | 偏弱 | weak_or_cooling |
| 83 | 元件 | 21.3 | 短线偏弱 | 43.6 | 降温 | weak_or_cooling |
| 84 | 塑料制品 | 21.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 85 | 消费电子 | 21.3 | 短线偏弱 | 41.5 | 降温 | weak_or_cooling |
| 86 | 通信设备 | 21.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 87 | 金属新材料 | 21.3 | 短线偏弱 | 35.5 | 降温 | weak_or_cooling |
| 88 | 非金属材料 | 21.3 | 短线偏弱 | 34.6 | 偏弱 | weak_or_cooling |
| 89 | 通信服务 | 21.3 | 短线偏弱 | 32.5 | 偏弱 | weak_or_cooling |
| 90 | 电机 | 21.3 | 短线偏弱 | 27.2 | 偏弱 | weak_or_cooling |

## 分歧板块

当前无明显分歧板块。

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 半导体

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
- 短线分: 55.8
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 16.8
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

### 2. 电子化学品

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
- 短线分: 55.8
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 16.8
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

### 3. 医疗服务

**趋势持续评分**:
- 趋势分: 67.5
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 13.7
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 10.0
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
- Profile: trend_and_burst_aligned
- Summary: 趋势和短线都强，双重确认
- Watch points:
  - 趋势和短线双重确认，可重点关注
  - 观察是否能持续保持双强态势

### 4. 游戏

**趋势持续评分**:
- 趋势分: 60.0
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 10.0
  - drawdown_component: 6.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 4.0

**短线爆发评分**:
- 短线分: 52.8
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 16.8
  - one_day_change_component: 12.0
  - three_day_momentum_component: 6.0
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

### 5. 证券

**趋势持续评分**:
- 趋势分: 59.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 6.0

**短线爆发评分**:
- 短线分: 39.8
- 短线等级: 短线降温
- 短线 breakdown:
  - radar_today_component: 10.8
  - one_day_change_component: 8.0
  - three_day_momentum_component: 3.0
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
