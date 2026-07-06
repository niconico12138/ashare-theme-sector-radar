# 板块综合评分

**分析日期**: 2026-07-06
**更新时间**: 2026-07-06T14:47:50.640490

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
| 1 | 动物疫苗 | 65.0 | 观察 | 58.8 | 短线中性 | neutral |
| 2 | 高股息精选 | 59.0 | 中性 | 55.8 | 短线中性 | neutral |
| 3 | 仿制药一致性评价 | 58.2 | 中性 | 58.8 | 短线中性 | neutral |
| 4 | 创新药 | 58.2 | 中性 | 58.8 | 短线中性 | neutral |
| 5 | 合成生物 | 58.2 | 中性 | 58.8 | 短线中性 | neutral |
| 6 | 阿尔茨海默概念 | 58.2 | 中性 | 58.8 | 短线中性 | neutral |
| 7 | 工业大麻 | 58.0 | 中性 | 58.8 | 短线中性 | neutral |
| 8 | 黑龙江自贸区 | 58.0 | 中性 | 58.8 | 短线中性 | neutral |
| 9 | 猴痘概念 | 56.2 | 中性 | 58.8 | 短线中性 | neutral |
| 10 | 超级品牌 | 56.0 | 中性 | 45.8 | 短线降温 | neutral |
| 11 | 氟化工概念 | 55.5 | 中性 | 27.3 | 短线偏弱 | neutral |
| 12 | 丙烯酸 | 55.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 13 | 航运概念 | 55.0 | 中性 | 58.8 | 短线中性 | neutral |
| 14 | 长三角一体化 | 54.0 | 中性 | 55.8 | 短线中性 | neutral |
| 15 | 重组蛋白 | 53.4 | 中性 | 58.8 | 短线中性 | neutral |
| 16 | 肝炎概念 | 53.2 | 中性 | 58.8 | 短线中性 | neutral |
| 17 | 辅助生殖 | 53.2 | 中性 | 58.8 | 短线中性 | neutral |
| 18 | 传感器 | 52.0 | 中性 | 52.8 | 短线中性 | neutral |
| 19 | 参股保险 | 52.0 | 中性 | 45.8 | 短线降温 | neutral |
| 20 | 参股银行 | 52.0 | 中性 | 45.8 | 短线降温 | neutral |
| 21 | 固废处理 | 51.0 | 中性 | 55.8 | 短线中性 | neutral |
| 22 | 芬太尼 | 50.2 | 中性 | 58.8 | 短线中性 | neutral |
| 23 | 三胎概念 | 50.0 | 中性 | 58.8 | 短线中性 | neutral |
| 24 | 供销社 | 50.0 | 中性 | 55.8 | 短线中性 | neutral |
| 25 | 共同富裕示范区 | 50.0 | 中性 | 55.8 | 短线中性 | neutral |
| 26 | 宠物经济 | 50.0 | 中性 | 58.8 | 短线中性 | neutral |
| 27 | 海南自贸区 | 48.2 | 降温 | 37.3 | 短线降温 | weak_or_cooling |
| 28 | 国产航母 | 48.2 | 降温 | 63.8 | 短线中性 | neutral |
| 29 | 工业互联网 | 48.0 | 降温 | 55.8 | 短线中性 | neutral |
| 30 | 高压氧舱 | 47.2 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 31 | 成飞概念 | 47.0 | 降温 | 63.8 | 短线中性 | neutral |
| 32 | 光刻胶 | 46.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 33 | 存储芯片 | 46.5 | 降温 | 25.3 | 短线偏弱 | weak_or_cooling |
| 34 | 冰雪产业 | 46.0 | 降温 | 55.8 | 短线中性 | neutral |
| 35 | 军工 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 36 | 比亚迪概念 | 44.0 | 降温 | 55.8 | 短线中性 | neutral |
| 37 | EDR概念 | 43.2 | 降温 | 49.8 | 短线降温 | weak_or_cooling |
| 38 | 黄金概念 | 43.2 | 降温 | 58.8 | 短线中性 | neutral |
| 39 | 参股券商 | 43.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 40 | 国企改革 | 43.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 41 | 白酒概念 | 43.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 42 | 股权转让(并购重组) | 43.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 43 | 华为汽车 | 42.0 | 降温 | 58.8 | 短线中性 | neutral |
| 44 | 航空发动机 | 42.0 | 降温 | 58.8 | 短线中性 | neutral |
| 45 | 地下管网 | 42.0 | 降温 | 55.8 | 短线中性 | neutral |
| 46 | 创投 | 41.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 47 | 核污染防治 | 41.0 | 降温 | 42.8 | 短线降温 | weak_or_cooling |
| 48 | 工业母机 | 40.2 | 降温 | 55.8 | 短线中性 | neutral |
| 49 | 核电 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 50 | 海工装备 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 51 | 车联网(车路协同) | 40.0 | 降温 | 52.8 | 短线中性 | neutral |
| 52 | 高铁 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 53 | 大飞机 | 39.0 | 降温 | 55.8 | 短线中性 | neutral |
| 54 | 长安汽车概念 | 39.0 | 降温 | 55.8 | 短线中性 | neutral |
| 55 | 飞行汽车(eVTOL) | 39.0 | 降温 | 55.8 | 短线中性 | neutral |
| 56 | 高端装备 | 39.0 | 降温 | 55.8 | 短线中性 | neutral |
| 57 | 第三代半导体 | 38.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 58 | 广东自贸区 | 38.0 | 降温 | 42.8 | 短线降温 | weak_or_cooling |
| 59 | 草甘膦 | 38.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 60 | AI PC | 37.2 | 降温 | 36.8 | 短线降温 | weak_or_cooling |
| 61 | 化肥 | 36.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 62 | 环氧丙烷 | 36.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 63 | 硅能源 | 36.2 | 降温 | 24.3 | 短线偏弱 | weak_or_cooling |
| 64 | 光刻机 | 35.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 65 | 电子纸 | 35.5 | 降温 | 21.3 | 短线偏弱 | weak_or_cooling |
| 66 | ERP概念 | 35.0 | 降温 | 55.8 | 短线中性 | neutral |
| 67 | 低空经济 | 35.0 | 降温 | 55.8 | 短线中性 | neutral |
| 68 | 储能 | 35.0 | 降温 | 52.8 | 短线中性 | neutral |
| 69 | 充电桩 | 35.0 | 降温 | 52.8 | 短线中性 | neutral |
| 70 | 安防 | 35.0 | 降温 | 52.8 | 短线中性 | neutral |
| 71 | 横琴新区 | 35.0 | 降温 | 55.8 | 短线中性 | neutral |
| 72 | 风电 | 35.0 | 降温 | 55.8 | 短线中性 | neutral |
| 73 | 高压快充 | 35.0 | 降温 | 52.8 | 短线中性 | neutral |
| 74 | 国家大基金持股 | 34.6 | 偏弱 | 21.3 | 短线偏弱 | weak_or_cooling |
| 75 | 大豆 | 34.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 76 | 宁德时代概念 | 34.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 77 | 福建自贸区 | 34.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 78 | 电力物联网 | 32.2 | 偏弱 | 52.8 | 短线中性 | neutral |
| 79 | 俄乌冲突概念 | 32.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 80 | 光伏概念 | 32.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 81 | 共享单车 | 32.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 82 | 华为概念 | 32.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 83 | 海峡两岸 | 32.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 84 | 独角兽概念 | 32.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 85 | 钒电池 | 32.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 86 | 锂电池概念 | 32.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 87 | 华为海思概念股 | 31.4 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 88 | 国资云 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 89 | 抽水蓄能 | 31.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 90 | 换电概念 | 31.0 | 偏弱 | 55.8 | 短线中性 | neutral |
| 91 | 超导概念 | 30.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 92 | 超级电容 | 30.2 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 93 | ETC | 30.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 94 | 东数西算(算力) | 30.0 | 偏弱 | 39.8 | 短线降温 | weak_or_cooling |
| 95 | AI手机 | 29.2 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 96 | 互联网金融 | 29.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 97 | 固态电池 | 28.2 | 偏弱 | 28.3 | 短线偏弱 | weak_or_cooling |
| 98 | 毫米波雷达 | 28.2 | 偏弱 | 49.8 | 短线降温 | weak_or_cooling |
| 99 | 动力电池回收 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 100 | 国产操作系统 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 101 | 多模态AI | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 102 | 抖音概念(字节概念) | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 103 | 百度概念 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 104 | 超超临界发电 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 105 | 阿里巴巴概念 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 106 | 鸿蒙概念 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 107 | 电子竞技 | 27.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 108 | 钙钛矿电池 | 27.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 109 | 代糖概念 | 27.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 110 | 光热发电 | 26.0 | 偏弱 | 52.8 | 短线中性 | neutral |
| 111 | 华为鲲鹏 | 25.2 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 112 | 富士康概念 | 25.2 | 偏弱 | 36.8 | 短线降温 | weak_or_cooling |
| 113 | 电子身份证 | 25.2 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 114 | BC电池 | 24.2 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 115 | 短剧游戏 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 116 | 金属钴 | 23.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 117 | 共封装光学(CPO) | 21.4 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |
| 118 | 华为欧拉 | 21.2 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 119 | AI语料 | 12.4 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 120 | F5G概念 | 12.4 | 偏弱 | 25.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 120

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 国产航母 | 63.8 | 短线中性 | 48.2 | 降温 | neutral |
| 2 | 成飞概念 | 63.8 | 短线中性 | 47.0 | 降温 | neutral |
| 3 | 动物疫苗 | 58.8 | 短线中性 | 65.0 | 观察 | neutral |
| 4 | 仿制药一致性评价 | 58.8 | 短线中性 | 58.2 | 中性 | neutral |
| 5 | 创新药 | 58.8 | 短线中性 | 58.2 | 中性 | neutral |
| 6 | 合成生物 | 58.8 | 短线中性 | 58.2 | 中性 | neutral |
| 7 | 阿尔茨海默概念 | 58.8 | 短线中性 | 58.2 | 中性 | neutral |
| 8 | 工业大麻 | 58.8 | 短线中性 | 58.0 | 中性 | neutral |
| 9 | 黑龙江自贸区 | 58.8 | 短线中性 | 58.0 | 中性 | neutral |
| 10 | 猴痘概念 | 58.8 | 短线中性 | 56.2 | 中性 | neutral |
| 11 | 航运概念 | 58.8 | 短线中性 | 55.0 | 中性 | neutral |
| 12 | 重组蛋白 | 58.8 | 短线中性 | 53.4 | 中性 | neutral |
| 13 | 肝炎概念 | 58.8 | 短线中性 | 53.2 | 中性 | neutral |
| 14 | 辅助生殖 | 58.8 | 短线中性 | 53.2 | 中性 | neutral |
| 15 | 芬太尼 | 58.8 | 短线中性 | 50.2 | 中性 | neutral |
| 16 | 三胎概念 | 58.8 | 短线中性 | 50.0 | 中性 | neutral |
| 17 | 宠物经济 | 58.8 | 短线中性 | 50.0 | 中性 | neutral |
| 18 | 黄金概念 | 58.8 | 短线中性 | 43.2 | 降温 | neutral |
| 19 | 华为汽车 | 58.8 | 短线中性 | 42.0 | 降温 | neutral |
| 20 | 航空发动机 | 58.8 | 短线中性 | 42.0 | 降温 | neutral |
| 21 | 高股息精选 | 55.8 | 短线中性 | 59.0 | 中性 | neutral |
| 22 | 长三角一体化 | 55.8 | 短线中性 | 54.0 | 中性 | neutral |
| 23 | 固废处理 | 55.8 | 短线中性 | 51.0 | 中性 | neutral |
| 24 | 供销社 | 55.8 | 短线中性 | 50.0 | 中性 | neutral |
| 25 | 共同富裕示范区 | 55.8 | 短线中性 | 50.0 | 中性 | neutral |
| 26 | 工业互联网 | 55.8 | 短线中性 | 48.0 | 降温 | neutral |
| 27 | 冰雪产业 | 55.8 | 短线中性 | 46.0 | 降温 | neutral |
| 28 | 军工 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 29 | 比亚迪概念 | 55.8 | 短线中性 | 44.0 | 降温 | neutral |
| 30 | 地下管网 | 55.8 | 短线中性 | 42.0 | 降温 | neutral |
| 31 | 工业母机 | 55.8 | 短线中性 | 40.2 | 降温 | neutral |
| 32 | 核电 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 33 | 海工装备 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 34 | 高铁 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 35 | 大飞机 | 55.8 | 短线中性 | 39.0 | 降温 | neutral |
| 36 | 长安汽车概念 | 55.8 | 短线中性 | 39.0 | 降温 | neutral |
| 37 | 飞行汽车(eVTOL) | 55.8 | 短线中性 | 39.0 | 降温 | neutral |
| 38 | 高端装备 | 55.8 | 短线中性 | 39.0 | 降温 | neutral |
| 39 | ERP概念 | 55.8 | 短线中性 | 35.0 | 降温 | neutral |
| 40 | 低空经济 | 55.8 | 短线中性 | 35.0 | 降温 | neutral |
| 41 | 横琴新区 | 55.8 | 短线中性 | 35.0 | 降温 | neutral |
| 42 | 风电 | 55.8 | 短线中性 | 35.0 | 降温 | neutral |
| 43 | 国资云 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 44 | 换电概念 | 55.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 45 | 传感器 | 52.8 | 短线中性 | 52.0 | 中性 | neutral |
| 46 | 车联网(车路协同) | 52.8 | 短线中性 | 40.0 | 降温 | neutral |
| 47 | 储能 | 52.8 | 短线中性 | 35.0 | 降温 | neutral |
| 48 | 充电桩 | 52.8 | 短线中性 | 35.0 | 降温 | neutral |
| 49 | 安防 | 52.8 | 短线中性 | 35.0 | 降温 | neutral |
| 50 | 高压快充 | 52.8 | 短线中性 | 35.0 | 降温 | neutral |
| 51 | 电力物联网 | 52.8 | 短线中性 | 32.2 | 偏弱 | neutral |
| 52 | 抽水蓄能 | 52.8 | 短线中性 | 31.0 | 偏弱 | neutral |
| 53 | 光热发电 | 52.8 | 短线中性 | 26.0 | 偏弱 | neutral |
| 54 | EDR概念 | 49.8 | 短线降温 | 43.2 | 降温 | weak_or_cooling |
| 55 | 毫米波雷达 | 49.8 | 短线降温 | 28.2 | 偏弱 | weak_or_cooling |
| 56 | 超级品牌 | 45.8 | 短线降温 | 56.0 | 中性 | neutral |
| 57 | 参股保险 | 45.8 | 短线降温 | 52.0 | 中性 | neutral |
| 58 | 参股银行 | 45.8 | 短线降温 | 52.0 | 中性 | neutral |
| 59 | 高压氧舱 | 45.8 | 短线降温 | 47.2 | 降温 | weak_or_cooling |
| 60 | 参股券商 | 45.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 61 | 国企改革 | 45.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 62 | 白酒概念 | 45.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 63 | 股权转让(并购重组) | 45.8 | 短线降温 | 43.0 | 降温 | weak_or_cooling |
| 64 | 创投 | 45.8 | 短线降温 | 41.0 | 降温 | weak_or_cooling |
| 65 | 草甘膦 | 45.8 | 短线降温 | 38.0 | 降温 | weak_or_cooling |
| 66 | 大豆 | 45.8 | 短线降温 | 34.0 | 偏弱 | weak_or_cooling |
| 67 | 福建自贸区 | 45.8 | 短线降温 | 34.0 | 偏弱 | weak_or_cooling |
| 68 | 俄乌冲突概念 | 45.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 69 | 共享单车 | 45.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 70 | 互联网金融 | 45.8 | 短线降温 | 29.2 | 偏弱 | weak_or_cooling |
| 71 | 超超临界发电 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 72 | 代糖概念 | 45.8 | 短线降温 | 27.0 | 偏弱 | weak_or_cooling |
| 73 | 金属钴 | 45.8 | 短线降温 | 23.2 | 偏弱 | weak_or_cooling |
| 74 | 核污染防治 | 42.8 | 短线降温 | 41.0 | 降温 | weak_or_cooling |
| 75 | 广东自贸区 | 42.8 | 短线降温 | 38.0 | 降温 | weak_or_cooling |
| 76 | 海峡两岸 | 42.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 77 | 独角兽概念 | 42.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 78 | 钒电池 | 42.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 79 | 锂电池概念 | 42.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 80 | ETC | 42.8 | 短线降温 | 30.0 | 偏弱 | weak_or_cooling |
| 81 | 动力电池回收 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 82 | 国产操作系统 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 83 | 多模态AI | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 84 | 抖音概念(字节概念) | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 85 | 百度概念 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 86 | 阿里巴巴概念 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 87 | 鸿蒙概念 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 88 | 华为鲲鹏 | 42.8 | 短线降温 | 25.2 | 偏弱 | weak_or_cooling |
| 89 | 电子身份证 | 42.8 | 短线降温 | 25.2 | 偏弱 | weak_or_cooling |
| 90 | 华为欧拉 | 42.8 | 短线降温 | 21.2 | 偏弱 | weak_or_cooling |
| 91 | 宁德时代概念 | 39.8 | 短线降温 | 34.0 | 偏弱 | weak_or_cooling |
| 92 | 光伏概念 | 39.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 93 | 华为概念 | 39.8 | 短线降温 | 32.0 | 偏弱 | weak_or_cooling |
| 94 | 东数西算(算力) | 39.8 | 短线降温 | 30.0 | 偏弱 | weak_or_cooling |
| 95 | 海南自贸区 | 37.3 | 短线降温 | 48.2 | 降温 | weak_or_cooling |
| 96 | AI PC | 36.8 | 短线降温 | 37.2 | 降温 | weak_or_cooling |
| 97 | AI手机 | 36.8 | 短线降温 | 29.2 | 偏弱 | weak_or_cooling |
| 98 | 富士康概念 | 36.8 | 短线降温 | 25.2 | 偏弱 | weak_or_cooling |
| 99 | 丙烯酸 | 34.3 | 短线偏弱 | 55.2 | 中性 | neutral |
| 100 | 化肥 | 34.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 101 | 环氧丙烷 | 34.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 102 | 短剧游戏 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 103 | 电子竞技 | 31.3 | 短线偏弱 | 27.2 | 偏弱 | weak_or_cooling |
| 104 | AI语料 | 31.3 | 短线偏弱 | 12.4 | 偏弱 | weak_or_cooling |
| 105 | 超级电容 | 28.3 | 短线偏弱 | 30.2 | 偏弱 | weak_or_cooling |
| 106 | 固态电池 | 28.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 107 | 氟化工概念 | 27.3 | 短线偏弱 | 55.5 | 中性 | neutral |
| 108 | 存储芯片 | 25.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 109 | 华为海思概念股 | 25.3 | 短线偏弱 | 31.4 | 偏弱 | weak_or_cooling |
| 110 | 超导概念 | 25.3 | 短线偏弱 | 30.2 | 偏弱 | weak_or_cooling |
| 111 | 钙钛矿电池 | 25.3 | 短线偏弱 | 27.2 | 偏弱 | weak_or_cooling |
| 112 | BC电池 | 25.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 113 | 共封装光学(CPO) | 25.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 114 | F5G概念 | 25.3 | 短线偏弱 | 12.4 | 偏弱 | weak_or_cooling |
| 115 | 硅能源 | 24.3 | 短线偏弱 | 36.2 | 降温 | weak_or_cooling |
| 116 | 光刻胶 | 21.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 117 | 第三代半导体 | 21.3 | 短线偏弱 | 38.5 | 降温 | weak_or_cooling |
| 118 | 光刻机 | 21.3 | 短线偏弱 | 35.5 | 降温 | weak_or_cooling |
| 119 | 电子纸 | 21.3 | 短线偏弱 | 35.5 | 降温 | weak_or_cooling |
| 120 | 国家大基金持股 | 21.3 | 短线偏弱 | 34.6 | 偏弱 | weak_or_cooling |

## 分歧板块

当前无明显分歧板块。

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 动物疫苗

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

### 2. 高股息精选

**趋势持续评分**:
- 趋势分: 59.0
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 10.0
  - relative_strength_component: 14.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 3.2
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

### 3. 仿制药一致性评价

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

### 4. 创新药

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

### 5. 合成生物

**趋势持续评分**:
- 趋势分: 58.2
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 8.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
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
