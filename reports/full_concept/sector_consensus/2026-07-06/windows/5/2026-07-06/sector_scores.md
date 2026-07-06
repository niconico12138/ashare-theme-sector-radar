# 板块综合评分

**分析日期**: 2026-07-06
**更新时间**: 2026-07-06T14:47:50.603738

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。

## 数据来源

- **板块类型**: concept
- **历史数据范围**: 2026-05-20 ~ 2026-07-06
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
| 1 | 共同富裕示范区 | 81.8 | 重点观察 | 55.8 | 短线中性 | neutral |
| 2 | 黄金概念 | 81.8 | 重点观察 | 58.8 | 短线中性 | neutral |
| 3 | 三胎概念 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 4 | 动物疫苗 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 5 | 合成生物 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 6 | 工业大麻 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 7 | 黑龙江自贸区 | 81.0 | 重点观察 | 58.8 | 短线中性 | neutral |
| 8 | 参股保险 | 78.8 | 观察 | 45.8 | 短线降温 | trend_only |
| 9 | 仿制药一致性评价 | 78.2 | 观察 | 58.8 | 短线中性 | neutral |
| 10 | 创新药 | 78.2 | 观察 | 58.8 | 短线中性 | neutral |
| 11 | 肝炎概念 | 78.2 | 观察 | 58.8 | 短线中性 | neutral |
| 12 | 辅助生殖 | 78.2 | 观察 | 58.8 | 短线中性 | neutral |
| 13 | 阿尔茨海默概念 | 78.2 | 观察 | 58.8 | 短线中性 | neutral |
| 14 | 航运概念 | 78.0 | 观察 | 58.8 | 短线中性 | neutral |
| 15 | 华为汽车 | 77.0 | 观察 | 63.8 | 短线中性 | neutral |
| 16 | 航空发动机 | 77.0 | 观察 | 63.8 | 短线中性 | neutral |
| 17 | 芬太尼 | 76.2 | 观察 | 58.8 | 短线中性 | neutral |
| 18 | 海南自贸区 | 74.2 | 观察 | 37.3 | 短线降温 | trend_only |
| 19 | 国产航母 | 74.2 | 观察 | 63.8 | 短线中性 | neutral |
| 20 | 宠物经济 | 74.0 | 观察 | 58.8 | 短线中性 | neutral |
| 21 | 工业互联网 | 74.0 | 观察 | 55.8 | 短线中性 | neutral |
| 22 | 工业母机 | 74.0 | 观察 | 55.8 | 短线中性 | neutral |
| 23 | 长安汽车概念 | 74.0 | 观察 | 55.8 | 短线中性 | neutral |
| 24 | 飞行汽车(eVTOL) | 74.0 | 观察 | 55.8 | 短线中性 | neutral |
| 25 | 高端装备 | 74.0 | 观察 | 55.8 | 短线中性 | neutral |
| 26 | 固废处理 | 73.8 | 观察 | 55.8 | 短线中性 | neutral |
| 27 | 地下管网 | 73.8 | 观察 | 55.8 | 短线中性 | neutral |
| 28 | 高股息精选 | 73.0 | 观察 | 55.8 | 短线中性 | neutral |
| 29 | 猴痘概念 | 71.2 | 观察 | 58.8 | 短线中性 | neutral |
| 30 | 重组蛋白 | 71.2 | 观察 | 58.8 | 短线中性 | neutral |
| 31 | 大飞机 | 71.0 | 观察 | 55.8 | 短线中性 | neutral |
| 32 | 国企改革 | 70.8 | 观察 | 45.8 | 短线降温 | trend_only |
| 33 | 福建自贸区 | 70.8 | 观察 | 45.8 | 短线降温 | trend_only |
| 34 | 超级品牌 | 70.8 | 观察 | 45.8 | 短线降温 | trend_only |
| 35 | 金属钴 | 70.8 | 观察 | 45.8 | 短线降温 | trend_only |
| 36 | 参股银行 | 70.0 | 观察 | 45.8 | 短线降温 | trend_only |
| 37 | 丙烯酸 | 66.2 | 观察 | 34.3 | 短线偏弱 | trend_only |
| 38 | 成飞概念 | 66.2 | 观察 | 63.8 | 短线中性 | neutral |
| 39 | ERP概念 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 40 | 低空经济 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 41 | 供销社 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 42 | 军工 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 43 | 冰雪产业 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 44 | 国资云 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 45 | 换电概念 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 46 | 核电 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 47 | 比亚迪概念 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 48 | 车联网(车路协同) | 66.0 | 观察 | 52.8 | 短线中性 | neutral |
| 49 | 长三角一体化 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 50 | 高压快充 | 66.0 | 观察 | 52.8 | 短线中性 | neutral |
| 51 | 高铁 | 66.0 | 观察 | 55.8 | 短线中性 | neutral |
| 52 | 高压氧舱 | 66.0 | 观察 | 45.8 | 短线降温 | trend_only |
| 53 | 大豆 | 65.0 | 观察 | 45.8 | 短线降温 | trend_only |
| 54 | 安防 | 64.0 | 中性 | 52.8 | 短线中性 | neutral |
| 55 | 电力物联网 | 64.0 | 中性 | 52.8 | 短线中性 | neutral |
| 56 | 抽水蓄能 | 63.8 | 中性 | 52.8 | 短线中性 | neutral |
| 57 | 传感器 | 63.2 | 中性 | 52.8 | 短线中性 | neutral |
| 58 | 储能 | 63.0 | 中性 | 52.8 | 短线中性 | neutral |
| 59 | 充电桩 | 63.0 | 中性 | 52.8 | 短线中性 | neutral |
| 60 | 光热发电 | 63.0 | 中性 | 52.8 | 短线中性 | neutral |
| 61 | 横琴新区 | 63.0 | 中性 | 55.8 | 短线中性 | neutral |
| 62 | 海工装备 | 63.0 | 中性 | 55.8 | 短线中性 | neutral |
| 63 | 风电 | 63.0 | 中性 | 55.8 | 短线中性 | neutral |
| 64 | 互联网金融 | 63.0 | 中性 | 45.8 | 短线降温 | neutral |
| 65 | 共享单车 | 63.0 | 中性 | 45.8 | 短线降温 | neutral |
| 66 | 创投 | 63.0 | 中性 | 45.8 | 短线降温 | neutral |
| 67 | 华为欧拉 | 63.0 | 中性 | 42.8 | 短线降温 | neutral |
| 68 | 华为鲲鹏 | 63.0 | 中性 | 42.8 | 短线降温 | neutral |
| 69 | 参股券商 | 63.0 | 中性 | 45.8 | 短线降温 | neutral |
| 70 | 核污染防治 | 63.0 | 中性 | 42.8 | 短线降温 | neutral |
| 71 | 白酒概念 | 63.0 | 中性 | 45.8 | 短线降温 | neutral |
| 72 | 股权转让(并购重组) | 63.0 | 中性 | 45.8 | 短线降温 | neutral |
| 73 | 氟化工概念 | 62.5 | 中性 | 27.3 | 短线偏弱 | neutral |
| 74 | EDR概念 | 61.2 | 中性 | 49.8 | 短线降温 | neutral |
| 75 | 短剧游戏 | 60.0 | 中性 | 34.3 | 短线偏弱 | neutral |
| 76 | ETC | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 77 | 俄乌冲突概念 | 60.0 | 中性 | 45.8 | 短线降温 | neutral |
| 78 | 动力电池回收 | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 79 | 国产操作系统 | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 80 | 多模态AI | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 81 | 宁德时代概念 | 60.0 | 中性 | 39.8 | 短线降温 | neutral |
| 82 | 广东自贸区 | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 83 | 抖音概念(字节概念) | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 84 | 海峡两岸 | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 85 | 独角兽概念 | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 86 | 百度概念 | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 87 | 超超临界发电 | 60.0 | 中性 | 45.8 | 短线降温 | neutral |
| 88 | 钒电池 | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 89 | 锂电池概念 | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 90 | 阿里巴巴概念 | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 91 | 鸿蒙概念 | 60.0 | 中性 | 42.8 | 短线降温 | neutral |
| 92 | 毫米波雷达 | 58.2 | 中性 | 49.8 | 短线降温 | neutral |
| 93 | 东数西算(算力) | 58.0 | 中性 | 39.8 | 短线降温 | neutral |
| 94 | 华为概念 | 58.0 | 中性 | 39.8 | 短线降温 | neutral |
| 95 | 化肥 | 56.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 96 | 电子身份证 | 55.2 | 中性 | 42.8 | 短线降温 | neutral |
| 97 | 草甘膦 | 54.0 | 中性 | 45.8 | 短线降温 | neutral |
| 98 | 代糖概念 | 53.0 | 中性 | 45.8 | 短线降温 | neutral |
| 99 | 光伏概念 | 53.0 | 中性 | 39.8 | 短线降温 | neutral |
| 100 | AI语料 | 52.2 | 中性 | 31.3 | 短线偏弱 | neutral |
| 101 | 电子竞技 | 50.0 | 中性 | 31.3 | 短线偏弱 | neutral |
| 102 | 环氧丙烷 | 49.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 103 | 固态电池 | 40.2 | 降温 | 28.3 | 短线偏弱 | weak_or_cooling |
| 104 | AI PC | 37.2 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 105 | 光刻胶 | 36.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 106 | 超导概念 | 33.5 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 107 | 超级电容 | 32.2 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 108 | 华为海思概念股 | 30.6 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 109 | AI手机 | 30.4 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 110 | 富士康概念 | 30.4 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 111 | 存储芯片 | 29.6 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 112 | BC电池 | 29.4 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 113 | 硅能源 | 29.4 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |
| 114 | 钙钛矿电池 | 26.4 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 115 | 第三代半导体 | 25.4 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 116 | 电子纸 | 22.6 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 117 | 光刻机 | 18.6 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 118 | 国家大基金持股 | 13.7 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 119 | F5G概念 | 11.7 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 120 | 共封装光学(CPO) | 11.7 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 120

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 华为汽车 | 63.8 | 短线中性 | 77.0 | 观察 | neutral |
| 2 | 航空发动机 | 63.8 | 短线中性 | 77.0 | 观察 | neutral |
| 3 | 国产航母 | 63.8 | 短线中性 | 74.2 | 观察 | neutral |
| 4 | 成飞概念 | 63.8 | 短线中性 | 66.2 | 观察 | neutral |
| 5 | 黄金概念 | 58.8 | 短线中性 | 81.8 | 重点观察 | neutral |
| 6 | 三胎概念 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 7 | 动物疫苗 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 8 | 合成生物 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 9 | 工业大麻 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 10 | 黑龙江自贸区 | 58.8 | 短线中性 | 81.0 | 重点观察 | neutral |
| 11 | 仿制药一致性评价 | 58.8 | 短线中性 | 78.2 | 观察 | neutral |
| 12 | 创新药 | 58.8 | 短线中性 | 78.2 | 观察 | neutral |
| 13 | 肝炎概念 | 58.8 | 短线中性 | 78.2 | 观察 | neutral |
| 14 | 辅助生殖 | 58.8 | 短线中性 | 78.2 | 观察 | neutral |
| 15 | 阿尔茨海默概念 | 58.8 | 短线中性 | 78.2 | 观察 | neutral |
| 16 | 航运概念 | 58.8 | 短线中性 | 78.0 | 观察 | neutral |
| 17 | 芬太尼 | 58.8 | 短线中性 | 76.2 | 观察 | neutral |
| 18 | 宠物经济 | 58.8 | 短线中性 | 74.0 | 观察 | neutral |
| 19 | 猴痘概念 | 58.8 | 短线中性 | 71.2 | 观察 | neutral |
| 20 | 重组蛋白 | 58.8 | 短线中性 | 71.2 | 观察 | neutral |
| 21 | 共同富裕示范区 | 55.8 | 短线中性 | 81.8 | 重点观察 | neutral |
| 22 | 工业互联网 | 55.8 | 短线中性 | 74.0 | 观察 | neutral |
| 23 | 工业母机 | 55.8 | 短线中性 | 74.0 | 观察 | neutral |
| 24 | 长安汽车概念 | 55.8 | 短线中性 | 74.0 | 观察 | neutral |
| 25 | 飞行汽车(eVTOL) | 55.8 | 短线中性 | 74.0 | 观察 | neutral |
| 26 | 高端装备 | 55.8 | 短线中性 | 74.0 | 观察 | neutral |
| 27 | 固废处理 | 55.8 | 短线中性 | 73.8 | 观察 | neutral |
| 28 | 地下管网 | 55.8 | 短线中性 | 73.8 | 观察 | neutral |
| 29 | 高股息精选 | 55.8 | 短线中性 | 73.0 | 观察 | neutral |
| 30 | 大飞机 | 55.8 | 短线中性 | 71.0 | 观察 | neutral |
| 31 | ERP概念 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 32 | 低空经济 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 33 | 供销社 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 34 | 军工 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 35 | 冰雪产业 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 36 | 国资云 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 37 | 换电概念 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 38 | 核电 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 39 | 比亚迪概念 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 40 | 长三角一体化 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 41 | 高铁 | 55.8 | 短线中性 | 66.0 | 观察 | neutral |
| 42 | 横琴新区 | 55.8 | 短线中性 | 63.0 | 中性 | neutral |
| 43 | 海工装备 | 55.8 | 短线中性 | 63.0 | 中性 | neutral |
| 44 | 风电 | 55.8 | 短线中性 | 63.0 | 中性 | neutral |
| 45 | 车联网(车路协同) | 52.8 | 短线中性 | 66.0 | 观察 | neutral |
| 46 | 高压快充 | 52.8 | 短线中性 | 66.0 | 观察 | neutral |
| 47 | 安防 | 52.8 | 短线中性 | 64.0 | 中性 | neutral |
| 48 | 电力物联网 | 52.8 | 短线中性 | 64.0 | 中性 | neutral |
| 49 | 抽水蓄能 | 52.8 | 短线中性 | 63.8 | 中性 | neutral |
| 50 | 传感器 | 52.8 | 短线中性 | 63.2 | 中性 | neutral |
| 51 | 储能 | 52.8 | 短线中性 | 63.0 | 中性 | neutral |
| 52 | 充电桩 | 52.8 | 短线中性 | 63.0 | 中性 | neutral |
| 53 | 光热发电 | 52.8 | 短线中性 | 63.0 | 中性 | neutral |
| 54 | EDR概念 | 49.8 | 短线降温 | 61.2 | 中性 | neutral |
| 55 | 毫米波雷达 | 49.8 | 短线降温 | 58.2 | 中性 | neutral |
| 56 | 参股保险 | 45.8 | 短线降温 | 78.8 | 观察 | trend_only |
| 57 | 国企改革 | 45.8 | 短线降温 | 70.8 | 观察 | trend_only |
| 58 | 福建自贸区 | 45.8 | 短线降温 | 70.8 | 观察 | trend_only |
| 59 | 超级品牌 | 45.8 | 短线降温 | 70.8 | 观察 | trend_only |
| 60 | 金属钴 | 45.8 | 短线降温 | 70.8 | 观察 | trend_only |
| 61 | 参股银行 | 45.8 | 短线降温 | 70.0 | 观察 | trend_only |
| 62 | 高压氧舱 | 45.8 | 短线降温 | 66.0 | 观察 | trend_only |
| 63 | 大豆 | 45.8 | 短线降温 | 65.0 | 观察 | trend_only |
| 64 | 互联网金融 | 45.8 | 短线降温 | 63.0 | 中性 | neutral |
| 65 | 共享单车 | 45.8 | 短线降温 | 63.0 | 中性 | neutral |
| 66 | 创投 | 45.8 | 短线降温 | 63.0 | 中性 | neutral |
| 67 | 参股券商 | 45.8 | 短线降温 | 63.0 | 中性 | neutral |
| 68 | 白酒概念 | 45.8 | 短线降温 | 63.0 | 中性 | neutral |
| 69 | 股权转让(并购重组) | 45.8 | 短线降温 | 63.0 | 中性 | neutral |
| 70 | 俄乌冲突概念 | 45.8 | 短线降温 | 60.0 | 中性 | neutral |
| 71 | 超超临界发电 | 45.8 | 短线降温 | 60.0 | 中性 | neutral |
| 72 | 草甘膦 | 45.8 | 短线降温 | 54.0 | 中性 | neutral |
| 73 | 代糖概念 | 45.8 | 短线降温 | 53.0 | 中性 | neutral |
| 74 | 华为欧拉 | 42.8 | 短线降温 | 63.0 | 中性 | neutral |
| 75 | 华为鲲鹏 | 42.8 | 短线降温 | 63.0 | 中性 | neutral |
| 76 | 核污染防治 | 42.8 | 短线降温 | 63.0 | 中性 | neutral |
| 77 | ETC | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 78 | 动力电池回收 | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 79 | 国产操作系统 | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 80 | 多模态AI | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 81 | 广东自贸区 | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 82 | 抖音概念(字节概念) | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 83 | 海峡两岸 | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 84 | 独角兽概念 | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 85 | 百度概念 | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 86 | 钒电池 | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 87 | 锂电池概念 | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 88 | 阿里巴巴概念 | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 89 | 鸿蒙概念 | 42.8 | 短线降温 | 60.0 | 中性 | neutral |
| 90 | 电子身份证 | 42.8 | 短线降温 | 55.2 | 中性 | neutral |
| 91 | 宁德时代概念 | 39.8 | 短线降温 | 60.0 | 中性 | neutral |
| 92 | 东数西算(算力) | 39.8 | 短线降温 | 58.0 | 中性 | neutral |
| 93 | 华为概念 | 39.8 | 短线降温 | 58.0 | 中性 | neutral |
| 94 | 光伏概念 | 39.8 | 短线降温 | 53.0 | 中性 | neutral |
| 95 | 海南自贸区 | 37.3 | 短线降温 | 74.2 | 观察 | trend_only |
| 96 | AI PC | 36.8 | 短线降温 | 37.2 | 降温 | weak_or_cooling |
| 97 | AI手机 | 36.8 | 短线降温 | 30.4 | 偏弱 | weak_or_cooling |
| 98 | 富士康概念 | 36.8 | 短线降温 | 30.4 | 偏弱 | weak_or_cooling |
| 99 | 丙烯酸 | 34.3 | 短线偏弱 | 66.2 | 观察 | trend_only |
| 100 | 短剧游戏 | 34.3 | 短线偏弱 | 60.0 | 中性 | neutral |
| 101 | 化肥 | 34.3 | 短线偏弱 | 56.2 | 中性 | neutral |
| 102 | 环氧丙烷 | 34.3 | 短线偏弱 | 49.2 | 降温 | weak_or_cooling |
| 103 | AI语料 | 31.3 | 短线偏弱 | 52.2 | 中性 | neutral |
| 104 | 电子竞技 | 31.3 | 短线偏弱 | 50.0 | 中性 | neutral |
| 105 | 固态电池 | 28.3 | 短线偏弱 | 40.2 | 降温 | weak_or_cooling |
| 106 | 超级电容 | 28.3 | 短线偏弱 | 32.2 | 偏弱 | weak_or_cooling |
| 107 | 氟化工概念 | 27.3 | 短线偏弱 | 62.5 | 中性 | neutral |
| 108 | 超导概念 | 25.3 | 短线偏弱 | 33.5 | 偏弱 | weak_or_cooling |
| 109 | 华为海思概念股 | 25.3 | 短线偏弱 | 30.6 | 偏弱 | weak_or_cooling |
| 110 | 存储芯片 | 25.3 | 短线偏弱 | 29.6 | 偏弱 | weak_or_cooling |
| 111 | BC电池 | 25.3 | 短线偏弱 | 29.4 | 偏弱 | weak_or_cooling |
| 112 | 钙钛矿电池 | 25.3 | 短线偏弱 | 26.4 | 偏弱 | weak_or_cooling |
| 113 | F5G概念 | 25.3 | 短线偏弱 | 11.7 | 偏弱 | weak_or_cooling |
| 114 | 共封装光学(CPO) | 25.3 | 短线偏弱 | 11.7 | 偏弱 | weak_or_cooling |
| 115 | 硅能源 | 24.3 | 短线偏弱 | 29.4 | 偏弱 | weak_or_cooling |
| 116 | 光刻胶 | 21.3 | 短线偏弱 | 36.5 | 降温 | weak_or_cooling |
| 117 | 第三代半导体 | 21.3 | 短线偏弱 | 25.4 | 偏弱 | weak_or_cooling |
| 118 | 电子纸 | 21.3 | 短线偏弱 | 22.6 | 偏弱 | weak_or_cooling |
| 119 | 光刻机 | 21.3 | 短线偏弱 | 18.6 | 偏弱 | weak_or_cooling |
| 120 | 国家大基金持股 | 21.3 | 短线偏弱 | 13.7 | 偏弱 | weak_or_cooling |

## 分歧板块

### 趋势强但短线不热

| 板块 | 趋势分 | 短线分 | 说明 |
|------|--------|--------|------|
| 参股保险 | 78.8 | 45.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 海南自贸区 | 74.2 | 37.3 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 国企改革 | 70.8 | 45.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 福建自贸区 | 70.8 | 45.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 超级品牌 | 70.8 | 45.8 | 趋势强但短线不热，中长期趋势观察价值较高 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 共同富裕示范区

**趋势持续评分**:
- 趋势分: 81.8
- 趋势等级: 重点观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 4.0
  - data_quality_component: 6.4
  - risk_penalty: 0.0

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

### 2. 黄金概念

**趋势持续评分**:
- 趋势分: 81.8
- 趋势等级: 重点观察
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 8.0
  - volatility_component: 4.0
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

### 3. 三胎概念

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

### 4. 动物疫苗

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

### 5. 合成生物

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

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
