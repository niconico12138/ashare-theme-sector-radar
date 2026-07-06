# 板块综合评分

**分析日期**: 2026-07-01
**更新时间**: 2026-07-05T18:21:34.289165

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

## 趋势持续 Top 120

| 排名 | 板块 | 趋势分 | 趋势等级 | 短线分 | 短线等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 存储芯片 | 78.0 | 观察 | 48.8 | 短线降温 | trend_only |
| 2 | 光刻机 | 75.0 | 观察 | 45.8 | 短线降温 | trend_only |
| 3 | 光刻胶 | 71.0 | 观察 | 58.8 | 短线中性 | neutral |
| 4 | 硅能源 | 71.0 | 观察 | 58.8 | 短线中性 | neutral |
| 5 | 氟化工概念 | 67.2 | 观察 | 69.8 | 短线活跃 | trend_and_burst_aligned |
| 6 | 国家大基金持股 | 64.5 | 中性 | 40.3 | 短线降温 | neutral |
| 7 | 第三代半导体 | 61.2 | 中性 | 37.3 | 短线降温 | neutral |
| 8 | 电子纸 | 58.2 | 中性 | 45.8 | 短线降温 | neutral |
| 9 | BC电池 | 58.0 | 中性 | 45.8 | 短线降温 | neutral |
| 10 | 创新药 | 57.4 | 中性 | 69.8 | 短线活跃 | neutral |
| 11 | 重组蛋白 | 57.4 | 中性 | 69.8 | 短线活跃 | neutral |
| 12 | 丙烯酸 | 54.0 | 中性 | 61.8 | 短线中性 | neutral |
| 13 | 黑龙江自贸区 | 54.0 | 中性 | 63.8 | 短线中性 | neutral |
| 14 | 合成生物 | 53.2 | 中性 | 66.8 | 短线活跃 | neutral |
| 15 | 猴痘概念 | 52.6 | 中性 | 72.3 | 短线活跃 | neutral |
| 16 | 华为海思概念股 | 52.2 | 中性 | 55.8 | 短线中性 | neutral |
| 17 | 超级电容 | 52.2 | 中性 | 55.8 | 短线中性 | neutral |
| 18 | 超级品牌 | 52.0 | 中性 | 55.8 | 短线中性 | neutral |
| 19 | 参股保险 | 51.0 | 中性 | 55.8 | 短线中性 | neutral |
| 20 | 仿制药一致性评价 | 50.4 | 中性 | 66.8 | 短线活跃 | neutral |
| 21 | 肝炎概念 | 50.4 | 中性 | 66.8 | 短线活跃 | neutral |
| 22 | 阿尔茨海默概念 | 50.4 | 中性 | 66.8 | 短线活跃 | neutral |
| 23 | 钙钛矿电池 | 49.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 24 | 工业大麻 | 49.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 25 | 动物疫苗 | 48.2 | 降温 | 63.8 | 短线中性 | neutral |
| 26 | 共同富裕示范区 | 47.0 | 降温 | 55.8 | 短线中性 | neutral |
| 27 | 国企改革 | 47.0 | 降温 | 55.8 | 短线中性 | neutral |
| 28 | 福建自贸区 | 47.0 | 降温 | 55.8 | 短线中性 | neutral |
| 29 | 辅助生殖 | 46.4 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 30 | 超导概念 | 44.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 31 | 宠物经济 | 44.2 | 降温 | 63.8 | 短线中性 | neutral |
| 32 | 海南自贸区 | 44.2 | 降温 | 55.8 | 短线中性 | neutral |
| 33 | 军工 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 34 | 冰雪产业 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 35 | 国产航母 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 36 | 大飞机 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 37 | 工业互联网 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 38 | 广东自贸区 | 44.0 | 降温 | 52.8 | 短线中性 | neutral |
| 39 | 核污染防治 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 40 | 白酒概念 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 41 | 股权转让(并购重组) | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 42 | 长三角一体化 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 43 | 飞行汽车(eVTOL) | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 44 | 高端装备 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 45 | 供销社 | 43.0 | 降温 | 63.8 | 短线中性 | neutral |
| 46 | EDR概念 | 41.2 | 降温 | 58.8 | 短线中性 | neutral |
| 47 | 华为概念 | 41.2 | 降温 | 55.8 | 短线中性 | neutral |
| 48 | 安防 | 41.2 | 降温 | 55.8 | 短线中性 | neutral |
| 49 | 光伏概念 | 41.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 50 | 三胎概念 | 40.2 | 降温 | 63.8 | 短线中性 | neutral |
| 51 | 化肥 | 40.2 | 降温 | 63.8 | 短线中性 | neutral |
| 52 | 俄乌冲突概念 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 53 | 储能 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 54 | 光热发电 | 40.0 | 降温 | 52.8 | 短线中性 | neutral |
| 55 | 创投 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 56 | 参股券商 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 57 | 参股银行 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 58 | 固废处理 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 59 | 地下管网 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 60 | 大豆 | 40.0 | 降温 | 52.8 | 短线中性 | neutral |
| 61 | 抽水蓄能 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 62 | 核电 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 63 | 横琴新区 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 64 | 海峡两岸 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 65 | 独角兽概念 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 66 | 电子竞技 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 67 | 短剧游戏 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 68 | 航运概念 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 69 | 超超临界发电 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 70 | 钒电池 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 71 | 风电 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 72 | 高股息精选 | 40.0 | 降温 | 52.8 | 短线中性 | neutral |
| 73 | 高铁 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 74 | AI PC | 38.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 75 | 传感器 | 38.2 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 76 | 工业母机 | 37.2 | 降温 | 55.8 | 短线中性 | neutral |
| 77 | 车联网(车路协同) | 37.2 | 降温 | 55.8 | 短线中性 | neutral |
| 78 | 充电桩 | 37.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 79 | 互联网金融 | 36.2 | 降温 | 63.8 | 短线中性 | neutral |
| 80 | 高压氧舱 | 36.2 | 降温 | 66.8 | 短线活跃 | burst_without_trend_confirmation |
| 81 | ETC | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 82 | 共享单车 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 83 | 海工装备 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 84 | 航空发动机 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 85 | 锂电池概念 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 86 | 黄金概念 | 36.0 | 降温 | 55.8 | 短线中性 | neutral |
| 87 | 芬太尼 | 33.4 | 偏弱 | 63.8 | 短线中性 | neutral |
| 88 | AI语料 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 89 | ERP概念 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 90 | 东数西算(算力) | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 91 | 低空经济 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 92 | 动力电池回收 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 93 | 华为欧拉 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 94 | 华为鲲鹏 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 95 | 国产操作系统 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 96 | 国资云 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 97 | 多模态AI | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 98 | 抖音概念(字节概念) | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 99 | 比亚迪概念 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 100 | 电力物联网 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 101 | 电子身份证 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 102 | 百度概念 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 103 | 长安汽车概念 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 104 | 阿里巴巴概念 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 105 | 鸿蒙概念 | 33.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 106 | 代糖概念 | 33.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 107 | 环氧丙烷 | 33.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 108 | 华为汽车 | 33.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 109 | 换电概念 | 33.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 110 | AI手机 | 31.6 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 111 | 富士康概念 | 30.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 112 | 固态电池 | 30.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 113 | 宁德时代概念 | 30.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 114 | 毫米波雷达 | 30.2 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 115 | 高压快充 | 30.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 116 | 金属钴 | 28.2 | 偏弱 | 55.8 | 短线中性 | neutral |
| 117 | 成飞概念 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 118 | 草甘膦 | 24.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 119 | 共封装光学(CPO) | 23.6 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 120 | F5G概念 | 11.7 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 120

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 猴痘概念 | 72.3 | 短线活跃 | 52.6 | 中性 | neutral |
| 2 | 氟化工概念 | 69.8 | 短线活跃 | 67.2 | 观察 | trend_and_burst_aligned |
| 3 | 创新药 | 69.8 | 短线活跃 | 57.4 | 中性 | neutral |
| 4 | 重组蛋白 | 69.8 | 短线活跃 | 57.4 | 中性 | neutral |
| 5 | 合成生物 | 66.8 | 短线活跃 | 53.2 | 中性 | neutral |
| 6 | 仿制药一致性评价 | 66.8 | 短线活跃 | 50.4 | 中性 | neutral |
| 7 | 肝炎概念 | 66.8 | 短线活跃 | 50.4 | 中性 | neutral |
| 8 | 阿尔茨海默概念 | 66.8 | 短线活跃 | 50.4 | 中性 | neutral |
| 9 | 工业大麻 | 66.8 | 短线活跃 | 49.2 | 降温 | burst_without_trend_confirmation |
| 10 | 辅助生殖 | 66.8 | 短线活跃 | 46.4 | 降温 | burst_without_trend_confirmation |
| 11 | 高压氧舱 | 66.8 | 短线活跃 | 36.2 | 降温 | burst_without_trend_confirmation |
| 12 | 黑龙江自贸区 | 63.8 | 短线中性 | 54.0 | 中性 | neutral |
| 13 | 动物疫苗 | 63.8 | 短线中性 | 48.2 | 降温 | neutral |
| 14 | 宠物经济 | 63.8 | 短线中性 | 44.2 | 降温 | neutral |
| 15 | 供销社 | 63.8 | 短线中性 | 43.0 | 降温 | neutral |
| 16 | 三胎概念 | 63.8 | 短线中性 | 40.2 | 降温 | neutral |
| 17 | 化肥 | 63.8 | 短线中性 | 40.2 | 降温 | neutral |
| 18 | 互联网金融 | 63.8 | 短线中性 | 36.2 | 降温 | neutral |
| 19 | 芬太尼 | 63.8 | 短线中性 | 33.4 | 偏弱 | neutral |
| 20 | 丙烯酸 | 61.8 | 短线中性 | 54.0 | 中性 | neutral |
| 21 | 光刻胶 | 58.8 | 短线中性 | 71.0 | 观察 | neutral |
| 22 | 硅能源 | 58.8 | 短线中性 | 71.0 | 观察 | neutral |
| 23 | EDR概念 | 58.8 | 短线中性 | 41.2 | 降温 | neutral |
| 24 | 华为海思概念股 | 55.8 | 短线中性 | 52.2 | 中性 | neutral |
| 25 | 超级电容 | 55.8 | 短线中性 | 52.2 | 中性 | neutral |
| 26 | 超级品牌 | 55.8 | 短线中性 | 52.0 | 中性 | neutral |
| 27 | 参股保险 | 55.8 | 短线中性 | 51.0 | 中性 | neutral |
| 28 | 共同富裕示范区 | 55.8 | 短线中性 | 47.0 | 降温 | neutral |
| 29 | 国企改革 | 55.8 | 短线中性 | 47.0 | 降温 | neutral |
| 30 | 福建自贸区 | 55.8 | 短线中性 | 47.0 | 降温 | neutral |
| 31 | 海南自贸区 | 55.8 | 短线中性 | 44.2 | 降温 | neutral |
| 32 | 军工 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 33 | 冰雪产业 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 34 | 国产航母 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 35 | 大飞机 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 36 | 工业互联网 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 37 | 核污染防治 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 38 | 白酒概念 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 39 | 股权转让(并购重组) | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 40 | 长三角一体化 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 41 | 飞行汽车(eVTOL) | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 42 | 高端装备 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 43 | 华为概念 | 55.8 | 短线中性 | 41.2 | 降温 | neutral |
| 44 | 安防 | 55.8 | 短线中性 | 41.2 | 降温 | neutral |
| 45 | 俄乌冲突概念 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 46 | 储能 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 47 | 创投 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 48 | 参股券商 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 49 | 参股银行 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 50 | 固废处理 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 51 | 地下管网 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 52 | 抽水蓄能 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 53 | 核电 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 54 | 横琴新区 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 55 | 海峡两岸 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 56 | 独角兽概念 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 57 | 电子竞技 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 58 | 短剧游戏 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 59 | 航运概念 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 60 | 超超临界发电 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 61 | 钒电池 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 62 | 风电 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 63 | 高铁 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 64 | 工业母机 | 55.8 | 短线中性 | 37.2 | 降温 | neutral |
| 65 | 车联网(车路协同) | 55.8 | 短线中性 | 37.2 | 降温 | neutral |
| 66 | ETC | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 67 | 共享单车 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 68 | 海工装备 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 69 | 航空发动机 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 70 | 锂电池概念 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 71 | 黄金概念 | 55.8 | 短线中性 | 36.0 | 降温 | neutral |
| 72 | AI语料 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 73 | ERP概念 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 74 | 东数西算(算力) | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 75 | 低空经济 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 76 | 动力电池回收 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 77 | 华为欧拉 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 78 | 华为鲲鹏 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 79 | 国产操作系统 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 80 | 国资云 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 81 | 多模态AI | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 82 | 抖音概念(字节概念) | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 83 | 比亚迪概念 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 84 | 电力物联网 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 85 | 电子身份证 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 86 | 百度概念 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 87 | 长安汽车概念 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 88 | 阿里巴巴概念 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 89 | 鸿蒙概念 | 55.8 | 短线中性 | 33.2 | 偏弱 | neutral |
| 90 | 环氧丙烷 | 55.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 91 | 金属钴 | 55.8 | 短线中性 | 28.2 | 偏弱 | neutral |
| 92 | 广东自贸区 | 52.8 | 短线中性 | 44.0 | 降温 | neutral |
| 93 | 光热发电 | 52.8 | 短线中性 | 40.0 | 降温 | neutral |
| 94 | 大豆 | 52.8 | 短线中性 | 40.0 | 降温 | neutral |
| 95 | 高股息精选 | 52.8 | 短线中性 | 40.0 | 降温 | neutral |
| 96 | 代糖概念 | 52.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 97 | 草甘膦 | 49.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 98 | 存储芯片 | 48.8 | 短线降温 | 78.0 | 观察 | trend_only |
| 99 | 光刻机 | 45.8 | 短线降温 | 75.0 | 观察 | trend_only |
| 100 | 电子纸 | 45.8 | 短线降温 | 58.2 | 中性 | neutral |
| 101 | BC电池 | 45.8 | 短线降温 | 58.0 | 中性 | neutral |
| 102 | 光伏概念 | 45.8 | 短线降温 | 41.0 | 降温 | weak_or_cooling |
| 103 | 传感器 | 45.8 | 短线降温 | 38.2 | 降温 | weak_or_cooling |
| 104 | 充电桩 | 45.8 | 短线降温 | 37.0 | 降温 | weak_or_cooling |
| 105 | 华为汽车 | 45.8 | 短线降温 | 33.0 | 偏弱 | weak_or_cooling |
| 106 | 换电概念 | 45.8 | 短线降温 | 33.0 | 偏弱 | weak_or_cooling |
| 107 | 固态电池 | 45.8 | 短线降温 | 30.2 | 偏弱 | weak_or_cooling |
| 108 | 宁德时代概念 | 45.8 | 短线降温 | 30.2 | 偏弱 | weak_or_cooling |
| 109 | 高压快充 | 45.8 | 短线降温 | 30.2 | 偏弱 | weak_or_cooling |
| 110 | 毫米波雷达 | 42.8 | 短线降温 | 30.2 | 偏弱 | weak_or_cooling |
| 111 | 成飞概念 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 112 | 国家大基金持股 | 40.3 | 短线降温 | 64.5 | 中性 | neutral |
| 113 | 第三代半导体 | 37.3 | 短线降温 | 61.2 | 中性 | neutral |
| 114 | 钙钛矿电池 | 34.3 | 短线偏弱 | 49.2 | 降温 | weak_or_cooling |
| 115 | 超导概念 | 34.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 116 | AI PC | 34.3 | 短线偏弱 | 38.5 | 降温 | weak_or_cooling |
| 117 | AI手机 | 34.3 | 短线偏弱 | 31.6 | 偏弱 | weak_or_cooling |
| 118 | 富士康概念 | 34.3 | 短线偏弱 | 30.4 | 偏弱 | weak_or_cooling |
| 119 | 共封装光学(CPO) | 31.3 | 短线偏弱 | 23.6 | 偏弱 | weak_or_cooling |
| 120 | F5G概念 | 31.3 | 短线偏弱 | 11.7 | 偏弱 | weak_or_cooling |

## 分歧板块

### 短线强但趋势未确认

| 板块 | 短线分 | 趋势分 | 说明 |
|------|--------|--------|------|
| 工业大麻 | 66.8 | 49.2 | 短线强但趋势未确认，需谨慎 |
| 辅助生殖 | 66.8 | 46.4 | 短线强但趋势未确认，需谨慎 |
| 高压氧舱 | 66.8 | 36.2 | 短线强但趋势未确认，需谨慎 |

### 趋势强但短线不热

| 板块 | 趋势分 | 短线分 | 说明 |
|------|--------|--------|------|
| 存储芯片 | 78.0 | 48.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 光刻机 | 75.0 | 45.8 | 趋势强但短线不热，中长期趋势观察价值较高 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 存储芯片

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

### 2. 光刻机

**趋势持续评分**:
- 趋势分: 75.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 15.0
  - relative_strength_component: 17.0
  - persistence_component: 20.0
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

### 3. 光刻胶

**趋势持续评分**:
- 趋势分: 71.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 17.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 2.0

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

### 4. 硅能源

**趋势持续评分**:
- 趋势分: 71.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 17.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 2.0

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

### 5. 氟化工概念

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

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
