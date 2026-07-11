# 双代理开发工作流规范

本文档规范 Codex 审核代理与 VSCode Claude Code 执行代理的协作方式。目标是让阶段任务形成稳定闭环：派单清晰、执行可验、测试口径明确、报告不覆盖、审核有证据。

## 1. 角色分工

### Codex 审核代理

- 负责拆解阶段目标、生成 Claude Code 派单提示词。
- 负责读取 Claude Code 汇报，但不得只信汇报。
- 负责复跑关键测试、检查报告、审核 diff。
- 负责判断是否验收、返工或进入下一阶段。
- 负责保护边界：不修改 `selection_quality`，不解除 `shadow-only`，除非阶段提示词明确要求。

### Claude Code 执行代理

- 负责按派单提示词修改代码、补测试、生成报告。
- 负责运行指定测试并汇报完整结果。
- 不得扩大任务范围。
- 不得删除历史阶段报告。
- 不得把 shadow 因子接入正式买入点、打分或筛选。

## 2. 标准流程

1. Codex 根据当前阶段结论生成派单提示词。
2. Codex 通过 VSCode Claude Code 面板发送任务。
3. Claude Code 执行修改、测试和报告生成。
4. Claude Code 汇报：
   - 修改文件
   - 新增文件
   - 报告路径
   - 执行命令
   - 测试结果
   - 未完成事项
5. Codex 读取汇报，但必须自行验证：
   - `git status --short`
   - 相关文件内容
   - 报告内容
   - 指定测试命令
6. Codex 给出审核结论：
   - 通过
   - 部分通过，需要返工
   - 不通过，说明阻塞原因

## 3. 派单提示词模板

```text
你是本项目的 Claude Code 执行代理。请实施【阶段名称】。

背景：
【写清上一阶段已验证结论、当前问题、禁止误判点】

本阶段目标：
1. 【目标 1】
2. 【目标 2】
3. 【目标 3】

实施要求：
1. 先检查相关文件，不要猜测。
2. 最小修改，优先复用现有脚本和项目风格。
3. 不做无关重构。
4. 不删除历史报告。
5. 不修改 selection_quality，除非本阶段明确要求。
6. bars 因子继续 shadow-only，除非本阶段明确要求。

报告要求：
1. 新报告必须使用本阶段独立文件名。
2. 不得覆盖旧阶段报告。
3. 报告必须包含数据来源、字段路径、样本数、关键结论。

测试要求：
运行以下命令并完整汇报结果：
【粘贴具体 pytest 命令】

完成后请汇报：
1. 修改文件
2. 新增文件
3. 报告路径
4. 关键验证结果
5. 是否修改 selection_quality
6. 是否继续 shadow-only
7. 测试命令和测试结果
8. 未完成事项或风险
```

## 4. Claude Code 汇报格式

Claude Code 完成后必须按以下格式汇报：

```text
执行完成/执行失败

1. 修改文件
- path/to/file.py: 修改说明

2. 新增文件
- path/to/new_file.py: 用途

3. 报告路径
- reports/.../phase_specific_report.json
- reports/.../phase_specific_report.md

4. 核心结论
- 【结论 1】
- 【结论 2】

5. 边界确认
- selection_quality: 未修改/已按要求修改
- shadow-only: 继续保持/已按要求调整
- 历史报告: 未删除

6. 测试
命令：
python -m pytest ...

结果：
xx passed in yy.s

7. 风险和未完成事项
- 无/具体事项
```

## 5. Codex 审核清单

Codex 不得直接接受 Claude Code 的成功结论。每次验收前必须完成以下检查：

```text
1. 工作区状态
git status --short

2. 文件检查
读取 Claude Code 声称修改的文件。

3. 报告检查
确认报告路径存在。
确认报告文件名属于当前阶段。
确认报告内容与汇报一致。

4. 测试复跑
运行派单中指定的测试命令。
只声明自己复跑过的测试结果。

5. 边界检查
确认没有无要求修改 selection_quality。
确认没有把 shadow-only 因子接入正式策略。
确认没有删除旧报告。

6. 结论
通过/返工/不通过。
```

## 6. 测试口径规则

- `所有测试通过` 只能用于全量测试命令成功时。
- 局部测试成功只能写成：`指定回归测试通过`。
- Claude Code 汇报的测试结果只能作为线索，不能作为验收依据。
- Codex 最终结论必须基于自己复跑的命令输出。
- 如果测试失败，必须汇报失败数、失败文件和根因，不得继续说阶段完成。

## 7. 报告命名规则

每个阶段必须生成独立报告名，禁止覆盖旧阶段报告。

推荐格式：

```text
reports/stock_factor_validation/<topic>_<start_date>_<end_date>.json
reports/stock_factor_validation/<topic>_<start_date>_<end_date>.md
```

示例：

```text
reports/stock_factor_validation/stock_profile_bars_state_source_validation_2026-04-01_2026-07-10.json
reports/stock_factor_validation/stock_profile_bars_state_source_validation_2026-04-01_2026-07-10.md
```

如果 Claude Code 覆盖了旧报告，Codex 必须标记为返工或交付瑕疵。

## 8. 返工规则

触发返工的常见条件：

- Claude Code 汇报测试通过，但 Codex 复跑失败。
- 报告文件名复用旧阶段。
- 报告内容与汇报不一致。
- 状态字段、raw_value 字段或数据源解释不清。
- 修改范围超出派单要求。
- 未经要求修改 `selection_quality`。
- 未经要求解除 `shadow-only`。

返工提示词必须只聚焦失败点，不重新打开已完成范围。

## 9. 当前 bars 因子边界

在 bars 因子进入正式策略前，默认边界如下：

- `selection_quality`: 暂不修改。
- bars 因子：继续 `shadow-only`。
- `liquidity_score`: 继续 `profile_only`。
- `overheat_state.high`: 可作为风险识别观察信号。
- `breakout_structure` 和 `drawdown_state`: 进入阈值校准前必须先确保 raw/state 来源可信。

## 10. 阶段验收用语

推荐用语：

- `指定回归测试通过：78 passed in 0.36s。`
- `业务目标基本达成，但报告命名存在交付瑕疵。`
- `不能宣称全量测试通过，因为本次只复跑了指定测试。`
- `需要返工，原因是...`

禁止用语：

- `应该没问题`
- `看起来通过`
- `Claude Code 说通过，所以通过`
- `所有测试通过`，但没有全量测试证据

