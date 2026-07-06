# 板块综合评分

**分析日期**: 2026-07-02
**更新时间**: 2026-07-02T22:58:42.094786

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
| 1 | 电子化学品 | 62.5 | 中性 | 30.3 | 短线偏弱 | neutral |
| 2 | 化学制药 | 60.4 | 中性 | 58.8 | 短线中性 | neutral |
| 3 | 游戏 | 58.2 | 中性 | 31.3 | 短线偏弱 | neutral |
| 4 | 物流 | 57.0 | 中性 | 58.8 | 短线中性 | neutral |
| 5 | 医疗服务 | 55.5 | 中性 | 31.3 | 短线偏弱 | neutral |
| 6 | 纺织制造 | 53.0 | 中性 | 55.8 | 短线中性 | neutral |
| 7 | 半导体 | 50.6 | 中性 | 27.3 | 短线偏弱 | neutral |
| 8 | 养殖业 | 50.2 | 中性 | 58.8 | 短线中性 | neutral |
| 9 | 化学制品 | 50.0 | 中性 | 45.8 | 短线降温 | neutral |
| 10 | 中药 | 48.2 | 降温 | 55.8 | 短线中性 | neutral |
| 11 | 美容护理 | 48.0 | 降温 | 55.8 | 短线中性 | neutral |
| 12 | 证券 | 47.6 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 13 | 环保设备 | 47.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 14 | 化学原料 | 47.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 15 | 生物制品 | 46.6 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 16 | 服装家纺 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 17 | 小金属 | 43.5 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 18 | 互联网电商 | 43.2 | 降温 | 37.3 | 短线降温 | weak_or_cooling |
| 19 | 白色家电 | 43.2 | 降温 | 37.3 | 短线降温 | weak_or_cooling |
| 20 | 光学光电子 | 42.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 21 | 农产品加工 | 42.2 | 降温 | 48.8 | 短线降温 | weak_or_cooling |
| 22 | 造纸 | 42.0 | 降温 | 55.8 | 短线中性 | neutral |
| 23 | 橡胶制品 | 41.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 24 | 通用设备 | 41.2 | 降温 | 37.3 | 短线降温 | weak_or_cooling |
| 25 | 家居用品 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 26 | 医疗器械 | 38.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 27 | 医药商业 | 38.2 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 28 | 汽车服务及其他 | 36.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 29 | 黑色家电 | 36.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 30 | 影视院线 | 36.2 | 降温 | 48.8 | 短线降温 | weak_or_cooling |
| 31 | 保险 | 35.6 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 32 | 化学纤维 | 35.0 | 降温 | 55.8 | 短线中性 | neutral |
| 33 | 工程机械 | 35.0 | 降温 | 55.8 | 短线中性 | neutral |
| 34 | 军工电子 | 34.5 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 35 | 钢铁 | 34.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 36 | 食品加工制造 | 34.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 37 | 银行 | 33.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 38 | 公路铁路运输 | 32.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 39 | 塑料制品 | 32.0 | 偏弱 | 48.8 | 短线降温 | weak_or_cooling |
| 40 | 文化传媒 | 32.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 41 | 旅游及酒店 | 32.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 42 | 石油加工贸易 | 32.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 43 | 农化制品 | 31.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 44 | 计算机设备 | 30.2 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 45 | 燃气 | 30.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 46 | 饮料制造 | 30.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 47 | 专用设备 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 48 | 包装印刷 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 49 | 厨卫电器 | 28.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 50 | 环境治理 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 51 | 白酒 | 28.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 52 | 轨交设备 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 53 | 零售 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 54 | 汽车零部件 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 55 | 港口航运 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 56 | 种植业与林业 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 57 | 其他电子 | 27.4 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |
| 58 | 小家电 | 27.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 59 | 自动化设备 | 25.4 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 60 | 油气开采及服务 | 24.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 61 | 综合 | 23.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 62 | 汽车整车 | 23.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 63 | 贵金属 | 22.4 | 偏弱 | 63.8 | 短线中性 | neutral |
| 64 | 非金属材料 | 21.6 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 65 | 金属新材料 | 21.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 66 | 军工装备 | 21.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 67 | 煤炭开采加工 | 21.2 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 68 | 电机 | 21.2 | 偏弱 | 48.8 | 短线降温 | weak_or_cooling |
| 69 | 能源金属 | 20.6 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 70 | 光伏设备 | 19.2 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 71 | 其他电源设备 | 19.2 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |
| 72 | 其他社会服务 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 73 | 建筑材料 | 19.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 74 | 电网设备 | 19.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 75 | 风电设备 | 19.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 76 | 元件 | 18.6 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 77 | 多元金融 | 18.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 78 | IT服务 | 17.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 79 | 教育 | 17.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 80 | 通信服务 | 17.4 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 81 | 建筑装饰 | 17.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 82 | 房地产 | 17.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 83 | 贸易 | 17.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 84 | 消费电子 | 16.4 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 85 | 机场航运 | 14.4 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 86 | 电力 | 13.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 87 | 工业金属 | 12.4 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 88 | 电池 | 12.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 89 | 软件开发 | 12.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 90 | 通信设备 | 12.4 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 90

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 贵金属 | 63.8 | 短线中性 | 22.4 | 偏弱 | neutral |
| 2 | 化学制药 | 58.8 | 短线中性 | 60.4 | 中性 | neutral |
| 3 | 物流 | 58.8 | 短线中性 | 57.0 | 中性 | neutral |
| 4 | 养殖业 | 58.8 | 短线中性 | 50.2 | 中性 | neutral |
| 5 | 纺织制造 | 55.8 | 短线中性 | 53.0 | 中性 | neutral |
| 6 | 中药 | 55.8 | 短线中性 | 48.2 | 降温 | neutral |
| 7 | 美容护理 | 55.8 | 短线中性 | 48.0 | 降温 | neutral |
| 8 | 服装家纺 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 9 | 造纸 | 55.8 | 短线中性 | 42.0 | 降温 | neutral |
| 10 | 家居用品 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 11 | 化学纤维 | 55.8 | 短线中性 | 35.0 | 降温 | neutral |
| 12 | 工程机械 | 55.8 | 短线中性 | 35.0 | 降温 | neutral |
| 13 | 银行 | 49.8 | 短线降温 | 33.0 | 偏弱 | weak_or_cooling |
| 14 | 农产品加工 | 48.8 | 短线降温 | 42.2 | 降温 | weak_or_cooling |
| 15 | 影视院线 | 48.8 | 短线降温 | 36.2 | 降温 | weak_or_cooling |
| 16 | 塑料制品 | 48.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 17 | 电机 | 48.8 | 短线降温 | 21.2 | 偏弱 | weak_or_cooling |
| 18 | 化学制品 | 45.8 | 短线降温 | 50.0 | 中性 | neutral |
| 19 | 化学原料 | 45.8 | 短线降温 | 47.0 | 降温 | weak_or_cooling |
| 20 | 医药商业 | 45.8 | 短线降温 | 38.2 | 降温 | weak_or_cooling |
| 21 | 钢铁 | 45.8 | 短线降温 | 34.0 | 偏弱 | weak_or_cooling |
| 22 | 食品加工制造 | 45.8 | 短线降温 | 34.0 | 偏弱 | weak_or_cooling |
| 23 | 文化传媒 | 45.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 24 | 旅游及酒店 | 45.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 25 | 石油加工贸易 | 45.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 26 | 农化制品 | 45.8 | 短线降温 | 31.0 | 偏弱 | weak_or_cooling |
| 27 | 燃气 | 45.8 | 短线降温 | 30.0 | 偏弱 | weak_or_cooling |
| 28 | 汽车零部件 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 29 | 种植业与林业 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 30 | 小家电 | 45.8 | 短线降温 | 27.0 | 偏弱 | weak_or_cooling |
| 31 | 汽车整车 | 45.8 | 短线降温 | 23.0 | 偏弱 | weak_or_cooling |
| 32 | 公路铁路运输 | 42.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 33 | 饮料制造 | 42.8 | 短线降温 | 30.0 | 偏弱 | weak_or_cooling |
| 34 | 港口航运 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 35 | 煤炭开采加工 | 42.8 | 短线降温 | 21.2 | 偏弱 | weak_or_cooling |
| 36 | 互联网电商 | 37.3 | 短线降温 | 43.2 | 降温 | weak_or_cooling |
| 37 | 白色家电 | 37.3 | 短线降温 | 43.2 | 降温 | weak_or_cooling |
| 38 | 通用设备 | 37.3 | 短线降温 | 41.2 | 降温 | weak_or_cooling |
| 39 | 环保设备 | 34.3 | 短线偏弱 | 47.2 | 降温 | weak_or_cooling |
| 40 | 生物制品 | 34.3 | 短线偏弱 | 46.6 | 降温 | weak_or_cooling |
| 41 | 橡胶制品 | 34.3 | 短线偏弱 | 41.2 | 降温 | weak_or_cooling |
| 42 | 医疗器械 | 34.3 | 短线偏弱 | 38.5 | 降温 | weak_or_cooling |
| 43 | 汽车服务及其他 | 34.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 44 | 黑色家电 | 34.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 45 | 保险 | 34.3 | 短线偏弱 | 35.6 | 降温 | weak_or_cooling |
| 46 | 专用设备 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 47 | 包装印刷 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 48 | 环境治理 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 49 | 轨交设备 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 50 | 零售 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 51 | 综合 | 34.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 52 | 金属新材料 | 34.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 53 | 军工装备 | 34.3 | 短线偏弱 | 21.2 | 偏弱 | weak_or_cooling |
| 54 | 其他社会服务 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 55 | 多元金融 | 34.3 | 短线偏弱 | 18.4 | 偏弱 | weak_or_cooling |
| 56 | IT服务 | 34.3 | 短线偏弱 | 17.4 | 偏弱 | weak_or_cooling |
| 57 | 教育 | 34.3 | 短线偏弱 | 17.4 | 偏弱 | weak_or_cooling |
| 58 | 建筑装饰 | 34.3 | 短线偏弱 | 17.2 | 偏弱 | weak_or_cooling |
| 59 | 房地产 | 34.3 | 短线偏弱 | 17.2 | 偏弱 | weak_or_cooling |
| 60 | 贸易 | 34.3 | 短线偏弱 | 17.2 | 偏弱 | weak_or_cooling |
| 61 | 电池 | 34.3 | 短线偏弱 | 12.4 | 偏弱 | weak_or_cooling |
| 62 | 软件开发 | 34.3 | 短线偏弱 | 12.4 | 偏弱 | weak_or_cooling |
| 63 | 游戏 | 31.3 | 短线偏弱 | 58.2 | 中性 | neutral |
| 64 | 医疗服务 | 31.3 | 短线偏弱 | 55.5 | 中性 | neutral |
| 65 | 小金属 | 31.3 | 短线偏弱 | 43.5 | 降温 | weak_or_cooling |
| 66 | 厨卫电器 | 31.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 67 | 白酒 | 31.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 68 | 油气开采及服务 | 31.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 69 | 能源金属 | 31.3 | 短线偏弱 | 20.6 | 偏弱 | weak_or_cooling |
| 70 | 建筑材料 | 31.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 71 | 电网设备 | 31.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 72 | 风电设备 | 31.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 73 | 电力 | 31.3 | 短线偏弱 | 13.2 | 偏弱 | weak_or_cooling |
| 74 | 工业金属 | 31.3 | 短线偏弱 | 12.4 | 偏弱 | weak_or_cooling |
| 75 | 电子化学品 | 30.3 | 短线偏弱 | 62.5 | 中性 | neutral |
| 76 | 证券 | 30.3 | 短线偏弱 | 47.6 | 降温 | weak_or_cooling |
| 77 | 光学光电子 | 30.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 78 | 军工电子 | 30.3 | 短线偏弱 | 34.5 | 偏弱 | weak_or_cooling |
| 79 | 计算机设备 | 30.3 | 短线偏弱 | 30.2 | 偏弱 | weak_or_cooling |
| 80 | 自动化设备 | 30.3 | 短线偏弱 | 25.4 | 偏弱 | weak_or_cooling |
| 81 | 通信服务 | 30.3 | 短线偏弱 | 17.4 | 偏弱 | weak_or_cooling |
| 82 | 非金属材料 | 28.3 | 短线偏弱 | 21.6 | 偏弱 | weak_or_cooling |
| 83 | 机场航运 | 28.3 | 短线偏弱 | 14.4 | 偏弱 | weak_or_cooling |
| 84 | 半导体 | 27.3 | 短线偏弱 | 50.6 | 中性 | neutral |
| 85 | 光伏设备 | 27.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 86 | 消费电子 | 27.3 | 短线偏弱 | 16.4 | 偏弱 | weak_or_cooling |
| 87 | 其他电子 | 24.3 | 短线偏弱 | 27.4 | 偏弱 | weak_or_cooling |
| 88 | 其他电源设备 | 24.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 89 | 通信设备 | 24.3 | 短线偏弱 | 12.4 | 偏弱 | weak_or_cooling |
| 90 | 元件 | 21.3 | 短线偏弱 | 18.6 | 偏弱 | weak_or_cooling |

## 分歧板块

当前无明显分歧板块。

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 电子化学品

**趋势持续评分**:
- 趋势分: 62.5
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 6.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 4.0

**短线爆发评分**:
- 短线分: 30.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 3.3
  - one_day_change_component: 0.0
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

### 2. 化学制药

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

### 3. 游戏

**趋势持续评分**:
- 趋势分: 58.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 4.0

**短线爆发评分**:
- 短线分: 31.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 3.3
  - one_day_change_component: 4.0
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

### 4. 物流

**趋势持续评分**:
- 趋势分: 57.0
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 10.0
  - relative_strength_component: 17.0
  - persistence_component: 10.0
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

### 5. 医疗服务

**趋势持续评分**:
- 趋势分: 55.5
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 6.0

**短线爆发评分**:
- 短线分: 31.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 3.3
  - one_day_change_component: 4.0
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

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
