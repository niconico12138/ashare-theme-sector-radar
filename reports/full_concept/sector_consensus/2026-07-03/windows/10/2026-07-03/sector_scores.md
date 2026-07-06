# 板块综合评分

**分析日期**: 2026-07-03
**更新时间**: 2026-07-03T19:45:47.946038

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。

## 数据来源

- **板块类型**: concept
- **历史数据范围**: 2026-05-20 ~ 2026-07-03
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

## 趋势持续 Top 120

| 排名 | 板块 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 氟化工概念 | 64.2 | 中性 | 48.8 | 短线降温 | neutral |
| 2 | 光刻胶 | 62.2 | 中性 | 30.3 | 短线偏弱 | neutral |
| 3 | 动物疫苗 | 62.0 | 中性 | 45.8 | 短线降温 | neutral |
| 4 | 丙烯酸 | 61.0 | 中性 | 45.8 | 短线降温 | neutral |
| 5 | 仿制药一致性评价 | 58.2 | 中性 | 58.8 | 短线中性 | neutral |
| 6 | 第三代半导体 | 55.5 | 中性 | 27.3 | 短线偏弱 | neutral |
| 7 | 创新药 | 55.2 | 中性 | 45.8 | 短线降温 | neutral |
| 8 | 合成生物 | 55.2 | 中性 | 45.8 | 短线降温 | neutral |
| 9 | 阿尔茨海默概念 | 55.2 | 中性 | 45.8 | 短线降温 | neutral |
| 10 | 海南自贸区 | 55.0 | 中性 | 58.8 | 短线中性 | neutral |
| 11 | 存储芯片 | 53.5 | 中性 | 24.3 | 短线偏弱 | neutral |
| 12 | 肝炎概念 | 50.2 | 中性 | 45.8 | 短线降温 | neutral |
| 13 | 辅助生殖 | 50.2 | 中性 | 45.8 | 短线降温 | neutral |
| 14 | 国家大基金持股 | 48.6 | 降温 | 24.3 | 短线偏弱 | weak_or_cooling |
| 15 | 环氧丙烷 | 48.0 | 降温 | 55.8 | 短线中性 | neutral |
| 16 | 工业大麻 | 47.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 17 | 超级品牌 | 47.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 18 | 重组蛋白 | 46.6 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 19 | 光刻机 | 46.5 | 降温 | 24.3 | 短线偏弱 | weak_or_cooling |
| 20 | 硅能源 | 45.2 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 21 | 猴痘概念 | 44.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 22 | 电子纸 | 44.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 23 | 长三角一体化 | 41.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 24 | 芬太尼 | 41.2 | 降温 | 55.8 | 短线中性 | neutral |
| 25 | 化肥 | 41.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 26 | 华为海思概念股 | 40.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 27 | 参股保险 | 39.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 28 | 参股银行 | 39.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 29 | 高压氧舱 | 38.5 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 30 | 宠物经济 | 37.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 31 | 三胎概念 | 37.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 32 | 传感器 | 36.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 33 | 超导概念 | 35.2 | 降温 | 24.3 | 短线偏弱 | weak_or_cooling |
| 34 | 黑龙江自贸区 | 35.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 35 | 超级电容 | 34.2 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 36 | 短剧游戏 | 34.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 37 | 航运概念 | 34.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 38 | 高股息精选 | 34.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 39 | AI PC | 33.5 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 40 | 核污染防治 | 32.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 41 | 草甘膦 | 32.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 42 | 东数西算(算力) | 30.2 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 43 | 宁德时代概念 | 30.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 44 | 固废处理 | 30.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 45 | AI手机 | 29.4 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 46 | 供销社 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 47 | 共同富裕示范区 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 48 | 军工 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 49 | 冰雪产业 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 50 | 华为概念 | 28.2 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 51 | 参股券商 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 52 | 固态电池 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 53 | 国企改革 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 54 | 多模态AI | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 55 | 工业互联网 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 56 | 工业母机 | 28.2 | 偏弱 | 37.3 | 短线降温 | weak_or_cooling |
| 57 | 广东自贸区 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 58 | 抖音概念(字节概念) | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 59 | 比亚迪概念 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 60 | 独角兽概念 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 61 | 白酒概念 | 28.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 62 | 股权转让(并购重组) | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 63 | 车联网(车路协同) | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 64 | 地下管网 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 65 | 大豆 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 66 | 钙钛矿电池 | 27.2 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 67 | ETC | 26.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 68 | EDR概念 | 25.4 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 69 | 富士康概念 | 25.4 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 70 | 黄金概念 | 25.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 71 | 共封装光学(CPO) | 24.6 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |
| 72 | BC电池 | 24.2 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 73 | 国产操作系统 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 74 | 换电概念 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 75 | 百度概念 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 76 | 福建自贸区 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 77 | 阿里巴巴概念 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 78 | 鸿蒙概念 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 79 | 低空经济 | 23.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 80 | 光伏概念 | 23.2 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 81 | 创投 | 23.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 82 | 大飞机 | 23.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 83 | 安防 | 23.2 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 84 | 核电 | 23.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 85 | 海峡两岸 | 23.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 86 | 电子竞技 | 23.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 87 | 航空发动机 | 23.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 88 | 钒电池 | 23.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 89 | 锂电池概念 | 23.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 90 | 飞行汽车(eVTOL) | 23.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 91 | 高端装备 | 23.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 92 | 金属钴 | 23.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 93 | AI语料 | 21.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 94 | 华为鲲鹏 | 21.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 95 | 毫米波雷达 | 21.4 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 96 | 电子身份证 | 21.4 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 97 | 互联网金融 | 20.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 98 | ERP概念 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 99 | 俄乌冲突概念 | 19.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 100 | 储能 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 101 | 充电桩 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 102 | 共享单车 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 103 | 动力电池回收 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 104 | 国产航母 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 105 | 国资云 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 106 | 成飞概念 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 107 | 抽水蓄能 | 19.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 108 | 横琴新区 | 19.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 109 | 海工装备 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 110 | 电力物联网 | 19.2 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 111 | 风电 | 19.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 112 | 高压快充 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 113 | 高铁 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 114 | 华为欧拉 | 17.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 115 | 代糖概念 | 17.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 116 | 光热发电 | 17.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 117 | 华为汽车 | 17.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 118 | 长安汽车概念 | 17.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 119 | 超超临界发电 | 15.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 120 | F5G概念 | 14.7 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 120

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 仿制药一致性评价 | 58.8 | 短线中性 | 58.2 | 中性 | neutral |
| 2 | 海南自贸区 | 58.8 | 短线中性 | 55.0 | 中性 | neutral |
| 3 | 环氧丙烷 | 55.8 | 短线中性 | 48.0 | 降温 | neutral |
| 4 | 芬太尼 | 55.8 | 短线中性 | 41.2 | 降温 | neutral |
| 5 | 氟化工概念 | 48.8 | 短线降温 | 64.2 | 中性 | neutral |
| 6 | 动物疫苗 | 45.8 | 短线降温 | 62.0 | 中性 | neutral |
| 7 | 丙烯酸 | 45.8 | 短线降温 | 61.0 | 中性 | neutral |
| 8 | 创新药 | 45.8 | 短线降温 | 55.2 | 中性 | neutral |
| 9 | 合成生物 | 45.8 | 短线降温 | 55.2 | 中性 | neutral |
| 10 | 阿尔茨海默概念 | 45.8 | 短线降温 | 55.2 | 中性 | neutral |
| 11 | 肝炎概念 | 45.8 | 短线降温 | 50.2 | 中性 | neutral |
| 12 | 辅助生殖 | 45.8 | 短线降温 | 50.2 | 中性 | neutral |
| 13 | 工业大麻 | 45.8 | 短线降温 | 47.0 | 降温 | weak_or_cooling |
| 14 | 超级品牌 | 45.8 | 短线降温 | 47.0 | 降温 | weak_or_cooling |
| 15 | 化肥 | 45.8 | 短线降温 | 41.0 | 降温 | weak_or_cooling |
| 16 | 参股保险 | 45.8 | 短线降温 | 39.0 | 降温 | weak_or_cooling |
| 17 | 参股银行 | 45.8 | 短线降温 | 39.0 | 降温 | weak_or_cooling |
| 18 | 三胎概念 | 45.8 | 短线降温 | 37.0 | 降温 | weak_or_cooling |
| 19 | 短剧游戏 | 45.8 | 短线降温 | 34.0 | 偏弱 | weak_or_cooling |
| 20 | 航运概念 | 45.8 | 短线降温 | 34.0 | 偏弱 | weak_or_cooling |
| 21 | 固废处理 | 45.8 | 短线降温 | 30.0 | 偏弱 | weak_or_cooling |
| 22 | 地下管网 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 23 | 黄金概念 | 45.8 | 短线降温 | 25.2 | 偏弱 | weak_or_cooling |
| 24 | 金属钴 | 45.8 | 短线降温 | 23.2 | 偏弱 | weak_or_cooling |
| 25 | 高股息精选 | 42.8 | 短线降温 | 34.0 | 偏弱 | weak_or_cooling |
| 26 | 草甘膦 | 42.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 27 | 大豆 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 28 | 工业母机 | 37.3 | 短线降温 | 28.2 | 偏弱 | weak_or_cooling |
| 29 | 重组蛋白 | 34.3 | 短线偏弱 | 46.6 | 降温 | weak_or_cooling |
| 30 | 猴痘概念 | 34.3 | 短线偏弱 | 44.5 | 降温 | weak_or_cooling |
| 31 | 长三角一体化 | 34.3 | 短线偏弱 | 41.2 | 降温 | weak_or_cooling |
| 32 | 宠物经济 | 34.3 | 短线偏弱 | 37.2 | 降温 | weak_or_cooling |
| 33 | 传感器 | 34.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 34 | 黑龙江自贸区 | 34.3 | 短线偏弱 | 35.2 | 降温 | weak_or_cooling |
| 35 | 核污染防治 | 34.3 | 短线偏弱 | 32.2 | 偏弱 | weak_or_cooling |
| 36 | 宁德时代概念 | 34.3 | 短线偏弱 | 30.2 | 偏弱 | weak_or_cooling |
| 37 | 供销社 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 38 | 共同富裕示范区 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 39 | 军工 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 40 | 冰雪产业 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 41 | 参股券商 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 42 | 固态电池 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 43 | 国企改革 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 44 | 多模态AI | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 45 | 工业互联网 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 46 | 广东自贸区 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 47 | 抖音概念(字节概念) | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 48 | 比亚迪概念 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 49 | 独角兽概念 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 50 | 股权转让(并购重组) | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 51 | 车联网(车路协同) | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 52 | 国产操作系统 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 53 | 换电概念 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 54 | 百度概念 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 55 | 福建自贸区 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 56 | 阿里巴巴概念 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 57 | 鸿蒙概念 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 58 | 低空经济 | 34.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 59 | 创投 | 34.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 60 | 大飞机 | 34.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 61 | 核电 | 34.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 62 | 海峡两岸 | 34.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 63 | 电子竞技 | 34.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 64 | 航空发动机 | 34.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 65 | 锂电池概念 | 34.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 66 | 飞行汽车(eVTOL) | 34.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 67 | 高端装备 | 34.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 68 | AI语料 | 34.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 69 | 华为鲲鹏 | 34.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 70 | 互联网金融 | 34.3 | 短线偏弱 | 20.4 | 偏弱 | weak_or_cooling |
| 71 | ERP概念 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 72 | 储能 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 73 | 充电桩 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 74 | 共享单车 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 75 | 动力电池回收 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 76 | 国产航母 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 77 | 国资云 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 78 | 成飞概念 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 79 | 海工装备 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 80 | 高压快充 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 81 | 高铁 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 82 | 华为欧拉 | 34.3 | 短线偏弱 | 17.4 | 偏弱 | weak_or_cooling |
| 83 | 华为汽车 | 34.3 | 短线偏弱 | 17.2 | 偏弱 | weak_or_cooling |
| 84 | 长安汽车概念 | 34.3 | 短线偏弱 | 17.2 | 偏弱 | weak_or_cooling |
| 85 | 高压氧舱 | 31.3 | 短线偏弱 | 38.5 | 降温 | weak_or_cooling |
| 86 | 白酒概念 | 31.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 87 | ETC | 31.3 | 短线偏弱 | 26.2 | 偏弱 | weak_or_cooling |
| 88 | 钒电池 | 31.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 89 | 俄乌冲突概念 | 31.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 90 | 抽水蓄能 | 31.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 91 | 横琴新区 | 31.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 92 | 风电 | 31.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 93 | 代糖概念 | 31.3 | 短线偏弱 | 17.2 | 偏弱 | weak_or_cooling |
| 94 | 光热发电 | 31.3 | 短线偏弱 | 17.2 | 偏弱 | weak_or_cooling |
| 95 | 超超临界发电 | 31.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 96 | 光刻胶 | 30.3 | 短线偏弱 | 62.2 | 中性 | neutral |
| 97 | 硅能源 | 30.3 | 短线偏弱 | 45.2 | 降温 | weak_or_cooling |
| 98 | 电子纸 | 30.3 | 短线偏弱 | 44.5 | 降温 | weak_or_cooling |
| 99 | 华为海思概念股 | 30.3 | 短线偏弱 | 40.5 | 降温 | weak_or_cooling |
| 100 | AI PC | 30.3 | 短线偏弱 | 33.5 | 偏弱 | weak_or_cooling |
| 101 | 东数西算(算力) | 30.3 | 短线偏弱 | 30.2 | 偏弱 | weak_or_cooling |
| 102 | 华为概念 | 30.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 103 | EDR概念 | 30.3 | 短线偏弱 | 25.4 | 偏弱 | weak_or_cooling |
| 104 | 安防 | 30.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 105 | 电子身份证 | 30.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 106 | 电力物联网 | 30.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 107 | 第三代半导体 | 27.3 | 短线偏弱 | 55.5 | 中性 | neutral |
| 108 | 超级电容 | 27.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |
| 109 | AI手机 | 27.3 | 短线偏弱 | 29.4 | 偏弱 | weak_or_cooling |
| 110 | 钙钛矿电池 | 27.3 | 短线偏弱 | 27.2 | 偏弱 | weak_or_cooling |
| 111 | 富士康概念 | 27.3 | 短线偏弱 | 25.4 | 偏弱 | weak_or_cooling |
| 112 | BC电池 | 27.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 113 | 光伏概念 | 27.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 114 | 毫米波雷达 | 27.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 115 | 存储芯片 | 24.3 | 短线偏弱 | 53.5 | 中性 | neutral |
| 116 | 国家大基金持股 | 24.3 | 短线偏弱 | 48.6 | 降温 | weak_or_cooling |
| 117 | 光刻机 | 24.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 118 | 超导概念 | 24.3 | 短线偏弱 | 35.2 | 降温 | weak_or_cooling |
| 119 | 共封装光学(CPO) | 24.3 | 短线偏弱 | 24.6 | 偏弱 | weak_or_cooling |
| 120 | F5G概念 | 24.3 | 短线偏弱 | 14.7 | 偏弱 | weak_or_cooling |

## 分歧板块

当前无明显分歧板块。

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 氟化工概念

**趋势持续评分**:
- 趋势分: 64.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 2.4
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

### 2. 光刻胶

**趋势持续评分**:
- 趋势分: 62.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 0.0

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

### 3. 动物疫苗

**趋势持续评分**:
- 趋势分: 62.0
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 4.0

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

### 4. 丙烯酸

**趋势持续评分**:
- 趋势分: 61.0
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 10.0
  - relative_strength_component: 17.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 2.0

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

### 5. 仿制药一致性评价

**趋势持续评分**:
- 趋势分: 58.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
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

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
