# 全量测试基线清零设计

## 状态与目标

- Phase 11 状态：实施、机械验收和当时两份独立只读终审已完成；A4/B3 均为 Critical=0、Important=0。该凭证不覆盖后续评分可信度扩展。
- 目标（已达成）：清零整改前全量 `pytest -q` 的 43 个历史失败，使测试不再依赖 worktree 外部或运行时生成的历史 `reports`。
- 范围：测试夹具、测试辅助工厂、必要的最小兼容修复，以及与这些失败直接相关的文档。
- 禁止：不连接券商，不生成实盘指令，不修改 `final_score`、`v2_score`、`selection_score`、`selection_score_adjusted`，不回退 dirty worktree，不提交代码。

## 历史基线与当前结果

- 历史全量基线：`2612 passed, 2 skipped, 43 failed`。该数字只描述整改前状态，不再代表当前测试结果。
- 当前原 12 模块失败集：`404 passed in 4.78s`，0 failed、0 skipped。
- 当前第四轮研究聚焦回归：`418 passed in 5.40s`。
- 当前 unified bridge 完整文件：`191 passed in 3.80s`。
- 当前九个直接受影响完整测试文件：`193 passed in 2.73s`。
- 当前 hermetic 全量回归：`3003 passed, 19 deselected in 17.95s`，0 failed；`2996 passed, 19 deselected in 18.27s` 及更早数字仅为历史整改凭证。
- 19 个 deselected 节点均为显式 `network` 合同；普通 `pytest -q` 默认排除它们，未发起 AkShare/代理访问。显式网络合同可用 `-m network` 单独运行，不属于 Phase 11 离线验收。

失败按测试职责分为以下簇：

| 失败簇 | 数量 | 主要原因 |
|---|---:|---|
| sector input backfill | 9 | 测试直接读取缺失的历史 `reports/sector_scores` 与派生报告 |
| rotation CLI / snapshot loader | 6 | 历史轮动快照不在当前 worktree，比较逻辑返回 `no_previous_data` |
| factor calibration / diagnosis | 6 | 集成测试期待运行时生成的 JSON/Markdown 已存在 |
| historical backfill / availability | 5 | 日期扫描和聚合依赖外部历史报告树 |
| risk component quality | 3 | 测试期待固定输出文件及章节存在 |
| selection validation | 2 | 日期扫描依赖外部 selection-validation 历史树 |
| paper wording contracts | 3 | 禁词断言范围与 paper/shadow 文案边界不一致 |
| unified bridge / daily runner | 9 | 缺板块评分报告导致 bridge 返回空结果并使后续集成测试失败 |

合计 43 个失败。

上述 43 个历史失败现已全部清零。

## 方案选择

采用混合式 hermetic fixture 方案：

1. 大多数测试通过 `tmp_path`、monkeypatch 和共享 fixture factory 构造最小输入树。
2. 需要验证历史快照格式与跨日期行为的测试使用小型静态 JSON fixture，不复制整棵生产 `reports`。
3. CLI 和 daily runner 集成测试显式注入 fixture root，禁止隐式读取开发机共享报告目录。
4. 只有当测试揭示真实业务缺陷时才修改生产代码；不得为让测试通过而放宽 fail-closed、paper-only 或数据身份约束。

终审整改进一步收紧 unified bridge 身份边界：CLI、继承环境或默认配置得到的 score root 都在任何网络工作前校验，daily wrapper 的默认根也先于 TCP/HTTP；显式根只接受 exact-date JSON，默认根拒绝非 ISO 日期路径，exact 文件损坏时拒绝，只有物理缺失时才按日期倒序预验证不晚于 `as_of` 的合法历史文件，daily wrapper 与 direct bridge 都会越过损坏的最近历史文件。共享 schema 要求非空 `scores`、合法板块身份、有限数值和文本 level；父进程 score 读取绑定已打开文件身份，并以 ASCII 转义的严格 JSON stdin 把同一 payload 和实际 fallback 日期交给 child，child 先消费 stdin，默认根仍不注入 report-root override。稳定 research/concept/cache 读取分别限制在各自专属子根，拒绝 sibling junction；打开时验证普通文件、containment 与身份。industry 顶层/行必需 schema、concept 完整表头与非空数值任一失败时整源拒绝；cache key/payload/hit 绑定请求日，默认 cache 读写只能是根下直接子文件，显式根禁用 cache 写入；bridge 同时保留 `weight` 与 `sector_weight` 后再归一化。严格 JSON 对 float 溢出整数给出带字段路径的受控错误。组合实验 candidate 与 selection 使用同一 `effective_end`；candidate/selection payload 日期绑定目录日，candidate 身份扫描只有在调用方请求 snapshot 时才保存完整文档。records 顶层/逐条记录、final provenance 与长历史 JSONL 使用生产共享递归 paper-only 门禁；有效 `entry_price` 只接受正有限非布尔数值，旧 canonical 的 invalid/no-bars/0 占位为唯一兼容。stop reaudit 同一 bytes 完成 SHA/解析/guard，长期 `trigger_price` 豁免仅接受正有限观测标量，新事件必须带完整 guard，只有固定 SHA 的既有事件文件可窄兼容。final 完整验证 calendar schema/date_count/范围/周末，并联结 1m/5m selection、calendar 与共享 source snapshot；records provenance 别名必须成对且无冲突，临时联结身份不改变冻结 serializer。source bars 的 envelope SHA 绑定父 candidate code/name，records 保存完整 calendar 身份，三个 audit 拒绝跨 calendar 混审。普通 pytest 默认排除 network marker；fixture 动态恢复代理环境和模块全局。冻结 expanded source provenance 形状与固定 decision SHA 均保持不变。

不采用以下方案：

- 复制完整历史 `reports` 到 worktree：体积大、易过期、无法保证 CI 可重复。
- 将缺文件测试统一改成 skip：会掩盖真实契约，不能形成可靠基线。
- 让生产代码静默 fallback 到任意旧报告：会破坏日期身份与 fail-closed 原则。

## Fixture 架构

### 共享 fixture factory

在 `tests/theme_sector_radar/` 的现有测试辅助模式内增加职责明确的构造器：

- 生成指定日期的最小 `sector_scores.json`。
- 生成 rotation day1/day2 历史快照和比较字段。
- 生成 selection-validation 日期树与 aggregate 输入。
- 生成 unified bridge 所需的板块评分、成分来源和最小行情响应。
- 生成 calibration、diagnosis、risk-quality 的最小合法输入与预期输出根。

fixture factory 只产生测试数据，不调用网络，不读取共享生产报告，也不写入项目固定输出目录。

### 静态 fixture

仅保留无法用简短工厂清晰表达的 schema 示例：

- 历史轮动报告最小快照。
- unified bridge 最小板块评分报告。
- 需要验证 Markdown 章节和兼容字段的黄金样例。

静态 fixture 必须足够小，并由测试显式引用路径。

## 修复顺序

1. 建立共享报告树 fixture 与路径注入方式。
2. 修复 sector input backfill、historical backfill 和 availability 日期扫描。
3. 修复 snapshot loader 与 rotation CLI 历史比较。
4. 修复 calibration、diagnosis、risk-quality 输出契约。
5. 修复 selection validation 日期树。
6. 修复 unified bridge 与 daily runner 的最小端到端 fixture。
7. 收紧 paper wording 契约，使其只拒绝真实交易指令，不误伤研究状态描述。

每个失败簇使用现有失败作为 RED；修复后先跑该簇，再跑此前已修复簇，最后跑全量。

## 业务代码修改边界

允许的生产代码修改仅限：

- 增加显式、可测试的输入路径参数或依赖注入点。
- 修复在合法 fixture 下仍可复现的空值处理、错误返回或 schema 兼容问题。
- 保持默认生产行为不变，并继续 fail closed。

禁止：

- 为测试读取任意最近日期报告。
- 在缺少指定日期数据时伪造成功结果。
- 放宽候选、selection、calendar、SHA 或 paper-only 身份检查。
- 修改任何官方评分字段或改变选股排序。

## 验证与验收

当前 Path A v3 自描述评分证据 SHA 为 `b321b00f...1091ab`，身份注释前 SHA `5e4df313...f7a5c6` 仅作历史内容身份；archive/v2/intermediate 为 `0997c880...4ae30` / `03d50287...2f2a6` / `f3e422f6...77ecb`。当前板块宇宙未历史版本化，故 `strict_pit_eligible=false`、observed tail 非 OOS、promotion/live false。fresh hermetic 全量为 `3003 passed, 19 deselected`；canonical candidate、records 与 decision 身份均未重算，11/3/0、live false 不变。

完成条件：

1. 每个原失败节点独立通过。
2. 全量 `python -m pytest -q` 为 0 failed。
3. 第四轮非平稳研究聚焦回归继续全绿。
4. `python -m compileall scripts theme_sector_radar tests` 通过。
5. `git diff --check` 通过。
6. 保护字段新增代码命中为 0。
7. 测试执行不需要网络、共享生产 `reports` 或本机专属目录。
8. 两份全新独立只读复审均为 `Critical=0, Important=0`。

## 完成后的项目状态

完成本阶段后，仓库将从“研究链可信但全量测试带历史失败”提升为“研究链可信且全量测试可在独立 worktree 重复全绿”。这不会改变当前策略结论：候选仍仅限 paper/shadow research，是否晋级继续由冻结后的前瞻样本和既定硬门槛决定。
