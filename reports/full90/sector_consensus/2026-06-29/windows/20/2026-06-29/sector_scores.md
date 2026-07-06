# 板块综合评分

**分析日期**: 2026-06-29
**更新时间**: 2026-07-05T22:02:00.878282

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
| 1 | 电子化学品 | 66.4 | 观察 | 55.8 | 短线中性 | neutral |
| 2 | 半导体 | 65.2 | 观察 | 55.8 | 短线中性 | neutral |
| 3 | 医疗服务 | 51.5 | 中性 | 64.3 | 短线中性 | neutral |
| 4 | 化学制药 | 49.5 | 降温 | 63.3 | 短线中性 | neutral |
| 5 | 光学光电子 | 49.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 6 | 证券 | 48.2 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 7 | 生物制品 | 47.5 | 降温 | 64.3 | 短线中性 | neutral |
| 8 | 小金属 | 47.4 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 9 | 其他电子 | 46.5 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 10 | 保险 | 46.2 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 11 | 游戏 | 46.0 | 降温 | 52.8 | 短线中性 | neutral |
| 12 | 军工电子 | 44.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 13 | 通用设备 | 44.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 14 | 环保设备 | 43.8 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 15 | 元件 | 43.6 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 16 | 能源金属 | 43.2 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 17 | 白色家电 | 43.0 | 降温 | 46.8 | 短线降温 | weak_or_cooling |
| 18 | 银行 | 43.0 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 19 | 化学制品 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 20 | 化学纤维 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 21 | 塑料制品 | 42.2 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 22 | 自动化设备 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 23 | 非金属材料 | 40.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 24 | 消费电子 | 39.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 25 | 橡胶制品 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 26 | 金属新材料 | 37.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 27 | 医疗器械 | 37.0 | 降温 | 52.8 | 短线中性 | neutral |
| 28 | 其他电源设备 | 36.5 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 29 | 其他社会服务 | 36.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 30 | 化学原料 | 36.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 31 | 计算机设备 | 36.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 32 | 轨交设备 | 36.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 33 | 通信设备 | 35.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 34 | 工业金属 | 33.2 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 35 | 专用设备 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 36 | 包装印刷 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 37 | 建筑材料 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 38 | 中药 | 31.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 39 | 黑色家电 | 30.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 40 | 军工装备 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 41 | 机场航运 | 28.4 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 42 | 纺织制造 | 27.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 43 | 汽车服务及其他 | 27.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 44 | 养殖业 | 26.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 45 | 光伏设备 | 25.2 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 46 | 工程机械 | 25.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 47 | 电池 | 24.4 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 48 | 港口航运 | 23.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 49 | 厨卫电器 | 22.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 50 | 公路铁路运输 | 19.8 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 51 | 农化制品 | 19.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 52 | 物流 | 19.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 53 | 造纸 | 19.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 54 | 钢铁 | 19.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 55 | 食品加工制造 | 19.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 56 | 白酒 | 18.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 57 | 饮料制造 | 18.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 58 | 贵金属 | 17.4 | 偏弱 | 46.8 | 短线降温 | weak_or_cooling |
| 59 | 互联网电商 | 17.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 60 | 家居用品 | 17.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 61 | 服装家纺 | 17.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 62 | 农产品加工 | 16.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 63 | 医药商业 | 16.0 | 偏弱 | 46.8 | 短线降温 | weak_or_cooling |
| 64 | 小家电 | 16.0 | 偏弱 | 46.8 | 短线降温 | weak_or_cooling |
| 65 | 美容护理 | 16.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 66 | IT服务 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 67 | 建筑装饰 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 68 | 汽车零部件 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 69 | 环境治理 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 70 | 石油加工贸易 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 71 | 软件开发 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 72 | 通信服务 | 15.2 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 73 | 煤炭开采加工 | 15.2 | 偏弱 | 46.8 | 短线降温 | weak_or_cooling |
| 74 | 教育 | 15.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 75 | 旅游及酒店 | 15.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 76 | 汽车整车 | 15.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 77 | 油气开采及服务 | 15.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 78 | 零售 | 15.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 79 | 多元金融 | 13.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 80 | 综合 | 13.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 81 | 种植业与林业 | 13.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 82 | 电力 | 11.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 83 | 电机 | 11.2 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 84 | 电网设备 | 11.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 85 | 房地产 | 10.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 86 | 文化传媒 | 9.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 87 | 风电设备 | 9.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 88 | 影视院线 | 8.4 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 89 | 贸易 | 6.5 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 90 | 燃气 | 4.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 90

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 医疗服务 | 64.3 | 短线中性 | 51.5 | 中性 | neutral |
| 2 | 生物制品 | 64.3 | 短线中性 | 47.5 | 降温 | neutral |
| 3 | 化学制药 | 63.3 | 短线中性 | 49.5 | 降温 | neutral |
| 4 | 电子化学品 | 55.8 | 短线中性 | 66.4 | 观察 | neutral |
| 5 | 半导体 | 55.8 | 短线中性 | 65.2 | 观察 | neutral |
| 6 | 游戏 | 52.8 | 短线中性 | 46.0 | 降温 | neutral |
| 7 | 医疗器械 | 52.8 | 短线中性 | 37.0 | 降温 | neutral |
| 8 | 中药 | 52.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 9 | 保险 | 49.8 | 短线降温 | 46.2 | 降温 | weak_or_cooling |
| 10 | 黑色家电 | 49.8 | 短线降温 | 30.0 | 偏弱 | weak_or_cooling |
| 11 | 养殖业 | 49.8 | 短线降温 | 26.0 | 偏弱 | weak_or_cooling |
| 12 | 厨卫电器 | 49.8 | 短线降温 | 22.0 | 偏弱 | weak_or_cooling |
| 13 | 白酒 | 49.8 | 短线降温 | 18.0 | 偏弱 | weak_or_cooling |
| 14 | 饮料制造 | 49.8 | 短线降温 | 18.0 | 偏弱 | weak_or_cooling |
| 15 | 农产品加工 | 49.8 | 短线降温 | 16.0 | 偏弱 | weak_or_cooling |
| 16 | 美容护理 | 49.8 | 短线降温 | 16.0 | 偏弱 | weak_or_cooling |
| 17 | 白色家电 | 46.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 18 | 贵金属 | 46.8 | 短线降温 | 17.4 | 偏弱 | weak_or_cooling |
| 19 | 医药商业 | 46.8 | 短线降温 | 16.0 | 偏弱 | weak_or_cooling |
| 20 | 小家电 | 46.8 | 短线降温 | 16.0 | 偏弱 | weak_or_cooling |
| 21 | 煤炭开采加工 | 46.8 | 短线降温 | 15.2 | 偏弱 | weak_or_cooling |
| 22 | 证券 | 39.8 | 短线降温 | 48.2 | 降温 | weak_or_cooling |
| 23 | 小金属 | 39.8 | 短线降温 | 47.4 | 降温 | weak_or_cooling |
| 24 | 环保设备 | 39.8 | 短线降温 | 43.8 | 降温 | weak_or_cooling |
| 25 | 银行 | 39.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 26 | 汽车服务及其他 | 39.8 | 短线降温 | 27.0 | 偏弱 | weak_or_cooling |
| 27 | 公路铁路运输 | 39.8 | 短线降温 | 19.8 | 偏弱 | weak_or_cooling |
| 28 | 物流 | 39.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 29 | 造纸 | 39.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 30 | 教育 | 39.8 | 短线降温 | 15.0 | 偏弱 | weak_or_cooling |
| 31 | 旅游及酒店 | 39.8 | 短线降温 | 15.0 | 偏弱 | weak_or_cooling |
| 32 | 能源金属 | 36.8 | 短线降温 | 43.2 | 降温 | weak_or_cooling |
| 33 | 工业金属 | 36.8 | 短线降温 | 33.2 | 偏弱 | weak_or_cooling |
| 34 | 钢铁 | 36.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 35 | 食品加工制造 | 36.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 36 | 家居用品 | 36.8 | 短线降温 | 17.0 | 偏弱 | weak_or_cooling |
| 37 | 服装家纺 | 36.8 | 短线降温 | 17.0 | 偏弱 | weak_or_cooling |
| 38 | 汽车整车 | 36.8 | 短线降温 | 15.0 | 偏弱 | weak_or_cooling |
| 39 | 油气开采及服务 | 36.8 | 短线降温 | 15.0 | 偏弱 | weak_or_cooling |
| 40 | 零售 | 36.8 | 短线降温 | 15.0 | 偏弱 | weak_or_cooling |
| 41 | 种植业与林业 | 36.8 | 短线降温 | 13.0 | 偏弱 | weak_or_cooling |
| 42 | 机场航运 | 31.3 | 短线偏弱 | 28.4 | 偏弱 | weak_or_cooling |
| 43 | 光学光电子 | 28.3 | 短线偏弱 | 49.2 | 降温 | weak_or_cooling |
| 44 | 军工电子 | 28.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 45 | 光伏设备 | 28.3 | 短线偏弱 | 25.2 | 偏弱 | weak_or_cooling |
| 46 | 其他电子 | 25.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 47 | 通用设备 | 25.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 48 | 化学制品 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 49 | 化学纤维 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 50 | 自动化设备 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 51 | 橡胶制品 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 52 | 其他电源设备 | 25.3 | 短线偏弱 | 36.5 | 降温 | weak_or_cooling |
| 53 | 其他社会服务 | 25.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 54 | 化学原料 | 25.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 55 | 计算机设备 | 25.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 56 | 轨交设备 | 25.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 57 | 专用设备 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 58 | 包装印刷 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 59 | 建筑材料 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 60 | 军工装备 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 61 | 纺织制造 | 25.3 | 短线偏弱 | 27.2 | 偏弱 | weak_or_cooling |
| 62 | 工程机械 | 25.3 | 短线偏弱 | 25.2 | 偏弱 | weak_or_cooling |
| 63 | 电池 | 25.3 | 短线偏弱 | 24.4 | 偏弱 | weak_or_cooling |
| 64 | 港口航运 | 25.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 65 | 农化制品 | 25.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 66 | 互联网电商 | 25.3 | 短线偏弱 | 17.2 | 偏弱 | weak_or_cooling |
| 67 | IT服务 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 68 | 建筑装饰 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 69 | 汽车零部件 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 70 | 环境治理 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 71 | 石油加工贸易 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 72 | 软件开发 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 73 | 多元金融 | 25.3 | 短线偏弱 | 13.2 | 偏弱 | weak_or_cooling |
| 74 | 综合 | 25.3 | 短线偏弱 | 13.2 | 偏弱 | weak_or_cooling |
| 75 | 电力 | 25.3 | 短线偏弱 | 11.2 | 偏弱 | weak_or_cooling |
| 76 | 电网设备 | 25.3 | 短线偏弱 | 11.2 | 偏弱 | weak_or_cooling |
| 77 | 房地产 | 25.3 | 短线偏弱 | 10.1 | 偏弱 | weak_or_cooling |
| 78 | 文化传媒 | 25.3 | 短线偏弱 | 9.2 | 偏弱 | weak_or_cooling |
| 79 | 风电设备 | 25.3 | 短线偏弱 | 9.2 | 偏弱 | weak_or_cooling |
| 80 | 影视院线 | 25.3 | 短线偏弱 | 8.4 | 偏弱 | weak_or_cooling |
| 81 | 贸易 | 25.3 | 短线偏弱 | 6.5 | 偏弱 | weak_or_cooling |
| 82 | 燃气 | 25.3 | 短线偏弱 | 4.2 | 偏弱 | weak_or_cooling |
| 83 | 元件 | 21.3 | 短线偏弱 | 43.6 | 降温 | weak_or_cooling |
| 84 | 塑料制品 | 21.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 85 | 非金属材料 | 21.3 | 短线偏弱 | 40.5 | 降温 | weak_or_cooling |
| 86 | 消费电子 | 21.3 | 短线偏弱 | 39.5 | 降温 | weak_or_cooling |
| 87 | 金属新材料 | 21.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 88 | 通信设备 | 21.3 | 短线偏弱 | 35.5 | 降温 | weak_or_cooling |
| 89 | 通信服务 | 21.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 90 | 电机 | 21.3 | 短线偏弱 | 11.2 | 偏弱 | weak_or_cooling |

## 分歧板块

当前无明显分歧板块。

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 电子化学品

**趋势持续评分**:
- 趋势分: 66.4
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 1.6
  - data_quality_component: 6.4
  - risk_penalty: 6.0

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

### 2. 半导体

**趋势持续评分**:
- 趋势分: 65.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 4.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 6.0

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
- 趋势分: 51.5
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 13.7
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 5.0
  - drawdown_component: 4.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 10.0

**短线爆发评分**:
- 短线分: 64.3
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 27.3
  - one_day_change_component: 20.0
  - three_day_momentum_component: 9.0
  - volume_or_heat_component: 5.0
  - rank_jump_component: 5.0
  - data_quality_component: 8.0
  - burst_risk_penalty: 10.0

**解读**:
- Profile: neutral
- Summary: 表现中性，可作为备选观察
- Watch points:
  - 等待更多确认信号
  - 关注后续表现

### 4. 化学制药

**趋势持续评分**:
- 趋势分: 49.5
- 趋势等级: 降温
- 趋势 breakdown:
  - radar_score_component: 13.7
  - momentum_component: 10.0
  - relative_strength_component: 17.0
  - persistence_component: 10.0
  - drawdown_component: 2.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 12.0

**短线爆发评分**:
- 短线分: 63.3
- 短线等级: 短线中性
- 短线 breakdown:
  - radar_today_component: 27.3
  - one_day_change_component: 20.0
  - three_day_momentum_component: 3.0
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

### 5. 光学光电子

**趋势持续评分**:
- 趋势分: 49.2
- 趋势等级: 降温
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 10.0
  - drawdown_component: 4.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 6.0

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
