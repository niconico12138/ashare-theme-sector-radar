# 行业方向三层 Shadow 分解结果

日期：2026-07-17

## 实现结果

- 新增 `industry_three_layer_shadow.py`，提供时序状态、截面强度、排名动量和 `50/30/20` 综合方向分。
- 行业 ranking、JSON 报告与 PIT 样本已接入；概念评分、正式行业分、风险扣分、排序和关注等级保持不变。
- 新增 shadow 覆盖率、状态分布和错误数元数据。
- shadow 计算故障已与正式评分隔离；非有限输入在严格 JSON 输出前 fail closed。
- 日常 loader 与 `build_pit_dataset` 均证明未来历史记录不改变同一 as-of 日期的三层结果。
- 首对独立复审发现的 partial 成熟度、排名端点压缩、生产严格 JSON、PIT manifest、最终汇总元数据和直接 PIT 不变性合同均已按 TDD 整改。

## 验证结果

- TDD 行为覆盖：时序/截面正交、排名上升与下降、历史不足、状态与风险分离、非有限输入、ranking 接入、故障隔离、元数据、JSON 持久化、PIT 未来数据不变性。
- 最新目标回归：`108 passed in 3.20s`。
- fresh hermetic 全量：`3003 passed, 19 deselected in 17.95s`，0 failed，transcript SHA `66221c08c6a87663722f0bcd9bfa2621b7a866988bd54e073c2462f7e3d94e75`。
- 普通全量仍按仓库合同排除 19 个显式 network 节点；本轮未连接网络或券商。
- 当前 v6 自描述严格 JSON identity SHA 为 `b481e02fc876294ffa0c9d64a18ad47eb4c3fc6d00b3395bca9724143e86bb54`。它绑定 `pytest.ini`、`theme_sector_radar/scripts/tests`、仓库根 `*.py` 与 `config/**` 下全部 552 个常规静态文件，LF-only TSV SHA `d74f17eab9c648b9a1ff1bc27c01f6ded74c455e596ffc7306036eb921d247f7`，以及 HEAD、dirty 状态、pytest 命令、退出码、结果和 transcript SHA；v1-v5 均为已覆盖历史身份。
- `compileall`、`git diff --check`、严格解析 `172 JSON + 2 JSONL + 38,778 行`、4 份 PIT 严格 JSON、保护字段 tracked/untracked `0/0` 和 v6 身份自洽均通过。
- 只读机器验收沿冻结路径与 SHA 深验 6 份唯一 records、8 份 audits、tail `20/18/14`、11 `observe` / 3 `insufficient_evidence` / 0 晋级；decision SHA 保持 `7c8cfa35...5e3f9`，`live_trading_ready=false`。

## 研究结论

三层架构已经作为可观测 shadow 分解落地，但本轮没有重算既有 Path A v3 评分证据，也不产生新的收益优越性结论。现有 Path A v3 的五个候选仍为 `remain_shadow_development`，`strict_pit_eligible=false`、`promotion_allowed=false`、`live_trading_ready=false` 均不变。
