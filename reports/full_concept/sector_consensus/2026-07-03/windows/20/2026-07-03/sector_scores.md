# 板块综合评分

**分析日期**: 2026-07-03
**更新时间**: 2026-07-03T19:45:47.982129

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
| 1 | 氟化工概念 | 66.2 | 观察 | 48.8 | 短线降温 | trend_only |
| 2 | 光刻胶 | 62.5 | 中性 | 30.3 | 短线偏弱 | neutral |
| 3 | 动物疫苗 | 59.0 | 中性 | 45.8 | 短线降温 | neutral |
| 4 | 丙烯酸 | 55.0 | 中性 | 45.8 | 短线降温 | neutral |
| 5 | 国家大基金持股 | 53.6 | 中性 | 24.3 | 短线偏弱 | neutral |
| 6 | 存储芯片 | 53.6 | 中性 | 24.3 | 短线偏弱 | neutral |
| 7 | 硅能源 | 53.2 | 中性 | 30.3 | 短线偏弱 | neutral |
| 8 | 环氧丙烷 | 53.0 | 中性 | 55.8 | 短线中性 | neutral |
| 9 | 光刻机 | 51.5 | 中性 | 24.3 | 短线偏弱 | neutral |
| 10 | 第三代半导体 | 51.5 | 中性 | 27.3 | 短线偏弱 | neutral |
| 11 | 传感器 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 12 | 阿尔茨海默概念 | 47.2 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 13 | 合成生物 | 47.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 14 | 富士康概念 | 46.5 | 降温 | 27.3 | 短线偏弱 | weak_or_cooling |
| 15 | 电子纸 | 46.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 16 | 超级电容 | 46.5 | 降温 | 27.3 | 短线偏弱 | weak_or_cooling |
| 17 | 仿制药一致性评价 | 45.2 | 降温 | 58.8 | 短线中性 | neutral |
| 18 | 创新药 | 45.2 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 19 | 重组蛋白 | 44.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 20 | 工业母机 | 44.2 | 降温 | 37.3 | 短线降温 | weak_or_cooling |
| 21 | 共封装光学(CPO) | 43.6 | 降温 | 24.3 | 短线偏弱 | weak_or_cooling |
| 22 | 华为海思概念股 | 43.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 23 | 固态电池 | 43.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 24 | 核污染防治 | 43.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 25 | 钙钛矿电池 | 42.5 | 降温 | 27.3 | 短线偏弱 | weak_or_cooling |
| 26 | 辅助生殖 | 42.2 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 27 | AI手机 | 41.5 | 降温 | 27.3 | 短线偏弱 | weak_or_cooling |
| 28 | 锂电池概念 | 41.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 29 | 芬太尼 | 40.0 | 降温 | 55.8 | 短线中性 | neutral |
| 30 | AI PC | 38.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 31 | 猴痘概念 | 38.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 32 | 航空发动机 | 38.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 33 | 肝炎概念 | 38.2 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 34 | 超导概念 | 36.5 | 降温 | 24.3 | 短线偏弱 | weak_or_cooling |
| 35 | 宁德时代概念 | 35.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 36 | 工业大麻 | 35.0 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 37 | 比亚迪概念 | 34.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 38 | 海南自贸区 | 34.0 | 偏弱 | 58.8 | 短线中性 | neutral |
| 39 | BC电池 | 33.5 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 40 | 毫米波雷达 | 31.4 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 41 | 军工 | 30.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 42 | 华为概念 | 30.2 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 43 | 光伏概念 | 28.2 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 44 | 大飞机 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 45 | 安防 | 28.2 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 46 | 成飞概念 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 47 | 长三角一体化 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 48 | 飞行汽车(eVTOL) | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 49 | 高端装备 | 28.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 50 | 化肥 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 51 | 参股保险 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 52 | 参股银行 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 53 | 固废处理 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 54 | 草甘膦 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 55 | 超级品牌 | 28.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 56 | 高股息精选 | 28.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 57 | 金属钴 | 27.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 58 | ETC | 26.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 59 | 东数西算(算力) | 26.2 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 60 | 国产操作系统 | 26.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 61 | 黄金概念 | 25.2 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 62 | 低空经济 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 63 | 供销社 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 64 | 共同富裕示范区 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 65 | 创投 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 66 | 参股券商 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 67 | 国产航母 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 68 | 国企改革 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 69 | 多模态AI | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 70 | 宠物经济 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 71 | 工业互联网 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 72 | 广东自贸区 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 73 | 抖音概念(字节概念) | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 74 | 核电 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 75 | 横琴新区 | 24.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 76 | 海峡两岸 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 77 | 海工装备 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 78 | 独角兽概念 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 79 | 电子竞技 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 80 | 福建自贸区 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 81 | 股权转让(并购重组) | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 82 | 车联网(车路协同) | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 83 | 高压快充 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 84 | 高压氧舱 | 24.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 85 | 高铁 | 24.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 86 | 三胎概念 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 87 | 地下管网 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 88 | 短剧游戏 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 89 | 航运概念 | 24.0 | 偏弱 | 45.8 | 短线降温 | weak_or_cooling |
| 90 | EDR概念 | 21.4 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 91 | 互联网金融 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 92 | 共享单车 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 93 | 冰雪产业 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 94 | 华为欧拉 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 95 | 华为鲲鹏 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 96 | 国资云 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 97 | 换电概念 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 98 | 电力物联网 | 20.2 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 99 | 电子身份证 | 20.2 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 100 | 百度概念 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 101 | 阿里巴巴概念 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 102 | 鸿蒙概念 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 103 | 黑龙江自贸区 | 20.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 104 | 代糖概念 | 19.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 105 | 俄乌冲突概念 | 19.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 106 | 储能 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 107 | 充电桩 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 108 | 动力电池回收 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 109 | 华为汽车 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 110 | 钒电池 | 19.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 111 | 长安汽车概念 | 19.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 112 | 风电 | 19.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 113 | F5G概念 | 18.6 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |
| 114 | AI语料 | 17.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 115 | 大豆 | 17.0 | 偏弱 | 42.8 | 短线降温 | weak_or_cooling |
| 116 | ERP概念 | 15.2 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 117 | 光热发电 | 15.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 118 | 抽水蓄能 | 15.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 119 | 白酒概念 | 15.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |
| 120 | 超超临界发电 | 11.2 | 偏弱 | 31.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 120

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 仿制药一致性评价 | 58.8 | 短线中性 | 45.2 | 降温 | neutral |
| 2 | 海南自贸区 | 58.8 | 短线中性 | 34.0 | 偏弱 | neutral |
| 3 | 环氧丙烷 | 55.8 | 短线中性 | 53.0 | 中性 | neutral |
| 4 | 芬太尼 | 55.8 | 短线中性 | 40.0 | 降温 | neutral |
| 5 | 氟化工概念 | 48.8 | 短线降温 | 66.2 | 观察 | trend_only |
| 6 | 动物疫苗 | 45.8 | 短线降温 | 59.0 | 中性 | neutral |
| 7 | 丙烯酸 | 45.8 | 短线降温 | 55.0 | 中性 | neutral |
| 8 | 阿尔茨海默概念 | 45.8 | 短线降温 | 47.2 | 降温 | weak_or_cooling |
| 9 | 合成生物 | 45.8 | 短线降温 | 47.0 | 降温 | weak_or_cooling |
| 10 | 创新药 | 45.8 | 短线降温 | 45.2 | 降温 | weak_or_cooling |
| 11 | 辅助生殖 | 45.8 | 短线降温 | 42.2 | 降温 | weak_or_cooling |
| 12 | 肝炎概念 | 45.8 | 短线降温 | 38.2 | 降温 | weak_or_cooling |
| 13 | 工业大麻 | 45.8 | 短线降温 | 35.0 | 降温 | weak_or_cooling |
| 14 | 化肥 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 15 | 参股保险 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 16 | 参股银行 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 17 | 固废处理 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 18 | 超级品牌 | 45.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 19 | 金属钴 | 45.8 | 短线降温 | 27.2 | 偏弱 | weak_or_cooling |
| 20 | 黄金概念 | 45.8 | 短线降温 | 25.2 | 偏弱 | weak_or_cooling |
| 21 | 三胎概念 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 22 | 地下管网 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 23 | 短剧游戏 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 24 | 航运概念 | 45.8 | 短线降温 | 24.0 | 偏弱 | weak_or_cooling |
| 25 | 草甘膦 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 26 | 高股息精选 | 42.8 | 短线降温 | 28.0 | 偏弱 | weak_or_cooling |
| 27 | 大豆 | 42.8 | 短线降温 | 17.0 | 偏弱 | weak_or_cooling |
| 28 | 工业母机 | 37.3 | 短线降温 | 44.2 | 降温 | weak_or_cooling |
| 29 | 传感器 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 30 | 重组蛋白 | 34.3 | 短线偏弱 | 44.5 | 降温 | weak_or_cooling |
| 31 | 固态电池 | 34.3 | 短线偏弱 | 43.5 | 降温 | weak_or_cooling |
| 32 | 核污染防治 | 34.3 | 短线偏弱 | 43.2 | 降温 | weak_or_cooling |
| 33 | 锂电池概念 | 34.3 | 短线偏弱 | 41.2 | 降温 | weak_or_cooling |
| 34 | 猴痘概念 | 34.3 | 短线偏弱 | 38.5 | 降温 | weak_or_cooling |
| 35 | 航空发动机 | 34.3 | 短线偏弱 | 38.2 | 降温 | weak_or_cooling |
| 36 | 宁德时代概念 | 34.3 | 短线偏弱 | 35.5 | 降温 | weak_or_cooling |
| 37 | 比亚迪概念 | 34.3 | 短线偏弱 | 34.2 | 偏弱 | weak_or_cooling |
| 38 | 军工 | 34.3 | 短线偏弱 | 30.2 | 偏弱 | weak_or_cooling |
| 39 | 大飞机 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 40 | 成飞概念 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 41 | 长三角一体化 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 42 | 飞行汽车(eVTOL) | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 43 | 高端装备 | 34.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 44 | 国产操作系统 | 34.3 | 短线偏弱 | 26.2 | 偏弱 | weak_or_cooling |
| 45 | 低空经济 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 46 | 供销社 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 47 | 共同富裕示范区 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 48 | 创投 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 49 | 参股券商 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 50 | 国产航母 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 51 | 国企改革 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 52 | 多模态AI | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 53 | 宠物经济 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 54 | 工业互联网 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 55 | 广东自贸区 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 56 | 抖音概念(字节概念) | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 57 | 核电 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 58 | 海峡两岸 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 59 | 海工装备 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 60 | 独角兽概念 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 61 | 电子竞技 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 62 | 福建自贸区 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 63 | 股权转让(并购重组) | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 64 | 车联网(车路协同) | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 65 | 高压快充 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 66 | 高铁 | 34.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 67 | 互联网金融 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 68 | 共享单车 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 69 | 冰雪产业 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 70 | 华为欧拉 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 71 | 华为鲲鹏 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 72 | 国资云 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 73 | 换电概念 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 74 | 百度概念 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 75 | 阿里巴巴概念 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 76 | 鸿蒙概念 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 77 | 黑龙江自贸区 | 34.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 78 | 储能 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 79 | 充电桩 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 80 | 动力电池回收 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 81 | 华为汽车 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 82 | 长安汽车概念 | 34.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 83 | AI语料 | 34.3 | 短线偏弱 | 17.4 | 偏弱 | weak_or_cooling |
| 84 | ERP概念 | 34.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 85 | ETC | 31.3 | 短线偏弱 | 26.2 | 偏弱 | weak_or_cooling |
| 86 | 横琴新区 | 31.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 87 | 高压氧舱 | 31.3 | 短线偏弱 | 24.2 | 偏弱 | weak_or_cooling |
| 88 | 代糖概念 | 31.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 89 | 俄乌冲突概念 | 31.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 90 | 钒电池 | 31.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 91 | 风电 | 31.3 | 短线偏弱 | 19.2 | 偏弱 | weak_or_cooling |
| 92 | 光热发电 | 31.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 93 | 抽水蓄能 | 31.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 94 | 白酒概念 | 31.3 | 短线偏弱 | 15.2 | 偏弱 | weak_or_cooling |
| 95 | 超超临界发电 | 31.3 | 短线偏弱 | 11.2 | 偏弱 | weak_or_cooling |
| 96 | 光刻胶 | 30.3 | 短线偏弱 | 62.5 | 中性 | neutral |
| 97 | 硅能源 | 30.3 | 短线偏弱 | 53.2 | 中性 | neutral |
| 98 | 电子纸 | 30.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 99 | 华为海思概念股 | 30.3 | 短线偏弱 | 43.5 | 降温 | weak_or_cooling |
| 100 | AI PC | 30.3 | 短线偏弱 | 38.5 | 降温 | weak_or_cooling |
| 101 | 华为概念 | 30.3 | 短线偏弱 | 30.2 | 偏弱 | weak_or_cooling |
| 102 | 安防 | 30.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 103 | 东数西算(算力) | 30.3 | 短线偏弱 | 26.2 | 偏弱 | weak_or_cooling |
| 104 | EDR概念 | 30.3 | 短线偏弱 | 21.4 | 偏弱 | weak_or_cooling |
| 105 | 电力物联网 | 30.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 106 | 电子身份证 | 30.3 | 短线偏弱 | 20.2 | 偏弱 | weak_or_cooling |
| 107 | 第三代半导体 | 27.3 | 短线偏弱 | 51.5 | 中性 | neutral |
| 108 | 富士康概念 | 27.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 109 | 超级电容 | 27.3 | 短线偏弱 | 46.5 | 降温 | weak_or_cooling |
| 110 | 钙钛矿电池 | 27.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 111 | AI手机 | 27.3 | 短线偏弱 | 41.5 | 降温 | weak_or_cooling |
| 112 | BC电池 | 27.3 | 短线偏弱 | 33.5 | 偏弱 | weak_or_cooling |
| 113 | 毫米波雷达 | 27.3 | 短线偏弱 | 31.4 | 偏弱 | weak_or_cooling |
| 114 | 光伏概念 | 27.3 | 短线偏弱 | 28.2 | 偏弱 | weak_or_cooling |
| 115 | 国家大基金持股 | 24.3 | 短线偏弱 | 53.6 | 中性 | neutral |
| 116 | 存储芯片 | 24.3 | 短线偏弱 | 53.6 | 中性 | neutral |
| 117 | 光刻机 | 24.3 | 短线偏弱 | 51.5 | 中性 | neutral |
| 118 | 共封装光学(CPO) | 24.3 | 短线偏弱 | 43.6 | 降温 | weak_or_cooling |
| 119 | 超导概念 | 24.3 | 短线偏弱 | 36.5 | 降温 | weak_or_cooling |
| 120 | F5G概念 | 24.3 | 短线偏弱 | 18.6 | 偏弱 | weak_or_cooling |

## 分歧板块

### 趋势强但短线不热

| 板块 | 趋势分 | 短线分 | 说明 |
|------|--------|--------|------|
| 氟化工概念 | 66.2 | 48.8 | 趋势强但短线不热，中长期趋势观察价值较高 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 氟化工概念

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

### 2. 光刻胶

**趋势持续评分**:
- 趋势分: 62.5
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 1.6
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 15.0
  - drawdown_component: 6.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 4.0

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
- 趋势分: 59.0
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 10.0
  - relative_strength_component: 17.0
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
- 趋势分: 55.0
- 趋势等级: 中性
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 10.0
  - relative_strength_component: 17.0
  - persistence_component: 15.0
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

### 5. 国家大基金持股

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
- 短线分: 24.3
- 短线等级: 短线偏弱
- 短线 breakdown:
  - radar_today_component: 3.3
  - one_day_change_component: 0.0
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

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
