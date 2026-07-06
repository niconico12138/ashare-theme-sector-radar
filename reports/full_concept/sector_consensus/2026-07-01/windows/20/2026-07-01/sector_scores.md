# 板块综合评分

**分析日期**: 2026-07-01
**更新时间**: 2026-07-05T18:21:34.361216

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。

## 数据来源

- **板块类型**: concept
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

## 趋势持续 Top 120

| 排名 | 板块 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 光刻胶 | 74.2 | 观察 | 58.8 | 短线中性 | neutral |
| 2 | 氟化工概念 | 70.2 | 观察 | 69.8 | 短线活跃 | trend_and_burst_aligned |
| 3 | 光刻机 | 66.2 | 观察 | 45.8 | 短线降温 | trend_only |
| 4 | 硅能源 | 65.0 | 观察 | 58.8 | 短线中性 | neutral |
| 5 | 存储芯片 | 62.2 | 中性 | 48.8 | 短线降温 | neutral |
| 6 | 第三代半导体 | 56.5 | 中性 | 37.3 | 短线降温 | neutral |
| 7 | 传感器 | 56.0 | 中性 | 45.8 | 短线降温 | neutral |
| 8 | 国家大基金持股 | 55.6 | 中性 | 40.3 | 短线降温 | neutral |
| 9 | 华为海思概念股 | 50.2 | 中性 | 55.8 | 短线中性 | neutral |
| 10 | 超级电容 | 50.2 | 中性 | 55.8 | 短线中性 | neutral |
| 11 | 电子纸 | 50.2 | 中性 | 45.8 | 短线降温 | neutral |
| 12 | 动物疫苗 | 49.0 | 降温 | 63.8 | 短线中性 | neutral |
| 13 | 钙钛矿电池 | 47.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 14 | 富士康概念 | 46.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 15 | 丙烯酸 | 46.0 | 降温 | 61.8 | 短线中性 | neutral |
| 16 | 工业母机 | 46.0 | 降温 | 55.8 | 短线中性 | neutral |
| 17 | 超导概念 | 44.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 18 | 重组蛋白 | 44.2 | 降温 | 69.8 | 短线活跃 | burst_without_trend_confirmation |
| 19 | BC电池 | 44.2 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 20 | 共封装光学(CPO) | 43.6 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 21 | AI手机 | 43.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 22 | 核污染防治 | 42.0 | 降温 | 55.8 | 短线中性 | neutral |
| 23 | 航空发动机 | 42.0 | 降温 | 55.8 | 短线中性 | neutral |
| 24 | 合成生物 | 41.0 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 25 | 创新药 | 40.2 | 降温 | 69.8 | 短线活跃 | burst_without_trend_confirmation |
| 26 | 固态电池 | 40.2 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 27 | 环氧丙烷 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 28 | 锂电池概念 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 29 | 光伏概念 | 39.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 30 | 宁德时代概念 | 39.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 31 | 猴痘概念 | 38.5 | 降温 | 72.3 | 短线活跃 | burst_without_trend_confirmation |
| 32 | 东数西算(算力) | 38.0 | 降温 | 55.8 | 短线中性 | neutral |
| 33 | 军工 | 38.0 | 降温 | 55.8 | 短线中性 | neutral |
| 34 | 华为概念 | 38.0 | 降温 | 55.8 | 短线中性 | neutral |
| 35 | 大飞机 | 38.0 | 降温 | 55.8 | 短线中性 | neutral |
| 36 | 比亚迪概念 | 38.0 | 降温 | 55.8 | 短线中性 | neutral |
| 37 | 仿制药一致性评价 | 36.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 38 | 辅助生殖 | 36.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 39 | 阿尔茨海默概念 | 36.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 40 | 毫米波雷达 | 36.2 | 降温 | 42.8 | 短线降温 | weak_or_cooling |
| 41 | 安防 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 42 | AI PC | 34.5 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 43 | 宠物经济 | 34.0 | 偏弱 | 63.8 | 短线中性 | neutral |
| 44 | 芬太尼 | 34.0 | 偏弱 | 63.8 | 短线中性 | neutral |
| 45 | 高压氧舱 | 34.0 | 偏弱 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 46 | F5G概念 | 33.6 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 47 | EDR概念 | 33.2 | 偏弱 | 58.8 | 短线中性 | neutral |
| 48 | 国产操作系统 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 49 | 肝炎概念 | 32.2 | 偏弱 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 50 | 低空经济 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 51 | 共同富裕示范区 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 52 | 创投 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 53 | 参股银行 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 54 | 国产航母 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 55 | 国企改革 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 56 | 工业互联网 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 57 | 广东自贸区 | 31.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 58 | 核电 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 59 | 海峡两岸 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 60 | 海工装备 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 61 | 独角兽概念 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 62 | 电子竞技 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 63 | 福建自贸区 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 64 | 股权转让(并购重组) | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 65 | 草甘膦 | 31.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 66 | 超级品牌 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 67 | 车联网(车路协同) | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 68 | 长三角一体化 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 69 | 风电 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 70 | 飞行汽车(eVTOL) | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 71 | 高端装备 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 72 | 高铁 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 73 | 互联网金融 | 30.0 | 偏弱 | 63.8 | 短线中性 | neutral |
| 74 | 供销社 | 30.0 | 偏弱 | 63.8 | 短线中性 | neutral |
| 75 | 化肥 | 30.0 | 偏弱 | 63.8 | 短线中性 | neutral |
| 76 | 工业大麻 | 30.0 | 偏弱 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 77 | 黑龙江自贸区 | 30.0 | 偏弱 | 63.8 | 短线中性 | neutral |
| 78 | ETC | 29.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 79 | 海南自贸区 | 29.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 80 | 成飞概念 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 81 | 高压快充 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 82 | 共享单车 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 83 | 冰雪产业 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 84 | 华为欧拉 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 85 | 华为鲲鹏 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 86 | 参股券商 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 87 | 固废处理 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 88 | 国资云 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 89 | 多模态AI | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 90 | 抖音概念(字节概念) | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 91 | 抽水蓄能 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 92 | 横琴新区 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 93 | 电力物联网 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 94 | 电子身份证 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 95 | 百度概念 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 96 | 短剧游戏 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 97 | 阿里巴巴概念 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 98 | 高股息精选 | 27.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 99 | 鸿蒙概念 | 27.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 100 | 金属钴 | 26.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 101 | 俄乌冲突概念 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 102 | 储能 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 103 | 动力电池回收 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 104 | 钒电池 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 105 | 长安汽车概念 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 106 | 三胎概念 | 25.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 107 | AI语料 | 24.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 108 | 换电概念 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 109 | 黄金概念 | 23.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 110 | 超超临界发电 | 23.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 111 | 充电桩 | 23.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 112 | 华为汽车 | 23.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 113 | ERP概念 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 114 | 代糖概念 | 22.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 115 | 光热发电 | 22.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 116 | 参股保险 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 117 | 地下管网 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 118 | 白酒概念 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 119 | 航运概念 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 120 | 大豆 | 20.0 | 偏弱 | 52.8 | 短线中性 | neutral |

## 短线爆发 Top 120

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 猴痘概念 | 72.3 | 短线活跃 | 38.5 | 降温 | burst_without_trend_confirmation |
| 2 | 氟化工概念 | 69.8 | 短线活跃 | 70.2 | 观察 | trend_and_burst_aligned |
| 3 | 重组蛋白 | 69.8 | 短线活跃 | 44.2 | 降温 | burst_without_trend_confirmation |
| 4 | 创新药 | 69.8 | 短线活跃 | 40.2 | 降温 | burst_without_trend_confirmation |
| 5 | 合成生物 | 66.8 | 短线活跃 | 41.0 | 降温 | burst_without_trend_confirmation |
| 6 | 仿制药一致性评价 | 66.8 | 短线活跃 | 36.2 | 降温 | burst_without_trend_confirmation |
| 7 | 辅助生殖 | 66.8 | 短线活跃 | 36.2 | 降温 | burst_without_trend_confirmation |
| 8 | 阿尔茨海默概念 | 66.8 | 短线活跃 | 36.2 | 降温 | burst_without_trend_confirmation |
| 9 | 高压氧舱 | 66.8 | 短线活跃 | 34.0 | 偏弱 | burst_without_trend_confirmation |
| 10 | 肝炎概念 | 66.8 | 短线活跃 | 32.2 | 偏弱 | burst_without_trend_confirmation |
| 11 | 工业大麻 | 66.8 | 短线活跃 | 30.0 | 偏弱 | burst_without_trend_confirmation |
| 12 | 动物疫苗 | 63.8 | 短线中性 | 49.0 | 降温 | neutral |
| 13 | 宠物经济 | 63.8 | 短线中性 | 34.0 | 偏弱 | neutral |
| 14 | 芬太尼 | 63.8 | 短线中性 | 34.0 | 偏弱 | neutral |
| 15 | 互联网金融 | 63.8 | 短线中性 | 30.0 | 偏弱 | neutral |
| 16 | 供销社 | 63.8 | 短线中性 | 30.0 | 偏弱 | neutral |
| 17 | 化肥 | 63.8 | 短线中性 | 30.0 | 偏弱 | neutral |
| 18 | 黑龙江自贸区 | 63.8 | 短线中性 | 30.0 | 偏弱 | neutral |
| 19 | 丙烯酸 | 61.8 | 短线中性 | 46.0 | 降温 | neutral |
| 20 | 光刻胶 | 58.8 | 短线中性 | 74.2 | 观察 | neutral |
| 21 | 硅能源 | 58.8 | 短线中性 | 65.0 | 观察 | neutral |
| 22 | EDR概念 | 58.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 23 | 三胎概念 | 58.8 | 短线中性 | 25.0 | 偏弱 | neutral |
| 24 | 华为海思概念股 | 55.8 | 短线中性 | 50.2 | 中性 | neutral |
| 25 | 超级电容 | 55.8 | 短线中性 | 50.2 | 中性 | neutral |
| 26 | 工业母机 | 55.8 | 短线中性 | 46.0 | 降温 | neutral |
| 27 | 核污染防治 | 55.8 | 短线中性 | 42.0 | 降温 | neutral |
| 28 | 航空发动机 | 55.8 | 短线中性 | 42.0 | 降温 | neutral |
| 29 | 环氧丙烷 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 30 | 锂电池概念 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 31 | 东数西算(算力) | 55.8 | 短线中性 | 38.0 | 降温 | neutral |
| 32 | 军工 | 55.8 | 短线中性 | 38.0 | 降温 | neutral |
| 33 | 华为概念 | 55.8 | 短线中性 | 38.0 | 降温 | neutral |
| 34 | 大飞机 | 55.8 | 短线中性 | 38.0 | 降温 | neutral |
| 35 | 比亚迪概念 | 55.8 | 短线中性 | 38.0 | 降温 | neutral |
| 36 | 安防 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 37 | 国产操作系统 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 38 | 低空经济 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 39 | 共同富裕示范区 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 40 | 创投 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 41 | 参股银行 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 42 | 国产航母 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 43 | 国企改革 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 44 | 工业互联网 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 45 | 核电 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 46 | 海峡两岸 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 47 | 海工装备 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 48 | 独角兽概念 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 49 | 电子竞技 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 50 | 福建自贸区 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 51 | 股权转让(并购重组) | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 52 | 超级品牌 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 53 | 车联网(车路协同) | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 54 | 长三角一体化 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 55 | 风电 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 56 | 飞行汽车(eVTOL) | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 57 | 高端装备 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 58 | 高铁 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 59 | ETC | 55.8 | 短线中性 | 29.0 | 偏弱 | neutral |
| 60 | 海南自贸区 | 55.8 | 短线中性 | 29.0 | 偏弱 | neutral |
| 61 | 共享单车 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 62 | 冰雪产业 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 63 | 华为欧拉 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 64 | 华为鲲鹏 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 65 | 参股券商 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 66 | 固废处理 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 67 | 国资云 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 68 | 多模态AI | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 69 | 抖音概念(字节概念) | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 70 | 抽水蓄能 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 71 | 横琴新区 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 72 | 电力物联网 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 73 | 电子身份证 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 74 | 百度概念 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 75 | 短剧游戏 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 76 | 阿里巴巴概念 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 77 | 鸿蒙概念 | 55.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 78 | 金属钴 | 55.8 | 短线中性 | 26.2 | 偏弱 | neutral |
| 79 | 俄乌冲突概念 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 80 | 储能 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 81 | 动力电池回收 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 82 | 钒电池 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 83 | 长安汽车概念 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 84 | AI语料 | 55.8 | 短线中性 | 24.2 | 偏弱 | neutral |
| 85 | 黄金概念 | 55.8 | 短线中性 | 23.2 | 偏弱 | neutral |
| 86 | 超超临界发电 | 55.8 | 短线中性 | 23.0 | 偏弱 | neutral |
| 87 | ERP概念 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 88 | 参股保险 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 89 | 地下管网 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 90 | 白酒概念 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 91 | 航运概念 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 92 | 广东自贸区 | 52.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 93 | 高股息精选 | 52.8 | 短线中性 | 27.0 | 偏弱 | neutral |
| 94 | 代糖概念 | 52.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 95 | 光热发电 | 52.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 96 | 大豆 | 52.8 | 短线中性 | 20.0 | 偏弱 | neutral |
| 97 | 草甘膦 | 49.8 | 短线降温 | 31.0 | 偏弱 | weak_or_cooling |
| 98 | 存储芯片 | 48.8 | 短线降温 | 62.2 | 中性 | neutral |
| 99 | 光刻机 | 45.8 | 短线降温 | 66.2 | 观察 | trend_only |
| 100 | 传感器 | 45.8 | 短线降温 | 56.0 | 中性 | neutral |
| 101 | 电子纸 | 45.8 | 短线降温 | 50.2 | 中性 | neutral |
| 102 | BC电池 | 45.8 | 短线降温 | 44.2 | 降温 | weak_or_cooling |
| 103 | 固态电池 | 45.8 | 短线降温 | 40.2 | 降温 | weak_or_cooling |
| 104 | 光伏概念 | 45.8 | 短线降温 | 39.0 | 降温 | weak_or_cooling |
| 105 | 宁德时代概念 | 45.8 | 短线降温 | 39.0 | 降温 | weak_or_cooling |
| 106 | 高压快充 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 107 | 换电概念 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 108 | 充电桩 | 45.8 | 短线降温 | 23.0 | 偏弱 | weak_or_cooling |
| 109 | 华为汽车 | 45.8 | 短线降温 | 23.0 | 偏弱 | weak_or_cooling |
| 110 | 毫米波雷达 | 42.8 | 短线降温 | 36.2 | 降温 | weak_or_cooling |
| 111 | 成飞概念 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 112 | 国家大基金持股 | 40.3 | 短线降温 | 55.6 | 中性 | neutral |
| 113 | 第三代半导体 | 37.3 | 短线降温 | 56.5 | 中性 | neutral |
| 114 | 钙钛矿电池 | 34.3 | 短线偏弱 | 47.2 | 降温 | weak_or_cooling |
| 115 | 富士康概念 | 34.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 116 | 超导概念 | 34.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 117 | AI手机 | 34.3 | 短线偏弱 | 43.5 | 降温 | weak_or_cooling |
| 118 | AI PC | 34.3 | 短线偏弱 | 34.5 | 偏弱 | weak_or_cooling |
| 119 | 共封装光学(CPO) | 31.3 | 短线偏弱 | 43.6 | 降温 | weak_or_cooling |
| 120 | F5G概念 | 31.3 | 短线偏弱 | 33.6 | 偏弱 | weak_or_cooling |

## 分歧板块

### 短线强但趋势未确认

| 板块 | 短线分 | 趋势分 | 说明 |
|------|--------|--------|------|
| 重组蛋白 | 69.8 | 44.2 | 短线强但趋势未确认，需谨慎 |
| 合成生物 | 66.8 | 41.0 | 短线强但趋势未确认，需谨慎 |
| 创新药 | 69.8 | 40.2 | 短线强但趋势未确认，需谨慎 |
| 猴痘概念 | 72.3 | 38.5 | 短线强但趋势未确认，需谨慎 |
| 仿制药一致性评价 | 66.8 | 36.2 | 短线强但趋势未确认，需谨慎 |

### 趋势强但短线不热

| 板块 | 趋势分 | 短线分 | 说明 |
|------|--------|--------|------|
| 光刻机 | 66.2 | 45.8 | 趋势强但短线不热，中长期趋势观察价值较高 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 光刻胶

**趋势持续评分**:
- 趋势分: 74.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 6.0
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

### 2. 氟化工概念

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
- Profile: trend_and_burst_aligned
- Summary: 趋势和短线都强，双重确认
- Watch points:
  - 趋势和短线双重确认，可重点关注
  - 观察是否能持续保持双强态势

### 3. 光刻机

**趋势持续评分**:
- 趋势分: 66.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 2.4
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
- Profile: trend_only
- Summary: 趋势强但短线不热，中长期趋势观察价值较高
- Watch points:
  - 趋势持续性好，但短线缺乏爆发力
  - 观察是否有催化剂推动短线表现

### 4. 硅能源

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

### 5. 存储芯片

**趋势持续评分**:
- 趋势分: 62.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 4.0
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

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
