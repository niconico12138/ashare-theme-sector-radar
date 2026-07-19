# 行业方向三层 Shadow 分解设计

日期：2026-07-17

## 目标与边界

- 保持数据层、Path A/B/C、板块到个股桥接架构不变。
- 三层结果仅作为行业 Path A 的 paper/shadow research 分解，不替换正式行业 `score`、`positive_score`、风险扣分、排序或关注等级。
- 不连接券商，不生成实盘指令，不修改 `final_score`、`v2_score`、`selection_score`、`selection_score_adjusted`。
- 复用 Phase 8 与 PIT 回放已有的 as-of 行业历史输入，不读取未来标签或未来收盘价。

## 三层定义

### 1. 时序状态层

满 20 个完成收益后可用，满分 100：

```text
25% 正向趋势拟合度
20% 连续突破质量
15% 最近10日上涨比例
10% 最近20日上涨比例
15% 20日回撤控制
15% 20日复合收益强度
```

该层只描述板块自身的连续状态，不消费横截面百分位。

### 2. 截面强度层

```text
35% 5日复合收益横截面百分位
35% 10日复合收益横截面百分位
30% 20日复合收益横截面百分位
```

百分位沿用现有同窗口签名、平均秩和覆盖门槛。窗口不足时标记 `partial` 或 `unavailable`，不伪造完整分。

### 3. 排名动量层

至少需要 5 个滚动 5 日收益横截面排名端点，使用最近 5 个端点：

```text
30% 当前百分位
35% 五端点斜率
15% 最近变化相对前三步均值的加速度
20% Top25% 驻留率
```

排名历史不足时综合方向分必须为 `None`。

## 综合与状态

```text
direction_score_shadow
= 50% time_series
+ 30% cross_section
+ 20% rank_momentum
```

三层全部可用才计算综合分。状态机仅用于研究解释：`emerging_acceleration`、`stable_core`、`risk_observation`、`pulse_confirmation_required`、`trend_weakening`、`weakening`、`watch`、`unavailable`。风险标志可把强方向标记为 `risk_observation`，但不得改变综合方向分。

## 接入与故障隔离

- 日常 ranking 将结果写入行业 `score_breakdown.three_layer_shadow`；概念评分不接入。
- `industry_trend_history` 汇总全体成功评分行业的 shadow 可用数、状态计数和计算错误数，不受 Top N 截断。
- PIT 样本自然持久化相同 breakdown；JSON 报告原样保留该对象。
- PIT `sample_manifest_sha256` 绑定每条样本的完整 `three_layer_shadow`；修改分数、状态或权重都会改变 manifest。
- 排名端点使用固定 10 槽 shadow 序列，缺失端点保留为 `None`，最近 5 槽不完整时不计算排名动量。既有正式 persistence 仍消费原 `daily_rank_percentiles`，正式确定性并列排序基线不变。
- 最终 `RadarReport` 与 JSON 报告持久化全体成功行业的 shadow 可用数、状态计数和错误数。
- 非有限输入 fail closed。shadow 计算异常只产生固定的 `unavailable/calculation_failed` 研究结构，不得移除正式行业、增加正式 warning 或改变正式报告状态。
- 有限原始输入若在财富路径、复合收益、复用 helper 或综合计算中产生 `NaN/Infinity`，同样 fail closed，不得由 `_clip` 伪装成边界高分。
- 日收益可信域统一为 `(-100%, +100%]`；正收盘价不可能产生 `-100%`，A 股行业日频收益不接受超过 `+100%` 的异常输入。loader、CLI、ranking、PIT 与 shadow 使用同一验证器。
- returns/dates/periods 轴必须可迭代、长度一致；日期必须为唯一且严格递增的 ISO 日期，period 必须由连续 ISO 端点组成并与 dates 对齐。截面及排名百分位必须位于 `[0, 1]`，越界输入直接降级，不裁剪成有效分。
- 生产 JSON 与 raw snapshot 保存入口先以 `allow_nan=False` 完整序列化，再写同目录临时文件，flush/fsync 后原子替换；失败时清理临时文件并保留旧目标。
- Path A PIT JSON、配套 Markdown、CLI 运行日志、研究 JSON 和索引输出统一使用公共原子 writer，替换失败保留旧目标。

## 晋级约束

本轮只建立可解释分解和可信数据合同，不声称提高历史收益或具备 OOS 证据。任何未来替换正式分的提案仍需独立预注册、历史版本化行业宇宙、walk-forward 稳定性和全新盲测门禁。
