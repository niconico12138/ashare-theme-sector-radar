# 板块综合评分

**分析日期**: 2026-06-29
**更新时间**: 2026-07-05T22:02:00.896704

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
| 1 | 光刻胶 | 69.2 | 观察 | 52.8 | 短线中性 | neutral |
| 2 | 国家大基金持股 | 68.2 | 观察 | 66.8 | 短线活跃 | trend_and_burst_aligned |
| 3 | 存储芯片 | 63.2 | 中性 | 55.8 | 短线中性 | neutral |
| 4 | 超导概念 | 61.0 | 中性 | 49.8 | 短线降温 | neutral |
| 5 | 光刻机 | 60.5 | 中性 | 31.3 | 短线偏弱 | neutral |
| 6 | 氟化工概念 | 60.0 | 中性 | 49.8 | 短线降温 | neutral |
| 7 | 动物疫苗 | 56.0 | 中性 | 49.8 | 短线降温 | neutral |
| 8 | 第三代半导体 | 55.2 | 中性 | 39.8 | 短线降温 | neutral |
| 9 | 阿尔茨海默概念 | 54.0 | 中性 | 57.8 | 短线中性 | neutral |
| 10 | 硅能源 | 53.2 | 中性 | 28.3 | 短线偏弱 | neutral |
| 11 | 重组蛋白 | 51.5 | 中性 | 64.3 | 短线中性 | neutral |
| 12 | 创新药 | 48.5 | 降温 | 61.3 | 短线中性 | neutral |
| 13 | 传感器 | 48.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 14 | AI手机 | 46.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 15 | 华为海思概念股 | 46.5 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 16 | 富士康概念 | 46.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 17 | 电子纸 | 46.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 18 | 钙钛矿电池 | 46.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 19 | 合成生物 | 46.0 | 降温 | 57.8 | 短线中性 | neutral |
| 20 | 丙烯酸 | 45.0 | 降温 | 39.8 | 短线降温 | weak_or_cooling |
| 21 | AI PC | 44.5 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 22 | 超级电容 | 44.5 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 23 | 宁德时代概念 | 44.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 24 | 毫米波雷达 | 44.2 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 25 | 辅助生殖 | 44.0 | 降温 | 52.8 | 短线中性 | neutral |
| 26 | 共封装光学(CPO) | 43.6 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 27 | BC电池 | 42.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 28 | 光伏概念 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 29 | 固态电池 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 30 | 工业母机 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 31 | 核污染防治 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 32 | 环氧丙烷 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 33 | 航空发动机 | 42.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 34 | 猴痘概念 | 42.0 | 降温 | 52.8 | 短线中性 | neutral |
| 35 | 仿制药一致性评价 | 39.2 | 降温 | 58.3 | 短线中性 | neutral |
| 36 | 军工 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 37 | 大飞机 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 38 | 比亚迪概念 | 39.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 39 | F5G概念 | 37.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 40 | 锂电池概念 | 37.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 41 | 芬太尼 | 37.0 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 42 | 东数西算(算力) | 36.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 43 | 华为概念 | 36.2 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 44 | 成飞概念 | 34.2 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 45 | 肝炎概念 | 33.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 46 | 金属钴 | 32.5 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 47 | 黄金概念 | 32.2 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 48 | 低空经济 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 49 | 安防 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 50 | 核电 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 51 | 海峡两岸 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 52 | 长三角一体化 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 53 | 飞行汽车(eVTOL) | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 54 | 高端装备 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 55 | 高铁 | 31.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 56 | 工业大麻 | 31.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 57 | 高压氧舱 | 30.0 | 偏弱 | 46.8 | 短线降温 | weak_or_cooling |
| 58 | 草甘膦 | 28.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 59 | EDR概念 | 27.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 60 | 华为汽车 | 27.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 61 | 股权转让(并购重组) | 27.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 62 | 高压快充 | 27.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 63 | 俄乌冲突概念 | 27.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 64 | 福建自贸区 | 27.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 65 | 超级品牌 | 26.8 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 66 | 高股息精选 | 26.8 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 67 | 宠物经济 | 26.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 68 | 冰雪产业 | 24.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 69 | 海南自贸区 | 24.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 70 | 创投 | 23.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 71 | 国产航母 | 23.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 72 | 工业互联网 | 23.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 73 | 海工装备 | 23.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 74 | 车联网(车路协同) | 23.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 75 | 三胎概念 | 22.0 | 偏弱 | 46.8 | 短线降温 | weak_or_cooling |
| 76 | 储能 | 21.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 77 | 充电桩 | 21.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 78 | 动力电池回收 | 21.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 79 | 钒电池 | 21.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 80 | 长安汽车概念 | 21.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 81 | ETC | 20.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 82 | 国产操作系统 | 20.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 83 | 供销社 | 19.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 84 | 共同富裕示范区 | 19.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 85 | 化肥 | 19.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 86 | 参股券商 | 19.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 87 | 参股银行 | 19.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 88 | 国企改革 | 19.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 89 | 航运概念 | 19.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 90 | 黑龙江自贸区 | 19.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 91 | 白酒概念 | 18.0 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 92 | 参股保险 | 17.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 93 | 大豆 | 17.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 94 | AI语料 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 95 | 互联网金融 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 96 | 代糖概念 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 97 | 共享单车 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 98 | 华为欧拉 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 99 | 华为鲲鹏 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 100 | 固废处理 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 101 | 多模态AI | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 102 | 广东自贸区 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 103 | 抖音概念(字节概念) | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 104 | 抽水蓄能 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 105 | 换电概念 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 106 | 横琴新区 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 107 | 独角兽概念 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 108 | 电子竞技 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 109 | 电子身份证 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 110 | 百度概念 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 111 | 阿里巴巴概念 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 112 | 风电 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 113 | 鸿蒙概念 | 15.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 114 | 超超临界发电 | 15.0 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 115 | ERP概念 | 13.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 116 | 光热发电 | 13.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 117 | 地下管网 | 13.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 118 | 国资云 | 11.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 119 | 电力物联网 | 11.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 120 | 短剧游戏 | 11.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 120

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 国家大基金持股 | 66.8 | 短线活跃 | 68.2 | 观察 | trend_and_burst_aligned |
| 2 | 重组蛋白 | 64.3 | 短线中性 | 51.5 | 中性 | neutral |
| 3 | 创新药 | 61.3 | 短线中性 | 48.5 | 降温 | neutral |
| 4 | 仿制药一致性评价 | 58.3 | 短线中性 | 39.2 | 降温 | neutral |
| 5 | 阿尔茨海默概念 | 57.8 | 短线中性 | 54.0 | 中性 | neutral |
| 6 | 合成生物 | 57.8 | 短线中性 | 46.0 | 降温 | neutral |
| 7 | 存储芯片 | 55.8 | 短线中性 | 63.2 | 中性 | neutral |
| 8 | 光刻胶 | 52.8 | 短线中性 | 69.2 | 观察 | neutral |
| 9 | 辅助生殖 | 52.8 | 短线中性 | 44.0 | 降温 | neutral |
| 10 | 猴痘概念 | 52.8 | 短线中性 | 42.0 | 降温 | neutral |
| 11 | 肝炎概念 | 52.8 | 短线中性 | 33.0 | 偏弱 | neutral |
| 12 | 超导概念 | 49.8 | 短线降温 | 61.0 | 中性 | neutral |
| 13 | 氟化工概念 | 49.8 | 短线降温 | 60.0 | 中性 | neutral |
| 14 | 动物疫苗 | 49.8 | 短线降温 | 56.0 | 中性 | neutral |
| 15 | 芬太尼 | 49.8 | 短线降温 | 37.0 | 降温 | weak_or_cooling |
| 16 | 工业大麻 | 49.8 | 短线降温 | 31.0 | 偏弱 | weak_or_cooling |
| 17 | 超级品牌 | 49.8 | 短线降温 | 26.8 | 偏弱 | weak_or_cooling |
| 18 | 高股息精选 | 49.8 | 短线降温 | 26.8 | 偏弱 | weak_or_cooling |
| 19 | 宠物经济 | 49.8 | 短线降温 | 26.0 | 偏弱 | weak_or_cooling |
| 20 | 白酒概念 | 49.8 | 短线降温 | 18.0 | 偏弱 | weak_or_cooling |
| 21 | 高压氧舱 | 46.8 | 短线降温 | 30.0 | 偏弱 | weak_or_cooling |
| 22 | 三胎概念 | 46.8 | 短线降温 | 22.0 | 偏弱 | weak_or_cooling |
| 23 | 第三代半导体 | 39.8 | 短线降温 | 55.2 | 中性 | neutral |
| 24 | 丙烯酸 | 39.8 | 短线降温 | 45.0 | 降温 | weak_or_cooling |
| 25 | 冰雪产业 | 39.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 26 | 大豆 | 39.8 | 短线降温 | 17.0 | 偏弱 | weak_or_cooling |
| 27 | 黄金概念 | 36.8 | 短线降温 | 32.2 | 偏弱 | weak_or_cooling |
| 28 | 俄乌冲突概念 | 36.8 | 短线降温 | 27.0 | 偏弱 | weak_or_cooling |
| 29 | 福建自贸区 | 36.8 | 短线降温 | 27.0 | 偏弱 | weak_or_cooling |
| 30 | 海南自贸区 | 36.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 31 | 供销社 | 36.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 32 | 共同富裕示范区 | 36.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 33 | 化肥 | 36.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 34 | 参股券商 | 36.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 35 | 参股银行 | 36.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 36 | 国企改革 | 36.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 37 | 航运概念 | 36.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 38 | 黑龙江自贸区 | 36.8 | 短线降温 | 19.0 | 偏弱 | weak_or_cooling |
| 39 | 参股保险 | 36.8 | 短线降温 | 17.0 | 偏弱 | weak_or_cooling |
| 40 | 超超临界发电 | 36.8 | 短线降温 | 15.0 | 偏弱 | weak_or_cooling |
| 41 | 光刻机 | 31.3 | 短线偏弱 | 60.5 | 中性 | neutral |
| 42 | 硅能源 | 28.3 | 短线偏弱 | 53.2 | 中性 | neutral |
| 43 | 钙钛矿电池 | 28.3 | 短线偏弱 | 46.2 | 降温 | weak_or_cooling |
| 44 | 超级电容 | 28.3 | 短线偏弱 | 44.5 | 降温 | weak_or_cooling |
| 45 | BC电池 | 28.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 46 | 传感器 | 25.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 47 | 华为海思概念股 | 25.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 48 | AI PC | 25.3 | 短线偏弱 | 44.5 | 降温 | weak_or_cooling |
| 49 | 宁德时代概念 | 25.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 50 | 光伏概念 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 51 | 固态电池 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 52 | 工业母机 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 53 | 核污染防治 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 54 | 环氧丙烷 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 55 | 航空发动机 | 25.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 56 | 军工 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 57 | 大飞机 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 58 | 比亚迪概念 | 25.3 | 短线偏弱 | 39.2 | 降温 | weak_or_cooling |
| 59 | 锂电池概念 | 25.3 | 短线偏弱 | 37.2 | 降温 | weak_or_cooling |
| 60 | 东数西算(算力) | 25.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 61 | 华为概念 | 25.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 62 | 金属钴 | 25.3 | 短线偏弱 | 32.5 | 偏弱 | weak_or_cooling |
| 63 | 低空经济 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 64 | 安防 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 65 | 核电 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 66 | 海峡两岸 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 67 | 长三角一体化 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 68 | 飞行汽车(eVTOL) | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 69 | 高端装备 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 70 | 高铁 | 25.3 | 短线偏弱 | 31.2 | 偏弱 | weak_or_cooling |
| 71 | 草甘膦 | 25.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 72 | EDR概念 | 25.3 | 短线偏弱 | 27.2 | 偏弱 | weak_or_cooling |
| 73 | 华为汽车 | 25.3 | 短线偏弱 | 27.2 | 偏弱 | weak_or_cooling |
| 74 | 股权转让(并购重组) | 25.3 | 短线偏弱 | 27.2 | 偏弱 | weak_or_cooling |
| 75 | 高压快充 | 25.3 | 短线偏弱 | 27.2 | 偏弱 | weak_or_cooling |
| 76 | 创投 | 25.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 77 | 国产航母 | 25.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 78 | 工业互联网 | 25.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 79 | 海工装备 | 25.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 80 | 车联网(车路协同) | 25.3 | 短线偏弱 | 23.2 | 偏弱 | weak_or_cooling |
| 81 | 储能 | 25.3 | 短线偏弱 | 21.2 | 偏弱 | weak_or_cooling |
| 82 | 充电桩 | 25.3 | 短线偏弱 | 21.2 | 偏弱 | weak_or_cooling |
| 83 | 动力电池回收 | 25.3 | 短线偏弱 | 21.2 | 偏弱 | weak_or_cooling |
| 84 | 钒电池 | 25.3 | 短线偏弱 | 21.2 | 偏弱 | weak_or_cooling |
| 85 | 长安汽车概念 | 25.3 | 短线偏弱 | 21.2 | 偏弱 | weak_or_cooling |
| 86 | ETC | 25.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 87 | 国产操作系统 | 25.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 88 | AI语料 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 89 | 互联网金融 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 90 | 代糖概念 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 91 | 共享单车 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 92 | 华为欧拉 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 93 | 华为鲲鹏 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 94 | 固废处理 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 95 | 多模态AI | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 96 | 广东自贸区 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 97 | 抖音概念(字节概念) | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 98 | 抽水蓄能 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 99 | 换电概念 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 100 | 横琴新区 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 101 | 独角兽概念 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 102 | 电子竞技 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 103 | 电子身份证 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 104 | 百度概念 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 105 | 阿里巴巴概念 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 106 | 风电 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 107 | 鸿蒙概念 | 25.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 108 | ERP概念 | 25.3 | 短线偏弱 | 13.2 | 偏弱 | weak_or_cooling |
| 109 | 光热发电 | 25.3 | 短线偏弱 | 13.2 | 偏弱 | weak_or_cooling |
| 110 | 地下管网 | 25.3 | 短线偏弱 | 13.2 | 偏弱 | weak_or_cooling |
| 111 | 国资云 | 25.3 | 短线偏弱 | 11.2 | 偏弱 | weak_or_cooling |
| 112 | 电力物联网 | 25.3 | 短线偏弱 | 11.2 | 偏弱 | weak_or_cooling |
| 113 | 短剧游戏 | 25.3 | 短线偏弱 | 11.2 | 偏弱 | weak_or_cooling |
| 114 | AI手机 | 21.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 115 | 富士康概念 | 21.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 116 | 电子纸 | 21.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 117 | 毫米波雷达 | 21.3 | 短线偏弱 | 44.2 | 降温 | weak_or_cooling |
| 118 | 共封装光学(CPO) | 21.3 | 短线偏弱 | 43.6 | 降温 | weak_or_cooling |
| 119 | F5G概念 | 21.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 120 | 成飞概念 | 21.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |

## 分歧板块

当前无明显分歧板块。

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 光刻胶

**趋势持续评分**:
- 趋势分: 69.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 4.0

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

### 2. 国家大基金持股

**趋势持续评分**:
- 趋势分: 68.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 11.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 4.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 6.0

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

### 3. 存储芯片

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

### 4. 超导概念

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
- 短线分: 49.8
- 短线等级: 短线降温
- 短线 breakdown:
  - radar_today_component: 16.8
  - one_day_change_component: 12.0
  - three_day_momentum_component: 3.0
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

### 5. 光刻机

**趋势持续评分**:
- 趋势分: 60.5
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 15.0
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
