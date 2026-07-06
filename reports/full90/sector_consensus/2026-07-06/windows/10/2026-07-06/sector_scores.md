# 板块综合评分

**分析日期**: 2026-07-06
**更新时间**: 2026-07-06T14:47:45.137139

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
| 1 | 物流 | 65.0 | 观察 | 58.8 | 短线中性 | neutral |
| 2 | 养殖业 | 63.2 | 中性 | 58.8 | 短线中性 | neutral |
| 3 | 医疗服务 | 62.2 | 中性 | 55.8 | 短线中性 | neutral |
| 4 | 白色家电 | 61.0 | 中性 | 58.8 | 短线中性 | neutral |
| 5 | 化学制药 | 60.4 | 中性 | 58.8 | 短线中性 | neutral |
| 6 | 造纸 | 58.0 | 中性 | 58.8 | 短线中性 | neutral |
| 7 | 证券 | 56.4 | 中性 | 45.8 | 短线降温 | neutral |
| 8 | 食品加工制造 | 55.0 | 中性 | 58.8 | 短线中性 | neutral |
| 9 | 环保设备 | 54.0 | 中性 | 55.8 | 短线中性 | neutral |
| 10 | 生物制品 | 53.4 | 中性 | 58.8 | 短线中性 | neutral |
| 11 | 工程机械 | 53.0 | 中性 | 66.8 | 短线活跃 | neutral |
| 12 | 服装家纺 | 53.0 | 中性 | 58.8 | 短线中性 | neutral |
| 13 | 纺织制造 | 53.0 | 中性 | 58.8 | 短线中性 | neutral |
| 14 | 汽车服务及其他 | 52.0 | 中性 | 55.8 | 短线中性 | neutral |
| 15 | 饮料制造 | 51.0 | 中性 | 55.8 | 短线中性 | neutral |
| 16 | 汽车零部件 | 50.2 | 中性 | 66.8 | 短线活跃 | neutral |
| 17 | 中药 | 50.2 | 中性 | 58.8 | 短线中性 | neutral |
| 18 | 公路铁路运输 | 50.0 | 中性 | 55.8 | 短线中性 | neutral |
| 19 | 厨卫电器 | 50.0 | 中性 | 52.8 | 短线中性 | neutral |
| 20 | 家居用品 | 50.0 | 中性 | 58.8 | 短线中性 | neutral |
| 21 | 自动化设备 | 48.2 | 降温 | 63.8 | 短线中性 | neutral |
| 22 | 医疗器械 | 48.2 | 降温 | 58.8 | 短线中性 | neutral |
| 23 | 通用设备 | 48.0 | 降温 | 55.8 | 短线中性 | neutral |
| 24 | 保险 | 47.4 | 降温 | 48.8 | 短线降温 | weak_or_cooling |
| 25 | 医药商业 | 47.2 | 降温 | 58.8 | 短线中性 | neutral |
| 26 | 农产品加工 | 47.2 | 降温 | 48.8 | 短线降温 | weak_or_cooling |
| 27 | 燃气 | 47.0 | 降温 | 58.8 | 短线中性 | neutral |
| 28 | 美容护理 | 47.0 | 降温 | 48.8 | 短线降温 | weak_or_cooling |
| 29 | 电机 | 46.5 | 降温 | 72.3 | 短线活跃 | burst_without_trend_confirmation |
| 30 | 石油加工贸易 | 46.0 | 降温 | 55.8 | 短线中性 | neutral |
| 31 | 轨交设备 | 46.0 | 降温 | 55.8 | 短线中性 | neutral |
| 32 | 游戏 | 45.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 33 | 军工电子 | 45.2 | 降温 | 55.8 | 短线中性 | neutral |
| 34 | 农化制品 | 45.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 35 | 黑色家电 | 45.0 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 36 | 橡胶制品 | 44.2 | 降温 | 40.3 | 短线降温 | weak_or_cooling |
| 37 | 专用设备 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 38 | 半导体 | 43.6 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 39 | 互联网电商 | 43.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 40 | 军工装备 | 43.2 | 降温 | 58.8 | 短线中性 | neutral |
| 41 | 风电设备 | 43.0 | 降温 | 63.8 | 短线中性 | neutral |
| 42 | 塑料制品 | 43.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 43 | 零售 | 43.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 44 | 电子化学品 | 42.6 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 45 | 旅游及酒店 | 42.0 | 降温 | 55.8 | 短线中性 | neutral |
| 46 | 环境治理 | 42.0 | 降温 | 55.8 | 短线中性 | neutral |
| 47 | 小家电 | 41.2 | 降温 | 58.8 | 短线中性 | neutral |
| 48 | 影视院线 | 41.2 | 降温 | 48.8 | 短线降温 | weak_or_cooling |
| 49 | 多元金融 | 40.2 | 降温 | 58.8 | 短线中性 | neutral |
| 50 | 汽车整车 | 40.0 | 降温 | 58.8 | 短线中性 | neutral |
| 51 | 煤炭开采加工 | 39.2 | 降温 | 58.8 | 短线中性 | neutral |
| 52 | 建筑装饰 | 39.0 | 降温 | 55.8 | 短线中性 | neutral |
| 53 | 银行 | 39.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 54 | 贵金属 | 38.6 | 降温 | 75.3 | 短线活跃 | burst_without_trend_confirmation |
| 55 | 化学制品 | 38.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 56 | 化学原料 | 38.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 57 | 教育 | 37.2 | 降温 | 58.8 | 短线中性 | neutral |
| 58 | 港口航运 | 37.0 | 降温 | 55.8 | 短线中性 | neutral |
| 59 | 计算机设备 | 37.0 | 降温 | 52.8 | 短线中性 | neutral |
| 60 | 综合 | 37.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 61 | 化学纤维 | 36.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 62 | 建筑材料 | 35.0 | 降温 | 52.8 | 短线中性 | neutral |
| 63 | 房地产 | 35.0 | 降温 | 55.8 | 短线中性 | neutral |
| 64 | 包装印刷 | 34.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 65 | 白酒 | 34.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 66 | 光学光电子 | 33.5 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 67 | 油气开采及服务 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 68 | 其他社会服务 | 32.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 69 | 电网设备 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 70 | 小金属 | 27.4 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |
| 71 | 其他电子 | 27.2 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 72 | 种植业与林业 | 27.2 | 偏弱 | 48.8 | 短线降温 | weak_or_cooling |
| 73 | 机场航运 | 25.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 74 | 文化传媒 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 75 | 钢铁 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 76 | 工业金属 | 24.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 77 | 金属新材料 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 78 | 消费电子 | 23.2 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 79 | 其他电源设备 | 23.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 80 | 电力 | 23.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 81 | 贸易 | 23.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 82 | 元件 | 22.4 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 83 | IT服务 | 21.2 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 84 | 电池 | 21.2 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 85 | 软件开发 | 21.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 86 | 通信服务 | 21.2 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 87 | 能源金属 | 20.6 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 88 | 光伏设备 | 19.2 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 89 | 通信设备 | 16.2 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 90 | 非金属材料 | 7.7 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 90

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 贵金属 | 75.3 | 短线活跃 | 38.6 | 降温 | burst_without_trend_confirmation |
| 2 | 电机 | 72.3 | 短线活跃 | 46.5 | 降温 | burst_without_trend_confirmation |
| 3 | 工程机械 | 66.8 | 短线活跃 | 53.0 | 中性 | neutral |
| 4 | 汽车零部件 | 66.8 | 短线活跃 | 50.2 | 中性 | neutral |
| 5 | 自动化设备 | 63.8 | 短线中性 | 48.2 | 降温 | neutral |
| 6 | 风电设备 | 63.8 | 短线中性 | 43.0 | 降温 | neutral |
| 7 | 物流 | 58.8 | 短线中性 | 65.0 | 观察 | neutral |
| 8 | 养殖业 | 58.8 | 短线中性 | 63.2 | 中性 | neutral |
| 9 | 白色家电 | 58.8 | 短线中性 | 61.0 | 中性 | neutral |
| 10 | 化学制药 | 58.8 | 短线中性 | 60.4 | 中性 | neutral |
| 11 | 造纸 | 58.8 | 短线中性 | 58.0 | 中性 | neutral |
| 12 | 食品加工制造 | 58.8 | 短线中性 | 55.0 | 中性 | neutral |
| 13 | 生物制品 | 58.8 | 短线中性 | 53.4 | 中性 | neutral |
| 14 | 服装家纺 | 58.8 | 短线中性 | 53.0 | 中性 | neutral |
| 15 | 纺织制造 | 58.8 | 短线中性 | 53.0 | 中性 | neutral |
| 16 | 中药 | 58.8 | 短线中性 | 50.2 | 中性 | neutral |
| 17 | 家居用品 | 58.8 | 短线中性 | 50.0 | 中性 | neutral |
| 18 | 医疗器械 | 58.8 | 短线中性 | 48.2 | 降温 | neutral |
| 19 | 医药商业 | 58.8 | 短线中性 | 47.2 | 降温 | neutral |
| 20 | 燃气 | 58.8 | 短线中性 | 47.0 | 降温 | neutral |
| 21 | 军工装备 | 58.8 | 短线中性 | 43.2 | 降温 | neutral |
| 22 | 小家电 | 58.8 | 短线中性 | 41.2 | 降温 | neutral |
| 23 | 多元金融 | 58.8 | 短线中性 | 40.2 | 降温 | neutral |
| 24 | 汽车整车 | 58.8 | 短线中性 | 40.0 | 降温 | neutral |
| 25 | 煤炭开采加工 | 58.8 | 短线中性 | 39.2 | 降温 | neutral |
| 26 | 教育 | 58.8 | 短线中性 | 37.2 | 降温 | neutral |
| 27 | 医疗服务 | 55.8 | 短线中性 | 62.2 | 中性 | neutral |
| 28 | 环保设备 | 55.8 | 短线中性 | 54.0 | 中性 | neutral |
| 29 | 汽车服务及其他 | 55.8 | 短线中性 | 52.0 | 中性 | neutral |
| 30 | 饮料制造 | 55.8 | 短线中性 | 51.0 | 中性 | neutral |
| 31 | 公路铁路运输 | 55.8 | 短线中性 | 50.0 | 中性 | neutral |
| 32 | 通用设备 | 55.8 | 短线中性 | 48.0 | 降温 | neutral |
| 33 | 石油加工贸易 | 55.8 | 短线中性 | 46.0 | 降温 | neutral |
| 34 | 轨交设备 | 55.8 | 短线中性 | 46.0 | 降温 | neutral |
| 35 | 军工电子 | 55.8 | 短线中性 | 45.2 | 降温 | neutral |
| 36 | 专用设备 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 37 | 旅游及酒店 | 55.8 | 短线中性 | 42.0 | 降温 | neutral |
| 38 | 环境治理 | 55.8 | 短线中性 | 42.0 | 降温 | neutral |
| 39 | 建筑装饰 | 55.8 | 短线中性 | 39.0 | 降温 | neutral |
| 40 | 港口航运 | 55.8 | 短线中性 | 37.0 | 降温 | neutral |
| 41 | 房地产 | 55.8 | 短线中性 | 35.0 | 降温 | neutral |
| 42 | 油气开采及服务 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 43 | 电网设备 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 44 | 工业金属 | 55.8 | 短线中性 | 24.2 | 偏弱 | neutral |
| 45 | 厨卫电器 | 52.8 | 短线中性 | 50.0 | 中性 | neutral |
| 46 | 计算机设备 | 52.8 | 短线中性 | 37.0 | 降温 | neutral |
| 47 | 建筑材料 | 52.8 | 短线中性 | 35.0 | 降温 | neutral |
| 48 | 消费电子 | 49.8 | 短线降温 | 23.2 | 偏弱 | weak_or_cooling |
| 49 | 保险 | 48.8 | 短线降温 | 47.4 | 降温 | weak_or_cooling |
| 50 | 农产品加工 | 48.8 | 短线降温 | 47.2 | 降温 | weak_or_cooling |
| 51 | 美容护理 | 48.8 | 短线降温 | 47.0 | 降温 | weak_or_cooling |
| 52 | 影视院线 | 48.8 | 短线降温 | 41.2 | 降温 | weak_or_cooling |
| 53 | 种植业与林业 | 48.8 | 短线降温 | 27.2 | 偏弱 | weak_or_cooling |
| 54 | 证券 | 45.8 | 短线降温 | 56.4 | 中性 | neutral |
| 55 | 农化制品 | 45.8 | 短线降温 | 45.0 | 降温 | weak_or_cooling |
| 56 | 塑料制品 | 45.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 57 | 零售 | 45.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 58 | 银行 | 45.8 | 短线降温 | 39.0 | 降温 | weak_or_cooling |
| 59 | 综合 | 45.8 | 短线降温 | 37.0 | 降温 | weak_or_cooling |
| 60 | 包装印刷 | 45.8 | 短线降温 | 34.0 | 偏弱 | weak_or_cooling |
| 61 | 白酒 | 45.8 | 短线降温 | 34.0 | 偏弱 | weak_or_cooling |
| 62 | 其他社会服务 | 45.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 63 | 金属新材料 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 64 | 贸易 | 45.8 | 短线降温 | 23.0 | 偏弱 | weak_or_cooling |
| 65 | 软件开发 | 45.8 | 短线降温 | 21.2 | 偏弱 | weak_or_cooling |
| 66 | 电力 | 42.8 | 短线降温 | 23.0 | 偏弱 | weak_or_cooling |
| 67 | IT服务 | 42.8 | 短线降温 | 21.2 | 偏弱 | weak_or_cooling |
| 68 | 电池 | 42.8 | 短线降温 | 21.2 | 偏弱 | weak_or_cooling |
| 69 | 通信服务 | 42.8 | 短线降温 | 21.2 | 偏弱 | weak_or_cooling |
| 70 | 橡胶制品 | 40.3 | 短线降温 | 44.2 | 降温 | weak_or_cooling |
| 71 | 黑色家电 | 39.8 | 短线降温 | 45.0 | 降温 | weak_or_cooling |
| 72 | 其他电子 | 36.8 | 短线降温 | 27.2 | 偏弱 | weak_or_cooling |
| 73 | 其他电源设备 | 36.8 | 短线降温 | 23.0 | 偏弱 | weak_or_cooling |
| 74 | 元件 | 36.8 | 短线降温 | 22.4 | 偏弱 | weak_or_cooling |
| 75 | 通信设备 | 36.8 | 短线降温 | 16.2 | 偏弱 | weak_or_cooling |
| 76 | 互联网电商 | 34.3 | 短线偏弱 | 43.2 | 降温 | weak_or_cooling |
| 77 | 化学制品 | 34.3 | 短线偏弱 | 38.2 | 降温 | weak_or_cooling |
| 78 | 化学原料 | 34.3 | 短线偏弱 | 38.2 | 降温 | weak_or_cooling |
| 79 | 化学纤维 | 34.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 80 | 机场航运 | 34.3 | 短线偏弱 | 25.2 | 偏弱 | weak_or_cooling |
| 81 | 文化传媒 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 82 | 钢铁 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 83 | 游戏 | 28.3 | 短线偏弱 | 45.2 | 降温 | weak_or_cooling |
| 84 | 能源金属 | 28.3 | 短线偏弱 | 20.6 | 偏弱 | weak_or_cooling |
| 85 | 光伏设备 | 28.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 86 | 光学光电子 | 25.3 | 短线偏弱 | 33.5 | 偏弱 | weak_or_cooling |
| 87 | 非金属材料 | 25.3 | 短线偏弱 | 7.7 | 偏弱 | weak_or_cooling |
| 88 | 小金属 | 24.3 | 短线偏弱 | 27.4 | 偏弱 | weak_or_cooling |
| 89 | 半导体 | 21.3 | 短线偏弱 | 43.6 | 降温 | weak_or_cooling |
| 90 | 电子化学品 | 21.3 | 短线偏弱 | 42.6 | 降温 | weak_or_cooling |

## 分歧板块

### 短线强但趋势未确认

| 板块 | 短线分 | 趋势分 | 说明 |
|------|--------|--------|------|
| 电机 | 72.3 | 46.5 | 短线强但趋势未确认，需谨慎 |
| 贵金属 | 75.3 | 38.6 | 短线强但趋势未确认，需谨慎 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 物流

**趋势持续评分**:
- 趋势分: 65.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
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

### 2. 养殖业

**趋势持续评分**:
- 趋势分: 63.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 4.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 8.0

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

### 3. 医疗服务

**趋势持续评分**:
- 趋势分: 62.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
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

### 4. 白色家电

**趋势持续评分**:
- 趋势分: 61.0
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
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

### 5. 化学制药

**趋势持续评分**:
- 趋势分: 60.4
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 4.0
  - volatility_component: 1.6
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

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
