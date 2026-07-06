# 板块综合评分

**分析日期**: 2026-06-29
**更新时间**: 2026-07-05T22:02:00.861671

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
| 1 | 国家大基金持股 | 81.2 | 重点观察 | 66.8 | 短线活跃 | trend_and_burst_aligned |
| 2 | 光刻胶 | 81.0 | 重点观察 | 52.8 | 短线中性 | neutral |
| 3 | 存储芯片 | 78.2 | 观察 | 55.8 | 短线中性 | neutral |
| 4 | 第三代半导体 | 73.0 | 观察 | 39.8 | 短线降温 | trend_only |
| 5 | 光刻机 | 64.2 | 中性 | 31.3 | 短线偏弱 | neutral |
| 6 | 超导概念 | 63.0 | 中性 | 49.8 | 短线降温 | neutral |
| 7 | 氟化工概念 | 62.2 | 中性 | 49.8 | 短线降温 | neutral |
| 8 | 动物疫苗 | 60.0 | 中性 | 49.8 | 短线降温 | neutral |
| 9 | 丙烯酸 | 57.0 | 中性 | 39.8 | 短线降温 | neutral |
| 10 | 仿制药一致性评价 | 56.5 | 中性 | 63.3 | 短线中性 | neutral |
| 11 | 创新药 | 56.5 | 中性 | 66.3 | 短线活跃 | neutral |
| 12 | 阿尔茨海默概念 | 56.2 | 中性 | 57.8 | 短线中性 | neutral |
| 13 | 猴痘概念 | 54.2 | 中性 | 57.8 | 短线中性 | neutral |
| 14 | 肝炎概念 | 54.2 | 中性 | 57.8 | 短线中性 | neutral |
| 15 | 辅助生殖 | 54.2 | 中性 | 57.8 | 短线中性 | neutral |
| 16 | 合成生物 | 54.0 | 中性 | 57.8 | 短线中性 | neutral |
| 17 | 华为海思概念股 | 52.5 | 中性 | 25.3 | 短线偏弱 | neutral |
| 18 | AI PC | 50.5 | 中性 | 25.3 | 短线偏弱 | neutral |
| 19 | 电子纸 | 50.5 | 中性 | 21.3 | 短线偏弱 | neutral |
| 20 | 超级电容 | 50.5 | 中性 | 28.3 | 短线偏弱 | neutral |
| 21 | 东数西算(算力) | 49.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 22 | 高压氧舱 | 49.0 | 降温 | 46.8 | 短线降温 | weak_or_cooling |
| 23 | 重组蛋白 | 48.6 | 降温 | 64.3 | 短线中性 | neutral |
| 24 | 传感器 | 48.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 25 | 硅能源 | 48.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 26 | 钙钛矿电池 | 48.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 27 | 工业大麻 | 48.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 28 | AI手机 | 46.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 29 | 宁德时代概念 | 46.5 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 30 | 富士康概念 | 46.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 31 | 环氧丙烷 | 46.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 32 | 宠物经济 | 46.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 33 | 共封装光学(CPO) | 45.6 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 34 | EDR概念 | 44.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 35 | 军工 | 44.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 36 | 华为概念 | 44.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 37 | 核污染防治 | 44.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 38 | 比亚迪概念 | 44.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 39 | 高股息精选 | 43.8 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 40 | 白酒概念 | 43.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 41 | 福建自贸区 | 43.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 42 | 航运概念 | 43.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 43 | 光伏概念 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 44 | 大飞机 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 45 | 安防 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 46 | 工业互联网 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 47 | 车联网(车路协同) | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 48 | 锂电池概念 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 49 | 长三角一体化 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 50 | 高压快充 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 51 | 参股券商 | 42.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 52 | 海南自贸区 | 42.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 53 | BC电池 | 41.5 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 54 | 固态电池 | 41.5 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 55 | 毫米波雷达 | 41.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 56 | ETC | 41.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 57 | 国产操作系统 | 41.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 58 | 芬太尼 | 41.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 59 | 超级品牌 | 41.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 60 | 供销社 | 40.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 61 | 共同富裕示范区 | 40.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 62 | 参股银行 | 40.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 63 | 国企改革 | 40.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 64 | 黑龙江自贸区 | 40.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 65 | F5G概念 | 39.6 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 66 | 低空经济 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 67 | 多模态AI | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 68 | 广东自贸区 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 69 | 成飞概念 | 39.2 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 70 | 抖音概念(字节概念) | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 71 | 换电概念 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 72 | 独角兽概念 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 73 | 百度概念 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 74 | 股权转让(并购重组) | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 75 | 航空发动机 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 76 | 阿里巴巴概念 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 77 | 鸿蒙概念 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 78 | 三胎概念 | 38.0 | 降温 | 46.8 | 短线降温 | weak_or_cooling |
| 79 | 储能 | 37.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 80 | 充电桩 | 37.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 81 | 工业母机 | 37.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 82 | 核电 | 37.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 83 | 海峡两岸 | 37.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 84 | 飞行汽车(eVTOL) | 37.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 85 | 高端装备 | 37.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 86 | 华为鲲鹏 | 36.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 87 | 固废处理 | 36.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 88 | 电子身份证 | 36.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 89 | 冰雪产业 | 36.0 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 90 | 黄金概念 | 35.2 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 91 | 俄乌冲突概念 | 35.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 92 | 化肥 | 35.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 93 | 参股保险 | 35.0 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 94 | 创投 | 34.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 95 | 横琴新区 | 34.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 96 | 海工装备 | 34.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 97 | 电力物联网 | 34.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 98 | 电子竞技 | 34.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 99 | 钒电池 | 34.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 100 | 风电 | 34.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 101 | 高铁 | 34.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 102 | 华为欧拉 | 32.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 103 | 华为汽车 | 32.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 104 | 长安汽车概念 | 32.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 105 | 动力电池回收 | 31.4 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 106 | 互联网金融 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 107 | 共享单车 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 108 | 国资云 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 109 | 抽水蓄能 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 110 | 短剧游戏 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 111 | 草甘膦 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 112 | 金属钴 | 29.6 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 113 | AI语料 | 29.4 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 114 | ERP概念 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 115 | 国产航母 | 29.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 116 | 大豆 | 29.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 117 | 超超临界发电 | 28.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 118 | 光热发电 | 26.1 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 119 | 代糖概念 | 25.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 120 | 地下管网 | 21.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 120

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 国家大基金持股 | 66.8 | 短线活跃 | 81.2 | 重点观察 | trend_and_burst_aligned |
| 2 | 创新药 | 66.3 | 短线活跃 | 56.5 | 中性 | neutral |
| 3 | 重组蛋白 | 64.3 | 短线中性 | 48.6 | 降温 | neutral |
| 4 | 仿制药一致性评价 | 63.3 | 短线中性 | 56.5 | 中性 | neutral |
| 5 | 阿尔茨海默概念 | 57.8 | 短线中性 | 56.2 | 中性 | neutral |
| 6 | 猴痘概念 | 57.8 | 短线中性 | 54.2 | 中性 | neutral |
| 7 | 肝炎概念 | 57.8 | 短线中性 | 54.2 | 中性 | neutral |
| 8 | 辅助生殖 | 57.8 | 短线中性 | 54.2 | 中性 | neutral |
| 9 | 合成生物 | 57.8 | 短线中性 | 54.0 | 中性 | neutral |
| 10 | 存储芯片 | 55.8 | 短线中性 | 78.2 | 观察 | neutral |
| 11 | 光刻胶 | 52.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 12 | 超导概念 | 49.8 | 短线降温 | 63.0 | 中性 | neutral |
| 13 | 氟化工概念 | 49.8 | 短线降温 | 62.2 | 中性 | neutral |
| 14 | 动物疫苗 | 49.8 | 短线降温 | 60.0 | 中性 | neutral |
| 15 | 工业大麻 | 49.8 | 短线降温 | 48.0 | 降温 | weak_or_cooling |
| 16 | 宠物经济 | 49.8 | 短线降温 | 46.0 | 降温 | weak_or_cooling |
| 17 | 高股息精选 | 49.8 | 短线降温 | 43.8 | 降温 | weak_or_cooling |
| 18 | 白酒概念 | 49.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 19 | 芬太尼 | 49.8 | 短线降温 | 41.0 | 降温 | weak_or_cooling |
| 20 | 超级品牌 | 49.8 | 短线降温 | 41.0 | 降温 | weak_or_cooling |
| 21 | 高压氧舱 | 46.8 | 短线降温 | 49.0 | 降温 | weak_or_cooling |
| 22 | 三胎概念 | 46.8 | 短线降温 | 38.0 | 降温 | weak_or_cooling |
| 23 | 第三代半导体 | 39.8 | 短线降温 | 73.0 | 观察 | trend_only |
| 24 | 丙烯酸 | 39.8 | 短线降温 | 57.0 | 中性 | neutral |
| 25 | 冰雪产业 | 39.8 | 短线降温 | 36.0 | 降温 | weak_or_cooling |
| 26 | 大豆 | 39.8 | 短线降温 | 29.0 | 偏弱 | weak_or_cooling |
| 27 | 福建自贸区 | 36.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 28 | 航运概念 | 36.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 29 | 参股券商 | 36.8 | 短线降温 | 42.0 | 降温 | weak_or_cooling |
| 30 | 海南自贸区 | 36.8 | 短线降温 | 42.0 | 降温 | weak_or_cooling |
| 31 | 供销社 | 36.8 | 短线降温 | 40.0 | 降温 | weak_or_cooling |
| 32 | 共同富裕示范区 | 36.8 | 短线降温 | 40.0 | 降温 | weak_or_cooling |
| 33 | 参股银行 | 36.8 | 短线降温 | 40.0 | 降温 | weak_or_cooling |
| 34 | 国企改革 | 36.8 | 短线降温 | 40.0 | 降温 | weak_or_cooling |
| 35 | 黑龙江自贸区 | 36.8 | 短线降温 | 40.0 | 降温 | weak_or_cooling |
| 36 | 黄金概念 | 36.8 | 短线降温 | 35.2 | 降温 | weak_or_cooling |
| 37 | 俄乌冲突概念 | 36.8 | 短线降温 | 35.0 | 降温 | weak_or_cooling |
| 38 | 化肥 | 36.8 | 短线降温 | 35.0 | 降温 | weak_or_cooling |
| 39 | 参股保险 | 36.8 | 短线降温 | 35.0 | 降温 | weak_or_cooling |
| 40 | 超超临界发电 | 36.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 41 | 光刻机 | 31.3 | 短线偏弱 | 64.2 | 中性 | neutral |
| 42 | 超级电容 | 28.3 | 短线偏弱 | 50.5 | 中性 | neutral |
| 43 | 硅能源 | 28.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 44 | 钙钛矿电池 | 28.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 45 | BC电池 | 28.3 | 短线偏弱 | 41.5 | 降温 | weak_or_cooling |
| 46 | 华为海思概念股 | 25.3 | 短线偏弱 | 52.5 | 中性 | neutral |
| 47 | AI PC | 25.3 | 短线偏弱 | 50.5 | 中性 | neutral |
| 48 | 东数西算(算力) | 25.3 | 短线偏弱 | 49.2 | 降温 | weak_or_cooling |
| 49 | 传感器 | 25.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 50 | 宁德时代概念 | 25.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 51 | 环氧丙烷 | 25.3 | 短线偏弱 | 46.2 | 降温 | weak_or_cooling |
| 52 | EDR概念 | 25.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 53 | 军工 | 25.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 54 | 华为概念 | 25.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 55 | 核污染防治 | 25.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 56 | 比亚迪概念 | 25.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 57 | 光伏概念 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 58 | 大飞机 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 59 | 安防 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 60 | 工业互联网 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 61 | 车联网(车路协同) | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 62 | 锂电池概念 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 63 | 长三角一体化 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 64 | 高压快充 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 65 | 固态电池 | 25.3 | 短线偏弱 | 41.5 | 降温 | weak_or_cooling |
| 66 | ETC | 25.3 | 短线偏弱 | 41.2 | 降温 | weak_or_cooling |
| 67 | 国产操作系统 | 25.3 | 短线偏弱 | 41.2 | 降温 | weak_or_cooling |
| 68 | 低空经济 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 69 | 多模态AI | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 70 | 广东自贸区 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 71 | 抖音概念(字节概念) | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 72 | 换电概念 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 73 | 独角兽概念 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 74 | 百度概念 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 75 | 股权转让(并购重组) | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 76 | 航空发动机 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 77 | 阿里巴巴概念 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 78 | 鸿蒙概念 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 79 | 储能 | 25.3 | 短线偏弱 | 37.2 | 降温 | weak_or_cooling |
| 80 | 充电桩 | 25.3 | 短线偏弱 | 37.2 | 降温 | weak_or_cooling |
| 81 | 工业母机 | 25.3 | 短线偏弱 | 37.2 | 降温 | weak_or_cooling |
| 82 | 核电 | 25.3 | 短线偏弱 | 37.2 | 降温 | weak_or_cooling |
| 83 | 海峡两岸 | 25.3 | 短线偏弱 | 37.2 | 降温 | weak_or_cooling |
| 84 | 飞行汽车(eVTOL) | 25.3 | 短线偏弱 | 37.2 | 降温 | weak_or_cooling |
| 85 | 高端装备 | 25.3 | 短线偏弱 | 37.2 | 降温 | weak_or_cooling |
| 86 | 华为鲲鹏 | 25.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 87 | 固废处理 | 25.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 88 | 电子身份证 | 25.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 89 | 创投 | 25.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |
| 90 | 横琴新区 | 25.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |
| 91 | 海工装备 | 25.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |
| 92 | 电力物联网 | 25.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |
| 93 | 电子竞技 | 25.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |
| 94 | 钒电池 | 25.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |
| 95 | 风电 | 25.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |
| 96 | 高铁 | 25.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |
| 97 | 华为欧拉 | 25.3 | 短线偏弱 | 32.2 | 偏弱 | weak_or_cooling |
| 98 | 华为汽车 | 25.3 | 短线偏弱 | 32.2 | 偏弱 | weak_or_cooling |
| 99 | 长安汽车概念 | 25.3 | 短线偏弱 | 32.2 | 偏弱 | weak_or_cooling |
| 100 | 动力电池回收 | 25.3 | 短线偏弱 | 31.4 | 偏弱 | weak_or_cooling |
| 101 | 互联网金融 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 102 | 共享单车 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 103 | 国资云 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 104 | 抽水蓄能 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 105 | 短剧游戏 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 106 | 草甘膦 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 107 | 金属钴 | 25.3 | 短线偏弱 | 29.6 | 偏弱 | weak_or_cooling |
| 108 | AI语料 | 25.3 | 短线偏弱 | 29.4 | 偏弱 | weak_or_cooling |
| 109 | ERP概念 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 110 | 国产航母 | 25.3 | 短线偏弱 | 29.2 | 偏弱 | weak_or_cooling |
| 111 | 光热发电 | 25.3 | 短线偏弱 | 26.1 | 偏弱 | weak_or_cooling |
| 112 | 代糖概念 | 25.3 | 短线偏弱 | 25.2 | 偏弱 | weak_or_cooling |
| 113 | 地下管网 | 25.3 | 短线偏弱 | 21.2 | 偏弱 | weak_or_cooling |
| 114 | 电子纸 | 21.3 | 短线偏弱 | 50.5 | 中性 | neutral |
| 115 | AI手机 | 21.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 116 | 富士康概念 | 21.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 117 | 共封装光学(CPO) | 21.3 | 短线偏弱 | 45.6 | 降温 | weak_or_cooling |
| 118 | 毫米波雷达 | 21.3 | 短线偏弱 | 41.5 | 降温 | weak_or_cooling |
| 119 | F5G概念 | 21.3 | 短线偏弱 | 39.6 | 降温 | weak_or_cooling |
| 120 | 成飞概念 | 21.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |

## 分歧板块

### 趋势强但短线不热

| 板块 | 趋势分 | 短线分 | 说明 |
|------|--------|--------|------|
| 第三代半导体 | 73.0 | 39.8 | 趋势强但短线不热，中长期趋势观察价值较高 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 国家大基金持股

**趋势持续评分**:
- 趋势分: 81.2
- 趋势等级: 重点观察
- 趋势 breakdown:
  - radar_score_component: 11.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 2.0

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

### 2. 光刻胶

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

### 3. 存储芯片

**趋势持续评分**:
- 趋势分: 78.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 2.4
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

### 4. 第三代半导体

**趋势持续评分**:
- 趋势分: 73.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 0.0

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
- 趋势分: 64.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 8.0
  - volatility_component: 3.2
  - data_quality_component: 6.4
  - risk_penalty: 0.0

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
