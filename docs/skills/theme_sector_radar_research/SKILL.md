# Theme Sector Radar Research Skill

## 目标

通过 MCP 调用现有量化研究程序，执行纸面/影子研究并解释结果。

## 固定流程

1. 调用 `check_data_health`。
2. 确认 `as_of_date` 为 canonical ISO 日期，且数据最新日不晚于研究日。
3. 调用 `run_full_paper_pipeline`，候选链固定为 `direction_linkage_v2`。
4. 调用 `get_direction_candidates` 和 `get_stock_ranking` 读取已落盘结果。
5. 检查 `run_health`、数据覆盖率、Linkage V2 状态和报告来源。
6. 输出板块、个股排名、因子解释、缺失数据和降级原因。

## 研究规则

- 方向分是当前板块主路径；趋势/短线路径默认关闭。
- 基础分与方向分不直接相加；基础排名只通过排名动量间接影响方向分。
- 旧 `relevance_score` 只作历史对照。
- Linkage V2 不可用时 fail-closed，不填 0，不回退旧路径。
- 行业 ML、个股 ML 和事件调整只做 Shadow A/B，不覆盖正式评分。
- 只能输出 paper/shadow candidate，不得称为买入清单。

## 禁止事项

- 不连接 broker。
- 不生成 order、仓位、买入或卖出指令。
- 不修改 `quant_score`、`final_score`、`v2_score`、`selection_score` 或
  `selection_score_adjusted`。
- 不把历史重建结果称为 OOS、严格 PIT 或可交易收益。
- 不用缺失数据、当前值或 fixture 伪造目标日期结果。

