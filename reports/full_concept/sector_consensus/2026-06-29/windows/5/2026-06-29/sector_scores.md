# 板块综合评分

**分析日期**: 2026-06-29
**更新时间**: 2026-07-05T22:02:00.825532

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。

## 数据来源

- **板块类型**: concept
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
| 1 | 国家大基金持股 | 74.2 | 观察 | 66.8 | 短线活跃 | trend_and_burst_aligned |
| 2 | 存储芯片 | 71.2 | 观察 | 55.8 | 短线中性 | neutral |
| 3 | 光刻胶 | 69.0 | 观察 | 52.8 | 短线中性 | neutral |
| 4 | 第三代半导体 | 66.0 | 观察 | 39.8 | 短线降温 | trend_only |
| 5 | 光刻机 | 62.2 | 中性 | 31.3 | 短线偏弱 | neutral |
| 6 | 重组蛋白 | 58.6 | 中性 | 69.3 | 短线活跃 | neutral |
| 7 | 氟化工概念 | 58.0 | 中性 | 49.8 | 短线降温 | neutral |
| 8 | 仿制药一致性评价 | 53.6 | 中性 | 63.3 | 短线中性 | neutral |
| 9 | 创新药 | 53.6 | 中性 | 66.3 | 短线活跃 | neutral |
| 10 | 超导概念 | 53.2 | 中性 | 49.8 | 短线降温 | neutral |
| 11 | 动物疫苗 | 53.0 | 中性 | 49.8 | 短线降温 | neutral |
| 12 | 超级品牌 | 53.0 | 中性 | 49.8 | 短线降温 | neutral |
| 13 | 猴痘概念 | 51.4 | 中性 | 57.8 | 短线中性 | neutral |
| 14 | 肝炎概念 | 51.4 | 中性 | 57.8 | 短线中性 | neutral |
| 15 | 辅助生殖 | 51.4 | 中性 | 57.8 | 短线中性 | neutral |
| 16 | 阿尔茨海默概念 | 51.4 | 中性 | 57.8 | 短线中性 | neutral |
| 17 | 高股息精选 | 50.0 | 中性 | 49.8 | 短线降温 | neutral |
| 18 | 合成生物 | 49.2 | 降温 | 57.8 | 短线中性 | neutral |
| 19 | 芬太尼 | 49.2 | 降温 | 54.8 | 短线中性 | neutral |
| 20 | 工业大麻 | 49.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 21 | 丙烯酸 | 47.8 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 22 | 高压氧舱 | 46.2 | 降温 | 46.8 | 短线降温 | weak_or_cooling |
| 23 | 三胎概念 | 46.0 | 降温 | 46.8 | 短线降温 | weak_or_cooling |
| 24 | 宠物经济 | 46.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 25 | 白酒概念 | 46.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 26 | AI PC | 43.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 27 | 华为海思概念股 | 43.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 28 | 电子纸 | 43.2 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 29 | 供销社 | 43.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 30 | 冰雪产业 | 43.0 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 31 | 参股银行 | 43.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 32 | 航运概念 | 43.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 33 | 黑龙江自贸区 | 43.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 34 | 超级电容 | 40.5 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 35 | 共同富裕示范区 | 40.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 36 | 参股券商 | 40.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 37 | 海南自贸区 | 40.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 38 | AI手机 | 39.2 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 39 | 富士康概念 | 39.2 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 40 | 传感器 | 37.0 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 41 | 钙钛矿电池 | 37.0 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 42 | 长三角一体化 | 37.0 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 43 | 共封装光学(CPO) | 36.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 44 | 环氧丙烷 | 36.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 45 | 硅能源 | 36.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 46 | 俄乌冲突概念 | 33.8 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 47 | 化肥 | 33.8 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 48 | 国企改革 | 33.8 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 49 | 参股保险 | 33.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 50 | 大豆 | 33.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 51 | 福建自贸区 | 33.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 52 | 广东自贸区 | 32.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 53 | 股权转让(并购重组) | 30.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 54 | 草甘膦 | 30.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 55 | BC电池 | 29.2 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 56 | EDR概念 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 57 | 固废处理 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 58 | 地下管网 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 59 | 宁德时代概念 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 60 | 成飞概念 | 29.2 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 61 | 横琴新区 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 62 | ETC | 26.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 63 | 超超临界发电 | 25.8 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 64 | 东数西算(算力) | 25.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 65 | 固态电池 | 25.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 66 | 毫米波雷达 | 25.2 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 67 | 代糖概念 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 68 | 低空经济 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 69 | 储能 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 70 | 充电桩 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 71 | 光伏概念 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 72 | 光热发电 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 73 | 军工 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 74 | 创投 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 75 | 华为概念 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 76 | 华为汽车 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 77 | 大飞机 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 78 | 安防 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 79 | 工业互联网 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 80 | 核污染防治 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 81 | 核电 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 82 | 海峡两岸 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 83 | 海工装备 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 84 | 电子竞技 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 85 | 车联网(车路协同) | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 86 | 钒电池 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 87 | 飞行汽车(eVTOL) | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 88 | 高端装备 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 89 | 高铁 | 25.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 90 | 黄金概念 | 25.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 91 | 比亚迪概念 | 24.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 92 | 独角兽概念 | 24.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 93 | 锂电池概念 | 24.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 94 | 国产航母 | 21.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 95 | 抽水蓄能 | 21.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 96 | 航空发动机 | 21.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 97 | 长安汽车概念 | 21.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 98 | 风电 | 21.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 99 | 高压快充 | 21.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 100 | 共享单车 | 20.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 101 | 工业母机 | 20.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 102 | 国产操作系统 | 17.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 103 | 抖音概念(字节概念) | 17.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 104 | 换电概念 | 17.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 105 | 电力物联网 | 17.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 106 | 百度概念 | 17.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 107 | 短剧游戏 | 17.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 108 | ERP概念 | 16.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 109 | 互联网金融 | 16.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 110 | 国资云 | 16.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 111 | 多模态AI | 16.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 112 | 阿里巴巴概念 | 16.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 113 | 鸿蒙概念 | 16.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 114 | 动力电池回收 | 11.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 115 | 电子身份证 | 11.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 116 | F5G概念 | 8.2 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 117 | 华为鲲鹏 | 7.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 118 | AI语料 | 3.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 119 | 华为欧拉 | 3.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 120 | 金属钴 | 0.5 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 120

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 重组蛋白 | 69.3 | 短线活跃 | 58.6 | 中性 | neutral |
| 2 | 国家大基金持股 | 66.8 | 短线活跃 | 74.2 | 观察 | trend_and_burst_aligned |
| 3 | 创新药 | 66.3 | 短线活跃 | 53.6 | 中性 | neutral |
| 4 | 仿制药一致性评价 | 63.3 | 短线中性 | 53.6 | 中性 | neutral |
| 5 | 猴痘概念 | 57.8 | 短线中性 | 51.4 | 中性 | neutral |
| 6 | 肝炎概念 | 57.8 | 短线中性 | 51.4 | 中性 | neutral |
| 7 | 辅助生殖 | 57.8 | 短线中性 | 51.4 | 中性 | neutral |
| 8 | 阿尔茨海默概念 | 57.8 | 短线中性 | 51.4 | 中性 | neutral |
| 9 | 合成生物 | 57.8 | 短线中性 | 49.2 | 降温 | neutral |
| 10 | 存储芯片 | 55.8 | 短线中性 | 71.2 | 观察 | neutral |
| 11 | 芬太尼 | 54.8 | 短线中性 | 49.2 | 降温 | neutral |
| 12 | 光刻胶 | 52.8 | 短线中性 | 69.0 | 观察 | neutral |
| 13 | 氟化工概念 | 49.8 | 短线降温 | 58.0 | 中性 | neutral |
| 14 | 超导概念 | 49.8 | 短线降温 | 53.2 | 中性 | neutral |
| 15 | 动物疫苗 | 49.8 | 短线降温 | 53.0 | 中性 | neutral |
| 16 | 超级品牌 | 49.8 | 短线降温 | 53.0 | 中性 | neutral |
| 17 | 高股息精选 | 49.8 | 短线降温 | 50.0 | 中性 | neutral |
| 18 | 工业大麻 | 49.8 | 短线降温 | 49.0 | 降温 | weak_or_cooling |
| 19 | 宠物经济 | 49.8 | 短线降温 | 46.0 | 降温 | weak_or_cooling |
| 20 | 白酒概念 | 49.8 | 短线降温 | 46.0 | 降温 | weak_or_cooling |
| 21 | 高压氧舱 | 46.8 | 短线降温 | 46.2 | 降温 | weak_or_cooling |
| 22 | 三胎概念 | 46.8 | 短线降温 | 46.0 | 降温 | weak_or_cooling |
| 23 | 第三代半导体 | 39.8 | 短线降温 | 66.0 | 观察 | trend_only |
| 24 | 丙烯酸 | 39.8 | 短线降温 | 47.8 | 降温 | weak_or_cooling |
| 25 | 冰雪产业 | 39.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 26 | 大豆 | 39.8 | 短线降温 | 33.0 | 偏弱 | weak_or_cooling |
| 27 | 供销社 | 36.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 28 | 参股银行 | 36.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 29 | 航运概念 | 36.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 30 | 黑龙江自贸区 | 36.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 31 | 共同富裕示范区 | 36.8 | 短线降温 | 40.0 | 降温 | weak_or_cooling |
| 32 | 参股券商 | 36.8 | 短线降温 | 40.0 | 降温 | weak_or_cooling |
| 33 | 海南自贸区 | 36.8 | 短线降温 | 40.0 | 降温 | weak_or_cooling |
| 34 | 俄乌冲突概念 | 36.8 | 短线降温 | 33.8 | 偏弱 | weak_or_cooling |
| 35 | 化肥 | 36.8 | 短线降温 | 33.8 | 偏弱 | weak_or_cooling |
| 36 | 国企改革 | 36.8 | 短线降温 | 33.8 | 偏弱 | weak_or_cooling |
| 37 | 参股保险 | 36.8 | 短线降温 | 33.0 | 偏弱 | weak_or_cooling |
| 38 | 福建自贸区 | 36.8 | 短线降温 | 33.0 | 偏弱 | weak_or_cooling |
| 39 | 超超临界发电 | 36.8 | 短线降温 | 25.8 | 偏弱 | weak_or_cooling |
| 40 | 黄金概念 | 36.8 | 短线降温 | 25.0 | 偏弱 | weak_or_cooling |
| 41 | 光刻机 | 31.3 | 短线偏弱 | 62.2 | 中性 | neutral |
| 42 | 超级电容 | 28.3 | 短线偏弱 | 40.5 | 降温 | weak_or_cooling |
| 43 | 钙钛矿电池 | 28.3 | 短线偏弱 | 37.0 | 降温 | weak_or_cooling |
| 44 | 硅能源 | 28.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 45 | BC电池 | 28.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 46 | AI PC | 25.3 | 短线偏弱 | 43.2 | 降温 | weak_or_cooling |
| 47 | 华为海思概念股 | 25.3 | 短线偏弱 | 43.2 | 降温 | weak_or_cooling |
| 48 | 传感器 | 25.3 | 短线偏弱 | 37.0 | 降温 | weak_or_cooling |
| 49 | 长三角一体化 | 25.3 | 短线偏弱 | 37.0 | 降温 | weak_or_cooling |
| 50 | 环氧丙烷 | 25.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 51 | 广东自贸区 | 25.3 | 短线偏弱 | 32.2 | 偏弱 | weak_or_cooling |
| 52 | 股权转让(并购重组) | 25.3 | 短线偏弱 | 30.1 | 偏弱 | weak_or_cooling |
| 53 | 草甘膦 | 25.3 | 短线偏弱 | 30.1 | 偏弱 | weak_or_cooling |
| 54 | EDR概念 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 55 | 固废处理 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 56 | 地下管网 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 57 | 宁德时代概念 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 58 | 横琴新区 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 59 | ETC | 25.3 | 短线偏弱 | 26.1 | 偏弱 | weak_or_cooling |
| 60 | 东数西算(算力) | 25.3 | 短线偏弱 | 25.2 | 偏弱 | weak_or_cooling |
| 61 | 固态电池 | 25.3 | 短线偏弱 | 25.2 | 偏弱 | weak_or_cooling |
| 62 | 代糖概念 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 63 | 低空经济 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 64 | 储能 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 65 | 充电桩 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 66 | 光伏概念 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 67 | 光热发电 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 68 | 军工 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 69 | 创投 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 70 | 华为概念 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 71 | 华为汽车 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 72 | 大飞机 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 73 | 安防 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 74 | 工业互联网 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 75 | 核污染防治 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 76 | 核电 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 77 | 海峡两岸 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 78 | 海工装备 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 79 | 电子竞技 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 80 | 车联网(车路协同) | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 81 | 钒电池 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 82 | 飞行汽车(eVTOL) | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 83 | 高端装备 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 84 | 高铁 | 25.3 | 短线偏弱 | 25.1 | 偏弱 | weak_or_cooling |
| 85 | 比亚迪概念 | 25.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 86 | 独角兽概念 | 25.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 87 | 锂电池概念 | 25.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 88 | 国产航母 | 25.3 | 短线偏弱 | 21.1 | 偏弱 | weak_or_cooling |
| 89 | 抽水蓄能 | 25.3 | 短线偏弱 | 21.1 | 偏弱 | weak_or_cooling |
| 90 | 航空发动机 | 25.3 | 短线偏弱 | 21.1 | 偏弱 | weak_or_cooling |
| 91 | 长安汽车概念 | 25.3 | 短线偏弱 | 21.1 | 偏弱 | weak_or_cooling |
| 92 | 风电 | 25.3 | 短线偏弱 | 21.1 | 偏弱 | weak_or_cooling |
| 93 | 高压快充 | 25.3 | 短线偏弱 | 21.1 | 偏弱 | weak_or_cooling |
| 94 | 共享单车 | 25.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 95 | 工业母机 | 25.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 96 | 国产操作系统 | 25.3 | 短线偏弱 | 17.1 | 偏弱 | weak_or_cooling |
| 97 | 抖音概念(字节概念) | 25.3 | 短线偏弱 | 17.1 | 偏弱 | weak_or_cooling |
| 98 | 换电概念 | 25.3 | 短线偏弱 | 17.1 | 偏弱 | weak_or_cooling |
| 99 | 电力物联网 | 25.3 | 短线偏弱 | 17.1 | 偏弱 | weak_or_cooling |
| 100 | 百度概念 | 25.3 | 短线偏弱 | 17.1 | 偏弱 | weak_or_cooling |
| 101 | 短剧游戏 | 25.3 | 短线偏弱 | 17.1 | 偏弱 | weak_or_cooling |
| 102 | ERP概念 | 25.3 | 短线偏弱 | 16.2 | 偏弱 | weak_or_cooling |
| 103 | 互联网金融 | 25.3 | 短线偏弱 | 16.2 | 偏弱 | weak_or_cooling |
| 104 | 国资云 | 25.3 | 短线偏弱 | 16.2 | 偏弱 | weak_or_cooling |
| 105 | 多模态AI | 25.3 | 短线偏弱 | 16.2 | 偏弱 | weak_or_cooling |
| 106 | 阿里巴巴概念 | 25.3 | 短线偏弱 | 16.2 | 偏弱 | weak_or_cooling |
| 107 | 鸿蒙概念 | 25.3 | 短线偏弱 | 16.2 | 偏弱 | weak_or_cooling |
| 108 | 动力电池回收 | 25.3 | 短线偏弱 | 11.2 | 偏弱 | weak_or_cooling |
| 109 | 电子身份证 | 25.3 | 短线偏弱 | 11.2 | 偏弱 | weak_or_cooling |
| 110 | 华为鲲鹏 | 25.3 | 短线偏弱 | 7.2 | 偏弱 | weak_or_cooling |
| 111 | AI语料 | 25.3 | 短线偏弱 | 3.2 | 偏弱 | weak_or_cooling |
| 112 | 华为欧拉 | 25.3 | 短线偏弱 | 3.2 | 偏弱 | weak_or_cooling |
| 113 | 金属钴 | 25.3 | 短线偏弱 | 0.5 | 偏弱 | weak_or_cooling |
| 114 | 电子纸 | 21.3 | 短线偏弱 | 43.2 | 降温 | weak_or_cooling |
| 115 | AI手机 | 21.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 116 | 富士康概念 | 21.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 117 | 共封装光学(CPO) | 21.3 | 短线偏弱 | 36.5 | 降温 | weak_or_cooling |
| 118 | 成飞概念 | 21.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 119 | 毫米波雷达 | 21.3 | 短线偏弱 | 25.2 | 偏弱 | weak_or_cooling |
| 120 | F5G概念 | 21.3 | 短线偏弱 | 8.2 | 偏弱 | weak_or_cooling |

## 分歧板块

### 趋势强但短线不热

| 板块 | 趋势分 | 短线分 | 说明 |
|------|--------|--------|------|
| 第三代半导体 | 66.0 | 39.8 | 趋势强但短线不热，中长期趋势观察价值较高 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 国家大基金持股

**趋势持续评分**:
- 趋势分: 74.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 11.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 4.0

**短线爆发评分**:
- 短线分: 66.8
- 短线等级: 短线活跃
- 短线 breakdown:
  - radar_today_component: 22.8
  - one_day_change_component: 16.0
  - three_day_momentum_component: 12.0
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

### 2. 存储芯片

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

### 3. 光刻胶

**趋势持续评分**:
- 趋势分: 69.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 2.0

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

### 4. 第三代半导体

**趋势持续评分**:
- 趋势分: 66.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 2.0

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
- Profile: trend_only
- Summary: 趋势强但短线不热，中长期趋势观察价值较高
- Watch points:
  - 趋势持续性好，但短线缺乏爆发力
  - 观察是否有催化剂推动短线表现

### 5. 光刻机

**趋势持续评分**:
- 趋势分: 62.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 2.0

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
