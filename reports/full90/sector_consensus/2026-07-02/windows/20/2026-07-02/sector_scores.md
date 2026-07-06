# 板块综合评分

**分析日期**: 2026-07-02
**更新时间**: 2026-07-02T22:58:42.121749

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
| 1 | 电子化学品 | 59.6 | 中性 | 30.3 | 短线偏弱 | neutral |
| 2 | 塑料制品 | 58.0 | 中性 | 48.8 | 短线降温 | neutral |
| 3 | 半导体 | 53.6 | 中性 | 27.3 | 短线偏弱 | neutral |
| 4 | 化学制药 | 53.2 | 中性 | 58.8 | 短线中性 | neutral |
| 5 | 化学制品 | 53.0 | 中性 | 45.8 | 短线降温 | neutral |
| 6 | 证券 | 50.5 | 中性 | 30.3 | 短线偏弱 | neutral |
| 7 | 化学原料 | 47.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 8 | 光学光电子 | 46.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 9 | 通用设备 | 46.2 | 降温 | 37.3 | 短线降温 | weak_or_cooling |
| 10 | 医疗服务 | 44.5 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 11 | 养殖业 | 44.0 | 降温 | 58.8 | 短线中性 | neutral |
| 12 | 纺织制造 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 13 | 其他电子 | 43.6 | 降温 | 24.3 | 短线偏弱 | weak_or_cooling |
| 14 | 小金属 | 43.6 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 15 | 军工电子 | 43.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 16 | 游戏 | 43.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 17 | 环保设备 | 43.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 18 | 金属新材料 | 42.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 19 | 保险 | 41.6 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 20 | 元件 | 41.6 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 21 | 自动化设备 | 41.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 22 | 物流 | 40.0 | 降温 | 58.8 | 短线中性 | neutral |
| 23 | 生物制品 | 39.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 24 | 白色家电 | 39.2 | 降温 | 37.3 | 短线降温 | weak_or_cooling |
| 25 | 化学纤维 | 39.0 | 降温 | 55.8 | 短线中性 | neutral |
| 26 | 非金属材料 | 35.5 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 27 | 工程机械 | 35.0 | 降温 | 55.8 | 短线中性 | neutral |
| 28 | 医疗器械 | 33.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 29 | 橡胶制品 | 32.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 30 | 中药 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 31 | 轨交设备 | 30.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 32 | 银行 | 29.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 33 | 专用设备 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 34 | 互联网电商 | 28.2 | 偏弱 | 37.3 | 短线降温 | weak_or_cooling |
| 35 | 其他社会服务 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 36 | 建筑材料 | 28.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 37 | 黑色家电 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 38 | 港口航运 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 39 | 造纸 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 40 | 能源金属 | 26.6 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 41 | 计算机设备 | 26.2 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 42 | 服装家纺 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 43 | 包装印刷 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 44 | 公路铁路运输 | 24.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 45 | 农化制品 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 46 | 文化传媒 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 47 | 旅游及酒店 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 48 | 汽车零部件 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 49 | 钢铁 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 50 | 食品加工制造 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 51 | 饮料制造 | 24.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 52 | 军工装备 | 23.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 53 | 贵金属 | 22.4 | 偏弱 | 63.8 | 短线中性 | neutral |
| 54 | 家居用品 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 55 | 美容护理 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 56 | 其他电源设备 | 21.4 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |
| 57 | 消费电子 | 21.4 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 58 | 电池 | 21.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 59 | 机场航运 | 20.4 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 60 | 厨卫电器 | 20.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 61 | 环境治理 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 62 | 电网设备 | 20.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 63 | 零售 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 64 | 光伏设备 | 19.2 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 65 | 汽车服务及其他 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 66 | 综合 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 67 | 农产品加工 | 19.0 | 偏弱 | 48.8 | 短线降温 | weak_or_cooling |
| 68 | 医药商业 | 19.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 69 | 小家电 | 19.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 70 | 石油加工贸易 | 19.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 71 | IT服务 | 17.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 72 | 软件开发 | 17.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 73 | 通信服务 | 17.4 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 74 | 通信设备 | 17.4 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |
| 75 | 影视院线 | 17.2 | 偏弱 | 48.8 | 短线降温 | weak_or_cooling |
| 76 | 电机 | 17.2 | 偏弱 | 48.8 | 短线降温 | weak_or_cooling |
| 77 | 多元金融 | 16.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 78 | 教育 | 16.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 79 | 建筑装饰 | 15.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 80 | 白酒 | 15.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 81 | 风电设备 | 15.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 82 | 汽车整车 | 15.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 83 | 燃气 | 15.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 84 | 种植业与林业 | 15.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 85 | 房地产 | 13.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 86 | 工业金属 | 12.4 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 87 | 煤炭开采加工 | 12.2 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 88 | 油气开采及服务 | 11.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 89 | 电力 | 11.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 90 | 贸易 | 6.5 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 90

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 贵金属 | 63.8 | 短线中性 | 22.4 | 偏弱 | neutral |
| 2 | 化学制药 | 58.8 | 短线中性 | 53.2 | 中性 | neutral |
| 3 | 养殖业 | 58.8 | 短线中性 | 44.0 | 降温 | neutral |
| 4 | 物流 | 58.8 | 短线中性 | 40.0 | 降温 | neutral |
| 5 | 纺织制造 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 6 | 化学纤维 | 55.8 | 短线中性 | 39.0 | 降温 | neutral |
| 7 | 工程机械 | 55.8 | 短线中性 | 35.0 | 降温 | neutral |
| 8 | 中药 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 9 | 造纸 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 10 | 服装家纺 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 11 | 家居用品 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 12 | 美容护理 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 13 | 银行 | 49.8 | 短线降温 | 29.0 | 偏弱 | weak_or_cooling |
| 14 | 塑料制品 | 48.8 | 短线降温 | 58.0 | 中性 | neutral |
| 15 | 农产品加工 | 48.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 16 | 影视院线 | 48.8 | 短线降温 | 17.2 | 偏弱 | weak_or_cooling |
| 17 | 电机 | 48.8 | 短线降温 | 17.2 | 偏弱 | weak_or_cooling |
| 18 | 化学制品 | 45.8 | 短线降温 | 53.0 | 中性 | neutral |
| 19 | 化学原料 | 45.8 | 短线降温 | 47.0 | 降温 | weak_or_cooling |
| 20 | 农化制品 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 21 | 文化传媒 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 22 | 旅游及酒店 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 23 | 汽车零部件 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 24 | 钢铁 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 25 | 食品加工制造 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 26 | 医药商业 | 45.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 27 | 小家电 | 45.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 28 | 石油加工贸易 | 45.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 29 | 汽车整车 | 45.8 | 短线降温 | 15.0 | 偏弱 | weak_or_cooling |
| 30 | 燃气 | 45.8 | 短线降温 | 15.0 | 偏弱 | weak_or_cooling |
| 31 | 种植业与林业 | 45.8 | 短线降温 | 15.0 | 偏弱 | weak_or_cooling |
| 32 | 港口航运 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 33 | 公路铁路运输 | 42.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 34 | 饮料制造 | 42.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 35 | 煤炭开采加工 | 42.8 | 短线降温 | 12.2 | 偏弱 | weak_or_cooling |
| 36 | 通用设备 | 37.3 | 短线降温 | 46.2 | 降温 | weak_or_cooling |
| 37 | 白色家电 | 37.3 | 短线降温 | 39.2 | 降温 | weak_or_cooling |
| 38 | 互联网电商 | 37.3 | 短线降温 | 28.2 | 偏弱 | weak_or_cooling |
| 39 | 环保设备 | 34.3 | 短线偏弱 | 43.2 | 降温 | weak_or_cooling |
| 40 | 金属新材料 | 34.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 41 | 保险 | 34.3 | 短线偏弱 | 41.6 | 降温 | weak_or_cooling |
| 42 | 生物制品 | 34.3 | 短线偏弱 | 39.5 | 降温 | weak_or_cooling |
| 43 | 医疗器械 | 34.3 | 短线偏弱 | 33.2 | 偏弱 | weak_or_cooling |
| 44 | 橡胶制品 | 34.3 | 短线偏弱 | 32.2 | 偏弱 | weak_or_cooling |
| 45 | 轨交设备 | 34.3 | 短线偏弱 | 30.2 | 偏弱 | weak_or_cooling |
| 46 | 专用设备 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 47 | 其他社会服务 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 48 | 黑色家电 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 49 | 包装印刷 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 50 | 军工装备 | 34.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 51 | 电池 | 34.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 52 | 环境治理 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 53 | 零售 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 54 | 汽车服务及其他 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 55 | 综合 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 56 | IT服务 | 34.3 | 短线偏弱 | 17.4 | 偏弱 | weak_or_cooling |
| 57 | 软件开发 | 34.3 | 短线偏弱 | 17.4 | 偏弱 | weak_or_cooling |
| 58 | 多元金融 | 34.3 | 短线偏弱 | 16.4 | 偏弱 | weak_or_cooling |
| 59 | 教育 | 34.3 | 短线偏弱 | 16.2 | 偏弱 | weak_or_cooling |
| 60 | 建筑装饰 | 34.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 61 | 房地产 | 34.3 | 短线偏弱 | 13.2 | 偏弱 | weak_or_cooling |
| 62 | 贸易 | 34.3 | 短线偏弱 | 6.5 | 偏弱 | weak_or_cooling |
| 63 | 医疗服务 | 31.3 | 短线偏弱 | 44.5 | 降温 | weak_or_cooling |
| 64 | 小金属 | 31.3 | 短线偏弱 | 43.6 | 降温 | weak_or_cooling |
| 65 | 游戏 | 31.3 | 短线偏弱 | 43.2 | 降温 | weak_or_cooling |
| 66 | 建筑材料 | 31.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 67 | 能源金属 | 31.3 | 短线偏弱 | 26.6 | 偏弱 | weak_or_cooling |
| 68 | 厨卫电器 | 31.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 69 | 电网设备 | 31.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 70 | 白酒 | 31.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 71 | 风电设备 | 31.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 72 | 工业金属 | 31.3 | 短线偏弱 | 12.4 | 偏弱 | weak_or_cooling |
| 73 | 油气开采及服务 | 31.3 | 短线偏弱 | 11.2 | 偏弱 | weak_or_cooling |
| 74 | 电力 | 31.3 | 短线偏弱 | 11.2 | 偏弱 | weak_or_cooling |
| 75 | 电子化学品 | 30.3 | 短线偏弱 | 59.6 | 中性 | neutral |
| 76 | 证券 | 30.3 | 短线偏弱 | 50.5 | 中性 | neutral |
| 77 | 光学光电子 | 30.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 78 | 军工电子 | 30.3 | 短线偏弱 | 43.5 | 降温 | weak_or_cooling |
| 79 | 自动化设备 | 30.3 | 短线偏弱 | 41.5 | 降温 | weak_or_cooling |
| 80 | 计算机设备 | 30.3 | 短线偏弱 | 26.2 | 偏弱 | weak_or_cooling |
| 81 | 通信服务 | 30.3 | 短线偏弱 | 17.4 | 偏弱 | weak_or_cooling |
| 82 | 非金属材料 | 28.3 | 短线偏弱 | 35.5 | 降温 | weak_or_cooling |
| 83 | 机场航运 | 28.3 | 短线偏弱 | 20.4 | 偏弱 | weak_or_cooling |
| 84 | 半导体 | 27.3 | 短线偏弱 | 53.6 | 中性 | neutral |
| 85 | 消费电子 | 27.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 86 | 光伏设备 | 27.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 87 | 其他电子 | 24.3 | 短线偏弱 | 43.6 | 降温 | weak_or_cooling |
| 88 | 其他电源设备 | 24.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 89 | 通信设备 | 24.3 | 短线偏弱 | 17.4 | 偏弱 | weak_or_cooling |
| 90 | 元件 | 21.3 | 短线偏弱 | 41.6 | 降温 | weak_or_cooling |

## 分歧板块

当前无明显分歧板块。

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 电子化学品

**趋势持续评分**:
- 趋势分: 59.6
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 1.6
  - data_quality_component: 6.4
  - risk_penalty: 6.0

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

### 2. 塑料制品

**趋势持续评分**:
- 趋势分: 58.0
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 4.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 6.0

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
- Profile: neutral
- Summary: 表现中性，可作为备选观察
- Watch points:
  - 等待更多确认信号
  - 关注后续表现

### 3. 半导体

**趋势持续评分**:
- 趋势分: 53.6
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 4.0
  - volatility_component: 1.6
  - data_quality_component: 6.4
  - risk_penalty: 10.0

**短线爆发评分**:
- 短线分: 27.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 3.3
  - one_day_change_component: 0.0
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

### 4. 化学制药

**趋势持续评分**:
- 趋势分: 53.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 10.0
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

### 5. 化学制品

**趋势持续评分**:
- 趋势分: 53.0
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 10.0
  - drawdown_component: 4.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 6.0

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
