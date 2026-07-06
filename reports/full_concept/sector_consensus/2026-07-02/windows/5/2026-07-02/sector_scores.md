# 板块综合评分

**分析日期**: 2026-07-02
**更新时间**: 2026-07-02T23:29:09.487696

> **免责声明**: 本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。

## 数据来源

- **板块类型**: concept
- **历史数据范围**: 2026-05-20 ~ 2026-07-02
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
| 1 | 丙烯酸 | 78.0 | 观察 | 45.8 | 短线降温 | trend_only |
| 2 | 海南自贸区 | 74.2 | 观察 | 58.8 | 短线中性 | neutral |
| 3 | 氟化工概念 | 73.2 | 观察 | 48.8 | 短线降温 | trend_only |
| 4 | 芬太尼 | 69.2 | 观察 | 55.8 | 短线中性 | neutral |
| 5 | 参股保险 | 69.0 | 观察 | 45.8 | 短线降温 | trend_only |
| 6 | 动物疫苗 | 66.2 | 观察 | 45.8 | 短线降温 | trend_only |
| 7 | 合成生物 | 66.2 | 观察 | 45.8 | 短线降温 | trend_only |
| 8 | 工业大麻 | 66.2 | 观察 | 45.8 | 短线降温 | trend_only |
| 9 | 超级品牌 | 66.0 | 观察 | 45.8 | 短线降温 | trend_only |
| 10 | 仿制药一致性评价 | 64.4 | 中性 | 58.8 | 短线中性 | neutral |
| 11 | 黑龙江自贸区 | 62.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 12 | 创新药 | 61.4 | 中性 | 45.8 | 短线降温 | neutral |
| 13 | 肝炎概念 | 61.4 | 中性 | 45.8 | 短线降温 | neutral |
| 14 | 辅助生殖 | 61.4 | 中性 | 45.8 | 短线降温 | neutral |
| 15 | 阿尔茨海默概念 | 61.4 | 中性 | 45.8 | 短线降温 | neutral |
| 16 | 三胎概念 | 61.2 | 中性 | 45.8 | 短线降温 | neutral |
| 17 | 参股银行 | 61.0 | 中性 | 45.8 | 短线降温 | neutral |
| 18 | 地下管网 | 61.0 | 中性 | 45.8 | 短线降温 | neutral |
| 19 | 大豆 | 61.0 | 中性 | 42.8 | 短线降温 | neutral |
| 20 | 高股息精选 | 61.0 | 中性 | 42.8 | 短线降温 | neutral |
| 21 | 硅能源 | 60.2 | 中性 | 30.3 | 短线偏弱 | neutral |
| 22 | 化肥 | 59.0 | 中性 | 45.8 | 短线降温 | neutral |
| 23 | 固废处理 | 59.0 | 中性 | 45.8 | 短线降温 | neutral |
| 24 | 短剧游戏 | 59.0 | 中性 | 45.8 | 短线降温 | neutral |
| 25 | 航运概念 | 59.0 | 中性 | 45.8 | 短线降温 | neutral |
| 26 | 黄金概念 | 59.0 | 中性 | 45.8 | 短线降温 | neutral |
| 27 | 光刻胶 | 57.5 | 中性 | 30.3 | 短线偏弱 | neutral |
| 28 | 共同富裕示范区 | 57.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 29 | 国企改革 | 57.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 30 | 福建自贸区 | 55.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 31 | 环氧丙烷 | 55.0 | 中性 | 55.8 | 短线中性 | neutral |
| 32 | 电子纸 | 54.6 | 中性 | 30.3 | 短线偏弱 | neutral |
| 33 | 猴痘概念 | 50.6 | 中性 | 34.3 | 短线偏弱 | neutral |
| 34 | 重组蛋白 | 50.6 | 中性 | 34.3 | 短线偏弱 | neutral |
| 35 | 宠物经济 | 50.5 | 中性 | 34.3 | 短线偏弱 | neutral |
| 36 | 供销社 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 37 | 俄乌冲突概念 | 50.2 | 中性 | 31.3 | 短线偏弱 | neutral |
| 38 | 共享单车 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 39 | 冰雪产业 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 40 | 参股券商 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 41 | 国产航母 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 42 | 核电 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 43 | 电子竞技 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 44 | 白酒概念 | 50.2 | 中性 | 31.3 | 短线偏弱 | neutral |
| 45 | 股权转让(并购重组) | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 46 | 长三角一体化 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 47 | 高端装备 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 48 | 高铁 | 50.2 | 中性 | 34.3 | 短线偏弱 | neutral |
| 49 | 金属钴 | 49.2 | 降温 | 45.8 | 短线降温 | weak_or_cooling |
| 50 | 草甘膦 | 49.0 | 降温 | 42.8 | 短线降温 | weak_or_cooling |
| 51 | 高压氧舱 | 48.5 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 52 | 低空经济 | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 53 | 军工 | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 54 | 创投 | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 55 | 华为汽车 | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 56 | 大飞机 | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 57 | 工业互联网 | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 58 | 核污染防治 | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 59 | 航空发动机 | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 60 | 长安汽车概念 | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 61 | 飞行汽车(eVTOL) | 48.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 62 | 超超临界发电 | 47.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 63 | 传感器 | 45.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 64 | 安防 | 45.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 65 | 工业母机 | 45.5 | 降温 | 37.3 | 短线降温 | weak_or_cooling |
| 66 | 车联网(车路协同) | 45.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 67 | 广东自贸区 | 45.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 68 | 海峡两岸 | 45.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 69 | 独角兽概念 | 45.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 70 | 锂电池概念 | 45.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 71 | ERP概念 | 42.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 72 | 互联网金融 | 42.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 73 | 华为欧拉 | 42.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 74 | 华为鲲鹏 | 42.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 75 | 国资云 | 42.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 76 | 多模态AI | 42.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 77 | 抖音概念(字节概念) | 42.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 78 | 比亚迪概念 | 42.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 79 | 百度概念 | 42.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 80 | 阿里巴巴概念 | 42.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 81 | 鸿蒙概念 | 42.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 82 | 光伏概念 | 42.2 | 降温 | 27.3 | 短线偏弱 | weak_or_cooling |
| 83 | 光热发电 | 42.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 84 | 抽水蓄能 | 42.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 85 | 钒电池 | 42.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 86 | AI语料 | 41.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 87 | 光刻机 | 40.6 | 降温 | 24.3 | 短线偏弱 | weak_or_cooling |
| 88 | 存储芯片 | 40.6 | 降温 | 24.3 | 短线偏弱 | weak_or_cooling |
| 89 | BC电池 | 40.5 | 降温 | 27.3 | 短线偏弱 | weak_or_cooling |
| 90 | 第三代半导体 | 40.5 | 降温 | 27.3 | 短线偏弱 | weak_or_cooling |
| 91 | ETC | 40.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 92 | 储能 | 40.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 93 | 充电桩 | 40.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 94 | 成飞概念 | 40.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 95 | 换电概念 | 40.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 96 | 横琴新区 | 40.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 97 | 海工装备 | 40.2 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 98 | 风电 | 40.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 99 | 代糖概念 | 38.2 | 降温 | 31.3 | 短线偏弱 | weak_or_cooling |
| 100 | EDR概念 | 37.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 101 | 东数西算(算力) | 37.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 102 | 华为概念 | 37.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 103 | 固态电池 | 37.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 104 | 国产操作系统 | 37.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 105 | 宁德时代概念 | 37.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 106 | 电力物联网 | 37.5 | 降温 | 30.3 | 短线偏弱 | weak_or_cooling |
| 107 | 超导概念 | 37.5 | 降温 | 24.3 | 短线偏弱 | weak_or_cooling |
| 108 | 高压快充 | 37.5 | 降温 | 34.3 | 短线偏弱 | weak_or_cooling |
| 109 | 国家大基金持股 | 36.6 | 降温 | 24.3 | 短线偏弱 | weak_or_cooling |
| 110 | 华为海思概念股 | 34.6 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 111 | 电子身份证 | 33.5 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 112 | 超级电容 | 33.5 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 113 | 钙钛矿电池 | 33.5 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 114 | 动力电池回收 | 29.4 | 偏弱 | 34.3 | 短线偏弱 | weak_or_cooling |
| 115 | AI PC | 27.6 | 偏弱 | 30.3 | 短线偏弱 | weak_or_cooling |
| 116 | 毫米波雷达 | 25.4 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 117 | AI手机 | 15.7 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 118 | 富士康概念 | 15.7 | 偏弱 | 27.3 | 短线偏弱 | weak_or_cooling |
| 119 | F5G概念 | 11.7 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |
| 120 | 共封装光学(CPO) | 11.7 | 偏弱 | 24.3 | 短线偏弱 | weak_or_cooling |

## 短线爆发 Top 120

| 排名 | 板块 | 短线分 | 短线等级 | 趋势分 | 趋势等级 | Profile |
|------|------|--------|----------|--------|----------|---------|
| 1 | 海南自贸区 | 58.8 | 短线中性 | 74.2 | 观察 | neutral |
| 2 | 仿制药一致性评价 | 58.8 | 短线中性 | 64.4 | 中性 | neutral |
| 3 | 芬太尼 | 55.8 | 短线中性 | 69.2 | 观察 | neutral |
| 4 | 环氧丙烷 | 55.8 | 短线中性 | 55.0 | 中性 | neutral |
| 5 | 氟化工概念 | 48.8 | 短线降温 | 73.2 | 观察 | trend_only |
| 6 | 丙烯酸 | 45.8 | 短线降温 | 78.0 | 观察 | trend_only |
| 7 | 参股保险 | 45.8 | 短线降温 | 69.0 | 观察 | trend_only |
| 8 | 动物疫苗 | 45.8 | 短线降温 | 66.2 | 观察 | trend_only |
| 9 | 合成生物 | 45.8 | 短线降温 | 66.2 | 观察 | trend_only |
| 10 | 工业大麻 | 45.8 | 短线降温 | 66.2 | 观察 | trend_only |
| 11 | 超级品牌 | 45.8 | 短线降温 | 66.0 | 观察 | trend_only |
| 12 | 创新药 | 45.8 | 短线降温 | 61.4 | 中性 | neutral |
| 13 | 肝炎概念 | 45.8 | 短线降温 | 61.4 | 中性 | neutral |
| 14 | 辅助生殖 | 45.8 | 短线降温 | 61.4 | 中性 | neutral |
| 15 | 阿尔茨海默概念 | 45.8 | 短线降温 | 61.4 | 中性 | neutral |
| 16 | 三胎概念 | 45.8 | 短线降温 | 61.2 | 中性 | neutral |
| 17 | 参股银行 | 45.8 | 短线降温 | 61.0 | 中性 | neutral |
| 18 | 地下管网 | 45.8 | 短线降温 | 61.0 | 中性 | neutral |
| 19 | 化肥 | 45.8 | 短线降温 | 59.0 | 中性 | neutral |
| 20 | 固废处理 | 45.8 | 短线降温 | 59.0 | 中性 | neutral |
| 21 | 短剧游戏 | 45.8 | 短线降温 | 59.0 | 中性 | neutral |
| 22 | 航运概念 | 45.8 | 短线降温 | 59.0 | 中性 | neutral |
| 23 | 黄金概念 | 45.8 | 短线降温 | 59.0 | 中性 | neutral |
| 24 | 金属钴 | 45.8 | 短线降温 | 49.2 | 降温 | weak_or_cooling |
| 25 | 大豆 | 42.8 | 短线降温 | 61.0 | 中性 | neutral |
| 26 | 高股息精选 | 42.8 | 短线降温 | 61.0 | 中性 | neutral |
| 27 | 草甘膦 | 42.8 | 短线降温 | 49.0 | 降温 | weak_or_cooling |
| 28 | 工业母机 | 37.3 | 短线降温 | 45.5 | 降温 | weak_or_cooling |
| 29 | 黑龙江自贸区 | 34.3 | 短线偏弱 | 62.2 | 中性 | neutral |
| 30 | 共同富裕示范区 | 34.3 | 短线偏弱 | 57.2 | 中性 | neutral |
| 31 | 国企改革 | 34.3 | 短线偏弱 | 57.2 | 中性 | neutral |
| 32 | 福建自贸区 | 34.3 | 短线偏弱 | 55.2 | 中性 | neutral |
| 33 | 猴痘概念 | 34.3 | 短线偏弱 | 50.6 | 中性 | neutral |
| 34 | 重组蛋白 | 34.3 | 短线偏弱 | 50.6 | 中性 | neutral |
| 35 | 宠物经济 | 34.3 | 短线偏弱 | 50.5 | 中性 | neutral |
| 36 | 供销社 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 37 | 共享单车 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 38 | 冰雪产业 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 39 | 参股券商 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 40 | 国产航母 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 41 | 核电 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 42 | 电子竞技 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 43 | 股权转让(并购重组) | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 44 | 长三角一体化 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 45 | 高端装备 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 46 | 高铁 | 34.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 47 | 低空经济 | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 48 | 军工 | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 49 | 创投 | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 50 | 华为汽车 | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 51 | 大飞机 | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 52 | 工业互联网 | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 53 | 核污染防治 | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 54 | 航空发动机 | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 55 | 长安汽车概念 | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 56 | 飞行汽车(eVTOL) | 34.3 | 短线偏弱 | 48.2 | 降温 | weak_or_cooling |
| 57 | 传感器 | 34.3 | 短线偏弱 | 45.5 | 降温 | weak_or_cooling |
| 58 | 车联网(车路协同) | 34.3 | 短线偏弱 | 45.5 | 降温 | weak_or_cooling |
| 59 | 广东自贸区 | 34.3 | 短线偏弱 | 45.2 | 降温 | weak_or_cooling |
| 60 | 海峡两岸 | 34.3 | 短线偏弱 | 45.2 | 降温 | weak_or_cooling |
| 61 | 独角兽概念 | 34.3 | 短线偏弱 | 45.2 | 降温 | weak_or_cooling |
| 62 | 锂电池概念 | 34.3 | 短线偏弱 | 45.2 | 降温 | weak_or_cooling |
| 63 | ERP概念 | 34.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 64 | 互联网金融 | 34.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 65 | 华为欧拉 | 34.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 66 | 华为鲲鹏 | 34.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 67 | 国资云 | 34.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 68 | 多模态AI | 34.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 69 | 抖音概念(字节概念) | 34.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 70 | 比亚迪概念 | 34.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 71 | 百度概念 | 34.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 72 | 阿里巴巴概念 | 34.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 73 | 鸿蒙概念 | 34.3 | 短线偏弱 | 42.5 | 降温 | weak_or_cooling |
| 74 | AI语料 | 34.3 | 短线偏弱 | 41.5 | 降温 | weak_or_cooling |
| 75 | 储能 | 34.3 | 短线偏弱 | 40.2 | 降温 | weak_or_cooling |
| 76 | 充电桩 | 34.3 | 短线偏弱 | 40.2 | 降温 | weak_or_cooling |
| 77 | 成飞概念 | 34.3 | 短线偏弱 | 40.2 | 降温 | weak_or_cooling |
| 78 | 换电概念 | 34.3 | 短线偏弱 | 40.2 | 降温 | weak_or_cooling |
| 79 | 海工装备 | 34.3 | 短线偏弱 | 40.2 | 降温 | weak_or_cooling |
| 80 | 固态电池 | 34.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 81 | 国产操作系统 | 34.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 82 | 宁德时代概念 | 34.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 83 | 高压快充 | 34.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 84 | 动力电池回收 | 34.3 | 短线偏弱 | 29.4 | 偏弱 | weak_or_cooling |
| 85 | 俄乌冲突概念 | 31.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 86 | 白酒概念 | 31.3 | 短线偏弱 | 50.2 | 中性 | neutral |
| 87 | 高压氧舱 | 31.3 | 短线偏弱 | 48.5 | 降温 | weak_or_cooling |
| 88 | 超超临界发电 | 31.3 | 短线偏弱 | 47.2 | 降温 | weak_or_cooling |
| 89 | 光热发电 | 31.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 90 | 抽水蓄能 | 31.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 91 | 钒电池 | 31.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 92 | ETC | 31.3 | 短线偏弱 | 40.2 | 降温 | weak_or_cooling |
| 93 | 横琴新区 | 31.3 | 短线偏弱 | 40.2 | 降温 | weak_or_cooling |
| 94 | 风电 | 31.3 | 短线偏弱 | 40.2 | 降温 | weak_or_cooling |
| 95 | 代糖概念 | 31.3 | 短线偏弱 | 38.2 | 降温 | weak_or_cooling |
| 96 | 硅能源 | 30.3 | 短线偏弱 | 60.2 | 中性 | neutral |
| 97 | 光刻胶 | 30.3 | 短线偏弱 | 57.5 | 中性 | neutral |
| 98 | 电子纸 | 30.3 | 短线偏弱 | 54.6 | 中性 | neutral |
| 99 | 安防 | 30.3 | 短线偏弱 | 45.5 | 降温 | weak_or_cooling |
| 100 | EDR概念 | 30.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 101 | 东数西算(算力) | 30.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 102 | 华为概念 | 30.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 103 | 电力物联网 | 30.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 104 | 华为海思概念股 | 30.3 | 短线偏弱 | 34.6 | 偏弱 | weak_or_cooling |
| 105 | 电子身份证 | 30.3 | 短线偏弱 | 33.5 | 偏弱 | weak_or_cooling |
| 106 | AI PC | 30.3 | 短线偏弱 | 27.6 | 偏弱 | weak_or_cooling |
| 107 | 光伏概念 | 27.3 | 短线偏弱 | 42.2 | 降温 | weak_or_cooling |
| 108 | BC电池 | 27.3 | 短线偏弱 | 40.5 | 降温 | weak_or_cooling |
| 109 | 第三代半导体 | 27.3 | 短线偏弱 | 40.5 | 降温 | weak_or_cooling |
| 110 | 超级电容 | 27.3 | 短线偏弱 | 33.5 | 偏弱 | weak_or_cooling |
| 111 | 钙钛矿电池 | 27.3 | 短线偏弱 | 33.5 | 偏弱 | weak_or_cooling |
| 112 | 毫米波雷达 | 27.3 | 短线偏弱 | 25.4 | 偏弱 | weak_or_cooling |
| 113 | AI手机 | 27.3 | 短线偏弱 | 15.7 | 偏弱 | weak_or_cooling |
| 114 | 富士康概念 | 27.3 | 短线偏弱 | 15.7 | 偏弱 | weak_or_cooling |
| 115 | 光刻机 | 24.3 | 短线偏弱 | 40.6 | 降温 | weak_or_cooling |
| 116 | 存储芯片 | 24.3 | 短线偏弱 | 40.6 | 降温 | weak_or_cooling |
| 117 | 超导概念 | 24.3 | 短线偏弱 | 37.5 | 降温 | weak_or_cooling |
| 118 | 国家大基金持股 | 24.3 | 短线偏弱 | 36.6 | 降温 | weak_or_cooling |
| 119 | F5G概念 | 24.3 | 短线偏弱 | 11.7 | 偏弱 | weak_or_cooling |
| 120 | 共封装光学(CPO) | 24.3 | 短线偏弱 | 11.7 | 偏弱 | weak_or_cooling |

## 分歧板块

### 趋势强但短线不热

| 板块 | 趋势分 | 短线分 | 说明 |
|------|--------|--------|------|
| 丙烯酸 | 78.0 | 45.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 氟化工概念 | 73.2 | 48.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 参股保险 | 69.0 | 45.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 动物疫苗 | 66.2 | 45.8 | 趋势强但短线不热，中长期趋势观察价值较高 |
| 合成生物 | 66.2 | 45.8 | 趋势强但短线不热，中长期趋势观察价值较高 |

## 风险提示

- 短线爆发不等于趋势确认
- 仅用于复盘观察，仅用于复盘观察
- 短线爆发需要观察次日是否持续

## 评分详情

### 1. 丙烯酸

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

### 2. 海南自贸区

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

### 3. 氟化工概念

**趋势持续评分**:
- 趋势分: 73.2
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 15.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
  - drawdown_component: 6.0
  - volatility_component: 2.4
  - data_quality_component: 6.4
  - risk_penalty: 2.0

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

### 4. 芬太尼

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

### 5. 参股保险

**趋势持续评分**:
- 趋势分: 69.0
- 趋势等级: 观察
- 趋势 breakdown:
  - radar_score_component: 5.4
  - momentum_component: 10.0
  - relative_strength_component: 20.0
  - persistence_component: 20.0
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
- Profile: trend_only
- Summary: 趋势强但短线不热，中长期趋势观察价值较高
- Watch points:
  - 趋势持续性好，但短线缺乏爆发力
  - 观察是否有催化剂推动短线表现

## 数据质量

- **整体数据质量分**: 0/100

## 声明

本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
