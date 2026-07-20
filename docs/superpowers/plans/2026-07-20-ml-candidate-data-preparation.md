# 个股 ML 候选数据准备计划

## 已完成

- [x] 保留 v9 的 99 日、1,730 行主 cohort，不扩张训练样本。
- [x] 扫描 candidate archive 的全部 160 个 content-bound 日源，识别 61 个未被 v9 manifest 绑定的额外日期和 1,072 行。
- [x] 统计逐股 1m session bars 的无未来日期覆盖：v9 cohort 1,353/1,730 行。
- [x] 复核 direction：51 个报告日期，v9 日期重叠 41 日，675 行同名观察；strict PIT 仍为 0。
- [x] 复核 Linkage V2：2 个单日报告、1 个报告日期、v9 日期重叠 0、dated input manifest 0；strict 可用仍为 0。
- [x] 生成 `candidate_data_preparation_v2_20260720` 独立 paper-only inventory、coverage report 和 A/B schema contract。

## 暂不执行

- 不训练新模型，不重算 round1-round20。
- 不把额外 61 日、当前 membership、当前 sector score 或 direction/Linkage 观察值并入训练。
- 不接正式排序、predictor、broker、order、live 或事件增强。

## 下一阶段准入

只有同时具备逐日股票 membership、嵌套 snapshot `as_of_date`、逐日 bars/技术输入
SHA，以及 Linkage V2 的逐日 constituent weight、stock/sector return、flow、quality
输入时，才可把相应字段从 `partial` 提升为 `strict_replayable`。之后仍需新窗口、
expanding/purge/OOS 设计和规则/ML/组合预注册对照，不能从本 99 日 reconstruction
窗口宣布晋级。
