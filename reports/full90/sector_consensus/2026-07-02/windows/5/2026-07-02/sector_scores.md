# 板块综合评分

**分析日期**: 2026-07-02
**更新时间**: 2026-07-02T22:58:42.065059

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。

## 数据来源

- **板块类型**: industry
- **历史数据范围**: 2026-05-20 ~ 2026-07-02
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
| 1 | 物流 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 2 | 服装家纺 | 74.0 | 观察 | 55.8 | 短线中性 | neutral |
| 3 | 美容护理 | 72.0 | 观察 | 55.8 | 短线中性 | neutral |
| 4 | 养殖业 | 71.2 | 观察 | 58.8 | 短线中性 | neutral |
| 5 | 农产品加工 | 68.2 | 观察 | 48.8 | 短线降温 | trend_only |
| 6 | 中药 | 67.2 | 观察 | 55.8 | 短线中性 | neutral |
| 7 | 家居用品 | 67.0 | 观察 | 55.8 | 短线中性 | neutral |
| 8 | 工程机械 | 67.0 | 观察 | 55.8 | 短线中性 | neutral |
| 9 | 造纸 | 67.0 | 观察 | 55.8 | 短线中性 | neutral |
| 10 | 饮料制造 | 66.0 | 观察 | 42.8 | 短线降温 | trend_only |
| 11 | 白色家电 | 65.2 | 观察 | 37.3 | 短线降温 | trend_only |
| 12 | 教育 | 64.5 | 中性 | 34.3 | 短线偏弱 | neutral |
| 13 | 化学制药 | 64.4 | 中性 | 58.8 | 短线中性 | neutral |
| 14 | 小家电 | 64.2 | 中性 | 45.8 | 短线降温 | neutral |
| 15 | 影视院线 | 64.2 | 中性 | 48.8 | 短线降温 | neutral |
| 16 | 化学制品 | 64.0 | 中性 | 45.8 | 短线降温 | neutral |
| 17 | 化学原料 | 64.0 | 中性 | 45.8 | 短线降温 | neutral |
| 18 | 纺织制造 | 63.0 | 中性 | 55.8 | 短线中性 | neutral |
| 19 | 电子化学品 | 62.5 | 中性 | 30.3 | 短线偏弱 | neutral |
| 20 | 贵金属 | 62.2 | 中性 | 63.8 | 短线中性 | neutral |
| 21 | 公路铁路运输 | 61.0 | 中性 | 42.8 | 短线降温 | neutral |
| 22 | 旅游及酒店 | 61.0 | 中性 | 45.8 | 短线降温 | neutral |
| 23 | 钢铁 | 61.0 | 中性 | 45.8 | 短线降温 | neutral |
| 24 | 银行 | 59.0 | 中性 | 49.8 | 短线降温 | neutral |
| 25 | 文化传媒 | 59.0 | 中性 | 45.8 | 短线降温 | neutral |
| 26 | 汽车整车 | 59.0 | 中性 | 45.8 | 短线降温 | neutral |
| 27 | 汽车零部件 | 59.0 | 中性 | 45.8 | 短线降温 | neutral |
| 28 | 燃气 | 59.0 | 中性 | 45.8 | 短线降温 | neutral |
| 29 | 食品加工制造 | 59.0 | 中性 | 45.8 | 短线降温 | neutral |
| 30 | 小金属 | 57.2 | 中性 | 31.3 | 短线偏弱 | neutral |
| 31 | 游戏 | 57.2 | 中性 | 31.3 | 短线偏弱 | neutral |
| 32 | 环保设备 | 57.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 33 | 医药商业 | 56.2 | 中性 | 45.8 | 短线降温 | neutral |
| 34 | 塑料制品 | 56.2 | 中性 | 48.8 | 短线降温 | neutral |
| 35 | 煤炭开采加工 | 56.2 | 中性 | 42.8 | 短线降温 | neutral |
| 36 | 种植业与林业 | 56.2 | 中性 | 45.8 | 短线降温 | neutral |
| 37 | 互联网电商 | 55.2 | 中性 | 37.3 | 短线降温 | neutral |
| 38 | 汽车服务及其他 | 55.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 39 | 零售 | 53.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 40 | 厨卫电器 | 52.5 | 中性 | 31.3 | 短线偏弱 | neutral |
| 41 | 轨交设备 | 52.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 42 | 电机 | 52.2 | 中性 | 48.8 | 短线降温 | neutral |
| 43 | 化学纤维 | 52.0 | 中性 | 55.8 | 短线中性 | neutral |
| 44 | 农化制品 | 52.0 | 中性 | 45.8 | 短线降温 | neutral |
| 45 | 石油加工贸易 | 52.0 | 中性 | 45.8 | 短线降温 | neutral |
| 46 | 生物制品 | 50.6 | 中性 | 34.3 | 短线偏弱 | neutral |
| 47 | 军工电子 | 50.5 | 中性 | 30.3 | 短线偏弱 | neutral |
| 48 | 黑色家电 | 50.5 | 中性 | 34.3 | 短线偏弱 | neutral |
| 49 | 专用设备 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 50 | 军工装备 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 51 | 包装印刷 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 52 | 橡胶制品 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 53 | 港口航运 | 49.0 | 降温 | 42.8 | 短线降温 | weak_or_cooling |
| 54 | 医疗器械 | 48.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 55 | 通用设备 | 48.5 | 降温 | 37.3 | 短线降温 | weak_or_cooling |
| 56 | 其他社会服务 | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 57 | 环境治理 | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 58 | 综合 | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 59 | 光学光电子 | 47.6 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 60 | 医疗服务 | 47.6 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 61 | 风电设备 | 47.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 62 | 证券 | 45.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 63 | 软件开发 | 45.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 64 | 光伏设备 | 45.2 | 降温 | 27.3 | 短线偏弱 | weak_or_cooling |
| 65 | 油气开采及服务 | 45.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 66 | 电力 | 45.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 67 | 建筑装饰 | 43.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 68 | 房地产 | 43.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 69 | 贸易 | 43.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 70 | 白酒 | 42.5 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 71 | 建筑材料 | 42.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 72 | 保险 | 38.6 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 73 | IT服务 | 38.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 74 | 电池 | 38.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 75 | 通信服务 | 38.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 76 | 金属新材料 | 38.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 77 | 自动化设备 | 37.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 78 | 计算机设备 | 37.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 79 | 半导体 | 36.6 | 降温 | 27.3 | 短线偏弱 | weak_or_cooling |
| 80 | 工业金属 | 36.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 81 | 电网设备 | 36.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 82 | 多元金融 | 35.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 83 | 能源金属 | 33.6 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 84 | 机场航运 | 25.2 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 85 | 消费电子 | 18.4 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 86 | 其他电子 | 15.7 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |
| 87 | 其他电源设备 | 14.4 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |
| 88 | 非金属材料 | 13.2 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 89 | 通信设备 | 11.7 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |
| 90 | 元件 | 6.7 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 90

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 贵金属 | 63.8 | 短线中性 | 62.2 | 中性 | neutral |
| 2 | 物流 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 3 | 养殖业 | 58.8 | 短线中性 | 71.2 | 观察 | neutral |
| 4 | 化学制药 | 58.8 | 短线中性 | 64.4 | 中性 | neutral |
| 5 | 服装家纺 | 55.8 | 短线中性 | 74.0 | 观察 | neutral |
| 6 | 美容护理 | 55.8 | 短线中性 | 72.0 | 观察 | neutral |
| 7 | 中药 | 55.8 | 短线中性 | 67.2 | 观察 | neutral |
| 8 | 家居用品 | 55.8 | 短线中性 | 67.0 | 观察 | neutral |
| 9 | 工程机械 | 55.8 | 短线中性 | 67.0 | 观察 | neutral |
| 10 | 造纸 | 55.8 | 短线中性 | 67.0 | 观察 | neutral |
| 11 | 纺织制造 | 55.8 | 短线中性 | 63.0 | 中性 | neutral |
| 12 | 化学纤维 | 55.8 | 短线中性 | 52.0 | 中性 | neutral |
| 13 | 银行 | 49.8 | 短线降温 | 59.0 | 中性 | neutral |
| 14 | 农产品加工 | 48.8 | 短线降温 | 68.2 | 观察 | trend_only |
| 15 | 影视院线 | 48.8 | 短线降温 | 64.2 | 中性 | neutral |
| 16 | 塑料制品 | 48.8 | 短线降温 | 56.2 | 中性 | neutral |
| 17 | 电机 | 48.8 | 短线降温 | 52.2 | 中性 | neutral |
| 18 | 小家电 | 45.8 | 短线降温 | 64.2 | 中性 | neutral |
| 19 | 化学制品 | 45.8 | 短线降温 | 64.0 | 中性 | neutral |
| 20 | 化学原料 | 45.8 | 短线降温 | 64.0 | 中性 | neutral |
| 21 | 旅游及酒店 | 45.8 | 短线降温 | 61.0 | 中性 | neutral |
| 22 | 钢铁 | 45.8 | 短线降温 | 61.0 | 中性 | neutral |
| 23 | 文化传媒 | 45.8 | 短线降温 | 59.0 | 中性 | neutral |
| 24 | 汽车整车 | 45.8 | 短线降温 | 59.0 | 中性 | neutral |
| 25 | 汽车零部件 | 45.8 | 短线降温 | 59.0 | 中性 | neutral |
| 26 | 燃气 | 45.8 | 短线降温 | 59.0 | 中性 | neutral |
| 27 | 食品加工制造 | 45.8 | 短线降温 | 59.0 | 中性 | neutral |
| 28 | 医药商业 | 45.8 | 短线降温 | 56.2 | 中性 | neutral |
| 29 | 种植业与林业 | 45.8 | 短线降温 | 56.2 | 中性 | neutral |
| 30 | 农化制品 | 45.8 | 短线降温 | 52.0 | 中性 | neutral |
| 31 | 石油加工贸易 | 45.8 | 短线降温 | 52.0 | 中性 | neutral |
| 32 | 饮料制造 | 42.8 | 短线降温 | 66.0 | 观察 | trend_only |
| 33 | 公路铁路运输 | 42.8 | 短线降温 | 61.0 | 中性 | neutral |
| 34 | 煤炭开采加工 | 42.8 | 短线降温 | 56.2 | 中性 | neutral |
| 35 | 港口航运 | 42.8 | 短线降温 | 49.0 | 降温 | weak_or_cooling |
| 36 | 白色家电 | 37.3 | 短线降温 | 65.2 | 观察 | trend_only |
| 37 | 互联网电商 | 37.3 | 短线降温 | 55.2 | 中性 | neutral |
| 38 | 通用设备 | 37.3 | 短线降温 | 48.5 | 降温 | weak_or_cooling |
| 39 | 教育 | 34.3 | 短线偏弱 | 64.5 | 中性 | neutral |
| 40 | 环保设备 | 34.3 | 短线偏弱 | 57.2 | 中性 | neutral |
| 41 | 汽车服务及其他 | 34.3 | 短线偏弱 | 55.2 | 中性 | neutral |
| 42 | 零售 | 34.3 | 短线偏弱 | 53.2 | 中性 | neutral |
| 43 | 轨交设备 | 34.3 | 短线偏弱 | 52.2 | 中性 | neutral |
| 44 | 生物制品 | 34.3 | 短线偏弱 | 50.6 | 中性 | neutral |
| 45 | 黑色家电 | 34.3 | 短线偏弱 | 50.5 | 中性 | neutral |
| 46 | 专用设备 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 47 | 军工装备 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 48 | 包装印刷 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 49 | 橡胶制品 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 50 | 医疗器械 | 34.3 | 短线偏弱 | 48.5 | 降温 | weak_or_cooling |
| 51 | 其他社会服务 | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 52 | 环境治理 | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 53 | 综合 | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 54 | 软件开发 | 34.3 | 短线偏弱 | 45.5 | 降温 | weak_or_cooling |
| 55 | 建筑装饰 | 34.3 | 短线偏弱 | 43.2 | 降温 | weak_or_cooling |
| 56 | 房地产 | 34.3 | 短线偏弱 | 43.2 | 降温 | weak_or_cooling |
| 57 | 贸易 | 34.3 | 短线偏弱 | 43.2 | 降温 | weak_or_cooling |
| 58 | 保险 | 34.3 | 短线偏弱 | 38.6 | 降温 | weak_or_cooling |
| 59 | IT服务 | 34.3 | 短线偏弱 | 38.5 | 降温 | weak_or_cooling |
| 60 | 电池 | 34.3 | 短线偏弱 | 38.5 | 降温 | weak_or_cooling |
| 61 | 金属新材料 | 34.3 | 短线偏弱 | 38.5 | 降温 | weak_or_cooling |
| 62 | 多元金融 | 34.3 | 短线偏弱 | 35.5 | 降温 | weak_or_cooling |
| 63 | 小金属 | 31.3 | 短线偏弱 | 57.2 | 中性 | neutral |
| 64 | 游戏 | 31.3 | 短线偏弱 | 57.2 | 中性 | neutral |
| 65 | 厨卫电器 | 31.3 | 短线偏弱 | 52.5 | 中性 | neutral |
| 66 | 医疗服务 | 31.3 | 短线偏弱 | 47.6 | 降温 | weak_or_cooling |
| 67 | 风电设备 | 31.3 | 短线偏弱 | 47.2 | 降温 | weak_or_cooling |
| 68 | 油气开采及服务 | 31.3 | 短线偏弱 | 45.2 | 降温 | weak_or_cooling |
| 69 | 电力 | 31.3 | 短线偏弱 | 45.2 | 降温 | weak_or_cooling |
| 70 | 白酒 | 31.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 71 | 建筑材料 | 31.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 72 | 工业金属 | 31.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 73 | 电网设备 | 31.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 74 | 能源金属 | 31.3 | 短线偏弱 | 33.6 | 偏弱 | weak_or_cooling |
| 75 | 电子化学品 | 30.3 | 短线偏弱 | 62.5 | 中性 | neutral |
| 76 | 军工电子 | 30.3 | 短线偏弱 | 50.5 | 中性 | neutral |
| 77 | 光学光电子 | 30.3 | 短线偏弱 | 47.6 | 降温 | weak_or_cooling |
| 78 | 证券 | 30.3 | 短线偏弱 | 45.5 | 降温 | weak_or_cooling |
| 79 | 通信服务 | 30.3 | 短线偏弱 | 38.5 | 降温 | weak_or_cooling |
| 80 | 自动化设备 | 30.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 81 | 计算机设备 | 30.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 82 | 机场航运 | 28.3 | 短线偏弱 | 25.2 | 偏弱 | weak_or_cooling |
| 83 | 非金属材料 | 28.3 | 短线偏弱 | 13.2 | 偏弱 | weak_or_cooling |
| 84 | 光伏设备 | 27.3 | 短线偏弱 | 45.2 | 降温 | weak_or_cooling |
| 85 | 半导体 | 27.3 | 短线偏弱 | 36.6 | 降温 | weak_or_cooling |
| 86 | 消费电子 | 27.3 | 短线偏弱 | 18.4 | 偏弱 | weak_or_cooling |
| 87 | 其他电子 | 24.3 | 短线偏弱 | 15.7 | 偏弱 | weak_or_cooling |
| 88 | 其他电源设备 | 24.3 | 短线偏弱 | 14.4 | 偏弱 | weak_or_cooling |
| 89 | 通信设备 | 24.3 | 短线偏弱 | 11.7 | 偏弱 | weak_or_cooling |
| 90 | 元件 | 21.3 | 短线偏弱 | 6.7 | 偏弱 | weak_or_cooling |

## 分歧板块

### 趋势强但短线不热

| 板块 | 趋势分 | 短线分 | 说明 |
|------|--------|--------|------|
| 农产品加工 | 68.2 | 48.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 饮料制造 | 66.0 | 42.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 白色家电 | 65.2 | 37.3 | 趋势强但短线不热，中长期趋势观察价值较高 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 物流

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

### 2. 服装家纺

**趋势持续评分**:
- 趋势分: 74.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
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

### 3. 美容护理

**趋势持续评分**:
- 趋势分: 72.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 3.2
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

### 4. 养殖业

**趋势持续评分**:
- 趋势分: 71.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 2.4
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

### 5. 农产品加工

**趋势持续评分**:
- 趋势分: 68.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 4.0

**短线爆发评分**:
- 短线分: 48.8
- 短线等级: 短线降温
- 短线 breakdown:
  - radar_today_component: 10.8
  - one_day_change_component: 8.0
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

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
