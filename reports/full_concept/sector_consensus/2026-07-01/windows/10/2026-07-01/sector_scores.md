# 板块综合评分

**分析日期**: 2026-07-01
**更新时间**: 2026-07-05T18:21:34.325149

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
| 1 | 光刻胶 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 2 | 存储芯片 | 78.0 | 观察 | 48.8 | 短线降温 | trend_only |
| 3 | 光刻机 | 73.0 | 观察 | 45.8 | 短线降温 | trend_only |
| 4 | 氟化工概念 | 70.2 | 观察 | 69.8 | 短线活跃 | trend_and_burst_aligned |
| 5 | 第三代半导体 | 69.2 | 观察 | 37.3 | 短线降温 | trend_only |
| 6 | 国家大基金持股 | 66.5 | 观察 | 40.3 | 短线降温 | trend_only |
| 7 | 华为海思概念股 | 61.2 | 中性 | 55.8 | 短线中性 | neutral |
| 8 | 电子纸 | 59.2 | 中性 | 45.8 | 短线降温 | neutral |
| 9 | 重组蛋白 | 56.4 | 中性 | 69.8 | 短线活跃 | neutral |
| 10 | 创新药 | 56.2 | 中性 | 69.8 | 短线活跃 | neutral |
| 11 | 丙烯酸 | 54.0 | 中性 | 61.8 | 短线中性 | neutral |
| 12 | 猴痘概念 | 53.5 | 中性 | 72.3 | 短线活跃 | neutral |
| 13 | 超级电容 | 51.0 | 中性 | 55.8 | 短线中性 | neutral |
| 14 | 阿尔茨海默概念 | 50.2 | 中性 | 66.8 | 短线活跃 | neutral |
| 15 | 硅能源 | 50.0 | 中性 | 58.8 | 短线中性 | neutral |
| 16 | 动物疫苗 | 49.0 | 降温 | 63.8 | 短线中性 | neutral |
| 17 | 仿制药一致性评价 | 48.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 18 | 辅助生殖 | 48.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 19 | 合成生物 | 46.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 20 | EDR概念 | 46.0 | 降温 | 58.8 | 短线中性 | neutral |
| 21 | 共封装光学(CPO) | 45.5 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 22 | AI PC | 44.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 23 | 肝炎概念 | 44.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 24 | AI手机 | 43.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 25 | 传感器 | 43.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 26 | 核污染防治 | 42.0 | 降温 | 55.8 | 短线中性 | neutral |
| 27 | 黑龙江自贸区 | 41.0 | 降温 | 63.8 | 短线中性 | neutral |
| 28 | 超导概念 | 40.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 29 | 宠物经济 | 39.0 | 降温 | 63.8 | 短线中性 | neutral |
| 30 | 东数西算(算力) | 38.0 | 降温 | 55.8 | 短线中性 | neutral |
| 31 | 华为概念 | 38.0 | 降温 | 55.8 | 短线中性 | neutral |
| 32 | 钙钛矿电池 | 37.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 33 | 富士康概念 | 36.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 34 | 工业大麻 | 36.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 35 | 高压氧舱 | 36.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 36 | 安防 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 37 | 工业互联网 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 38 | 环氧丙烷 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 39 | 股权转让(并购重组) | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 40 | 超级品牌 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 41 | 车联网(车路协同) | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 42 | 长三角一体化 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 43 | BC电池 | 35.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 44 | 宁德时代概念 | 35.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 45 | 供销社 | 34.0 | 偏弱 | 63.8 | 短线中性 | neutral |
| 46 | ETC | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 47 | 军工 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 48 | 国产操作系统 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 49 | 比亚迪概念 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 50 | 海南自贸区 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 51 | 光伏概念 | 33.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 52 | 低空经济 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 53 | 共同富裕示范区 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 54 | 冰雪产业 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 55 | 华为鲲鹏 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 56 | 参股保险 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 57 | 参股券商 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 58 | 参股银行 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 59 | 固废处理 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 60 | 国产航母 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 61 | 国企改革 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 62 | 多模态AI | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 63 | 大飞机 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 64 | 工业母机 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 65 | 广东自贸区 | 31.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 66 | 抖音概念(字节概念) | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 67 | 独角兽概念 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 68 | 白酒概念 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 69 | 百度概念 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 70 | 短剧游戏 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 71 | 福建自贸区 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 72 | 航空发动机 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 73 | 航运概念 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 74 | 锂电池概念 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 75 | 阿里巴巴概念 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 76 | 高股息精选 | 31.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 77 | 鸿蒙概念 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 78 | 固态电池 | 30.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 79 | 毫米波雷达 | 30.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 80 | 三胎概念 | 29.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 81 | 电子身份证 | 28.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 82 | 成飞概念 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 83 | 换电概念 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 84 | 高压快充 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 85 | 互联网金融 | 26.2 | 偏弱 | 58.8 | 短线中性 | neutral |
| 86 | 化肥 | 26.2 | 偏弱 | 58.8 | 短线中性 | neutral |
| 87 | 芬太尼 | 26.2 | 偏弱 | 58.8 | 短线中性 | neutral |
| 88 | ERP概念 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 89 | 俄乌冲突概念 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 90 | 储能 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 91 | 共享单车 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 92 | 创投 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 93 | 动力电池回收 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 94 | 国资云 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 95 | 地下管网 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 96 | 大豆 | 26.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 97 | 抽水蓄能 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 98 | 核电 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 99 | 横琴新区 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 100 | 海峡两岸 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 101 | 海工装备 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 102 | 电力物联网 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 103 | 电子竞技 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 104 | 草甘膦 | 26.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 105 | 钒电池 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 106 | 风电 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 107 | 飞行汽车(eVTOL) | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 108 | 高端装备 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 109 | 高铁 | 26.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 110 | AI语料 | 24.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 111 | 华为欧拉 | 24.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 112 | 金属钴 | 24.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 113 | 代糖概念 | 24.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 114 | 光热发电 | 24.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 115 | 长安汽车概念 | 24.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 116 | 黄金概念 | 23.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 117 | 充电桩 | 23.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 118 | 超超临界发电 | 22.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 119 | 华为汽车 | 21.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 120 | F5G概念 | 19.4 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 120

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 猴痘概念 | 72.3 | 短线活跃 | 53.5 | 中性 | neutral |
| 2 | 氟化工概念 | 69.8 | 短线活跃 | 70.2 | 观察 | trend_and_burst_aligned |
| 3 | 重组蛋白 | 69.8 | 短线活跃 | 56.4 | 中性 | neutral |
| 4 | 创新药 | 69.8 | 短线活跃 | 56.2 | 中性 | neutral |
| 5 | 阿尔茨海默概念 | 66.8 | 短线活跃 | 50.2 | 中性 | neutral |
| 6 | 仿制药一致性评价 | 66.8 | 短线活跃 | 48.2 | 降温 | burst_without_trend_confirmation |
| 7 | 辅助生殖 | 66.8 | 短线活跃 | 48.2 | 降温 | burst_without_trend_confirmation |
| 8 | 合成生物 | 66.8 | 短线活跃 | 46.2 | 降温 | burst_without_trend_confirmation |
| 9 | 肝炎概念 | 66.8 | 短线活跃 | 44.2 | 降温 | burst_without_trend_confirmation |
| 10 | 工业大麻 | 66.8 | 短线活跃 | 36.2 | 降温 | burst_without_trend_confirmation |
| 11 | 高压氧舱 | 66.8 | 短线活跃 | 36.2 | 降温 | burst_without_trend_confirmation |
| 12 | 动物疫苗 | 63.8 | 短线中性 | 49.0 | 降温 | neutral |
| 13 | 黑龙江自贸区 | 63.8 | 短线中性 | 41.0 | 降温 | neutral |
| 14 | 宠物经济 | 63.8 | 短线中性 | 39.0 | 降温 | neutral |
| 15 | 供销社 | 63.8 | 短线中性 | 34.0 | 偏弱 | neutral |
| 16 | 丙烯酸 | 61.8 | 短线中性 | 54.0 | 中性 | neutral |
| 17 | 光刻胶 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 18 | 硅能源 | 58.8 | 短线中性 | 50.0 | 中性 | neutral |
| 19 | EDR概念 | 58.8 | 短线中性 | 46.0 | 降温 | neutral |
| 20 | 三胎概念 | 58.8 | 短线中性 | 29.0 | 偏弱 | neutral |
| 21 | 互联网金融 | 58.8 | 短线中性 | 26.2 | 偏弱 | neutral |
| 22 | 化肥 | 58.8 | 短线中性 | 26.2 | 偏弱 | neutral |
| 23 | 芬太尼 | 58.8 | 短线中性 | 26.2 | 偏弱 | neutral |
| 24 | 华为海思概念股 | 55.8 | 短线中性 | 61.2 | 中性 | neutral |
| 25 | 超级电容 | 55.8 | 短线中性 | 51.0 | 中性 | neutral |
| 26 | 核污染防治 | 55.8 | 短线中性 | 42.0 | 降温 | neutral |
| 27 | 东数西算(算力) | 55.8 | 短线中性 | 38.0 | 降温 | neutral |
| 28 | 华为概念 | 55.8 | 短线中性 | 38.0 | 降温 | neutral |
| 29 | 安防 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 30 | 工业互联网 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 31 | 环氧丙烷 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 32 | 股权转让(并购重组) | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 33 | 超级品牌 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 34 | 车联网(车路协同) | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 35 | 长三角一体化 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 36 | ETC | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 37 | 军工 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 38 | 国产操作系统 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 39 | 比亚迪概念 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 40 | 海南自贸区 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 41 | 低空经济 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 42 | 共同富裕示范区 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 43 | 冰雪产业 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 44 | 华为鲲鹏 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 45 | 参股保险 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 46 | 参股券商 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 47 | 参股银行 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 48 | 固废处理 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 49 | 国产航母 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 50 | 国企改革 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 51 | 多模态AI | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 52 | 大飞机 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 53 | 工业母机 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 54 | 抖音概念(字节概念) | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 55 | 独角兽概念 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 56 | 白酒概念 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 57 | 百度概念 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 58 | 短剧游戏 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 59 | 福建自贸区 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 60 | 航空发动机 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 61 | 航运概念 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 62 | 锂电池概念 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 63 | 阿里巴巴概念 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 64 | 鸿蒙概念 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 65 | 电子身份证 | 55.8 | 短线中性 | 28.2 | 偏弱 | neutral |
| 66 | ERP概念 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 67 | 俄乌冲突概念 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 68 | 储能 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 69 | 共享单车 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 70 | 创投 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 71 | 动力电池回收 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 72 | 国资云 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 73 | 地下管网 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 74 | 抽水蓄能 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 75 | 核电 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 76 | 横琴新区 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 77 | 海峡两岸 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 78 | 海工装备 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 79 | 电力物联网 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 80 | 电子竞技 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 81 | 钒电池 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 82 | 风电 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 83 | 飞行汽车(eVTOL) | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 84 | 高端装备 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 85 | 高铁 | 55.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 86 | AI语料 | 55.8 | 短线中性 | 24.2 | 偏弱 | neutral |
| 87 | 华为欧拉 | 55.8 | 短线中性 | 24.2 | 偏弱 | neutral |
| 88 | 金属钴 | 55.8 | 短线中性 | 24.2 | 偏弱 | neutral |
| 89 | 长安汽车概念 | 55.8 | 短线中性 | 24.0 | 偏弱 | neutral |
| 90 | 黄金概念 | 55.8 | 短线中性 | 23.2 | 偏弱 | neutral |
| 91 | 超超临界发电 | 55.8 | 短线中性 | 22.0 | 偏弱 | neutral |
| 92 | 广东自贸区 | 52.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 93 | 高股息精选 | 52.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 94 | 大豆 | 52.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 95 | 代糖概念 | 52.8 | 短线中性 | 24.0 | 偏弱 | neutral |
| 96 | 光热发电 | 52.8 | 短线中性 | 24.0 | 偏弱 | neutral |
| 97 | 草甘膦 | 49.8 | 短线降温 | 26.0 | 偏弱 | weak_or_cooling |
| 98 | 存储芯片 | 48.8 | 短线降温 | 78.0 | 观察 | trend_only |
| 99 | 光刻机 | 45.8 | 短线降温 | 73.0 | 观察 | trend_only |
| 100 | 电子纸 | 45.8 | 短线降温 | 59.2 | 中性 | neutral |
| 101 | 传感器 | 45.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 102 | BC电池 | 45.8 | 短线降温 | 35.0 | 降温 | weak_or_cooling |
| 103 | 宁德时代概念 | 45.8 | 短线降温 | 35.0 | 降温 | weak_or_cooling |
| 104 | 光伏概念 | 45.8 | 短线降温 | 33.0 | 偏弱 | weak_or_cooling |
| 105 | 固态电池 | 45.8 | 短线降温 | 30.0 | 偏弱 | weak_or_cooling |
| 106 | 换电概念 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 107 | 高压快充 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 108 | 充电桩 | 45.8 | 短线降温 | 23.0 | 偏弱 | weak_or_cooling |
| 109 | 华为汽车 | 45.8 | 短线降温 | 21.0 | 偏弱 | weak_or_cooling |
| 110 | 毫米波雷达 | 42.8 | 短线降温 | 30.0 | 偏弱 | weak_or_cooling |
| 111 | 成飞概念 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 112 | 国家大基金持股 | 40.3 | 短线降温 | 66.5 | 观察 | trend_only |
| 113 | 第三代半导体 | 37.3 | 短线降温 | 69.2 | 观察 | trend_only |
| 114 | AI PC | 34.3 | 短线偏弱 | 44.5 | 降温 | weak_or_cooling |
| 115 | AI手机 | 34.3 | 短线偏弱 | 43.5 | 降温 | weak_or_cooling |
| 116 | 超导概念 | 34.3 | 短线偏弱 | 40.2 | 降温 | weak_or_cooling |
| 117 | 钙钛矿电池 | 34.3 | 短线偏弱 | 37.2 | 降温 | weak_or_cooling |
| 118 | 富士康概念 | 34.3 | 短线偏弱 | 36.5 | 降温 | weak_or_cooling |
| 119 | 共封装光学(CPO) | 31.3 | 短线偏弱 | 45.5 | 降温 | weak_or_cooling |
| 120 | F5G概念 | 31.3 | 短线偏弱 | 19.4 | 偏弱 | weak_or_cooling |

## 分歧板块

### 短线强但趋势未确认

| 板块 | 短线分 | 趋势分 | 说明 |
|------|--------|--------|------|
| 仿制药一致性评价 | 66.8 | 48.2 | 短线强但趋势未确认，需谨慎 |
| 辅助生殖 | 66.8 | 48.2 | 短线强但趋势未确认，需谨慎 |
| 合成生物 | 66.8 | 46.2 | 短线强但趋势未确认，需谨慎 |
| 肝炎概念 | 66.8 | 44.2 | 短线强但趋势未确认，需谨慎 |
| 工业大麻 | 66.8 | 36.2 | 短线强但趋势未确认，需谨慎 |

### 趋势强但短线不热

| 板块 | 趋势分 | 短线分 | 说明 |
|------|--------|--------|------|
| 存储芯片 | 78.0 | 48.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 光刻机 | 73.0 | 45.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 第三代半导体 | 69.2 | 37.3 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 国家大基金持股 | 66.5 | 40.3 | 趋势强但短线不热，中长期趋势观察价值较高 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 光刻胶

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

### 2. 存储芯片

**趋势持续评分**:
- 趋势分: 78.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 0.0

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

### 3. 光刻机

**趋势持续评分**:
- 趋势分: 73.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 0.0

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

### 4. 氟化工概念

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

### 5. 第三代半导体

**趋势持续评分**:
- 趋势分: 69.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 0.0

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

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
