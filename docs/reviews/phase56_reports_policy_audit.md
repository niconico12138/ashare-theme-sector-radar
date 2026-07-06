# Phase 56 Reports Policy Audit

## 1. Phase 56 目标

制定 `reports/` 目录下运行产物的版本管理策略，给出后续提交拆分方案，不做功能扩张。

## 2. 当前 reports 分类和用途

| 目录 | 文件数 | 用途 | 可再生成 |
|------|--------|------|----------|
| `reports/theme_sector_radar/` | 158 | 每日行业/概念板块雷达日报（JSON + Markdown + raw_snapshot + run_log） | 是（`--daily`） |
| `reports/sector_research/` | 76 | 每日板块综合研判报告（JSON + Markdown + daily_summary） | 是（`--research-agents`） |
| `reports/sector_scores/` | 10 | 每日板块评分输出 | 是（`--score-sectors`） |
| `reports/sector_scores_batch/` | 4 | 批量评分输出 | 是 |
| `reports/sector_consensus/` | 240 | 多窗口共识输出 | 是（`--multi-window-consensus`） |
| `reports/backtests/` | 28 | 回测结果（agent_layers、agent_reliability、catalyst_events 等） | 是（回测命令） |
| `reports/data_downloads/` | 20 | 催化事件下载数据 | 是（`--download-catalyst-events`） |
| `reports/daily_health/` | 2 | 每日健康检查输出 | 是（`--daily-health-check`） |
| `reports/experiments/` | 5 | 实验权重对比 | 是（实验脚本） |
| `reports/research/` | 2 | 催化数据源研究 | 是（研究脚本） |

**合计**：约 545 个文件，全部可再生成。

## 3. 建议纳入版本管理的内容

以下内容已在 Phase 55 审计中确认纳入：

- `theme_sector_radar/` 下所有源码
- `tests/theme_sector_radar/` 下所有测试（~90 个文件）
- `docs/plans/phase*.md`（~25 个）
- `docs/reviews/phase*.md`（~30 个）
- `README.md`
- `scripts/check_cache.py`、`scripts/check_catalyst_cache.py`
- `requirements.txt`、`setup.py`、`pytest.ini`
- `.gitignore`

## 4. 建议不纳入版本管理的内容

| 目录/文件 | 理由 |
|-----------|------|
| `reports/theme_sector_radar/` | 可再生成的每日日报 |
| `reports/sector_research/` | 可再生成的研判报告 |
| `reports/sector_scores/` | 可再生成的评分输出 |
| `reports/sector_scores_batch/` | 可再生成的批量输出 |
| `reports/sector_consensus/` | 可再生成的共识输出 |
| `reports/backtests/` | 可再生成的回测结果 |
| `reports/data_downloads/` | 可再生成的下载数据 |
| `reports/daily_health/` | 可再生成的健康检查 |
| `reports/experiments/` | 可再生成的实验输出 |
| `reports/research/` | 可再生成的研究输出 |
| `data_cache/` | 缓存数据（已在 .gitignore） |
| `logs/` | 运行日志（已在 .gitignore） |
| `test_output/` | 测试输出 |
| `scripts/phase52_network_smoke_result.json` | 单次运行结果 |

## 5. 建议样例保留策略

**推荐建立 `docs/samples/` 目录**，只复制极少量代表性样例：

```
docs/samples/
├── reports/
│   ├── theme_sector_radar/
│   │   └── 2026-06-28/          # 1 天样例日报
│   │       ├── theme_sector_radar.json
│   │       └── theme_sector_radar.md
│   └── sector_research/
│       └── 2026-06-28/          # 1 天样例研判报告
│           ├── sector_research.json
│           └── sector_research.md
└── README.md                    # 样例说明
```

**不移动原 reports 中的文件**，只在 `docs/samples/` 下复制代表性样例。这样：
- 版本管理中有可运行的样例
- 原 reports 保持完整，不破坏现有路径
- 可再生成性不受影响

## 6. .gitignore 建议

当前 `.gitignore` 中 `reports/` 被注释掉了（`# reports/`）。建议**在文档中建议但暂不修改**，原因：

1. `reports/` 下已有部分 tracked 文件（M 状态），直接添加 `reports/` 到 .gitignore 不会自动移除已跟踪文件
2. 如果要彻底忽略 reports，需要后续单独执行 `git rm --cached`，需人工确认
3. 当前 Phase 56 只做策略制定，不做实际修改

**如果决定修改 .gitignore**，最小改动为：
```gitignore
# 报告目录（运行产物，不纳入版本管理）
reports/
# 但保留 docs/samples/ 下的代表性样例
!docs/samples/
```

**影响说明**：
- 已跟踪的 reports 文件不会被 .gitignore 自动移除
- 新增的 reports 文件将被忽略
- 若要清理已跟踪的 reports 文件，需后续单独执行 `git rm --cached reports/...`

## 7. 风险说明

1. **reports 当前有部分 tracked 修改**：38 个 M 文件中有 12 个在 `reports/` 下。单纯 .gitignore 不会影响这些已跟踪文件。
2. **若要彻底清理 tracked reports**：需要后续执行 `git rm --cached`，需人工确认每个文件。
3. **reports 策略变更可能影响 CI/CD**：如果有 CI 脚本依赖 reports 目录结构，需要同步更新。
4. **docs/samples/ 需要定期更新**：如果核心报告格式变化，样例也需要同步更新。

## 8. 后续提交拆分建议

### 提交 1：核心源码
```
theme_sector_radar/
README.md
requirements.txt
setup.py
pytest.ini
```
**不应包含**：tests、docs、scripts、reports

### 提交 2：测试
```
tests/
```
**不应包含**：源码、docs、reports

### 提交 3：文档
```
docs/plans/
docs/reviews/
docs/daily_*.md
docs/release_snapshot_phase55.md
docs/roadmap_after_phase51.md
```
**不应包含**：源码、tests、reports

### 提交 4：脚本和操作手册
```
scripts/check_cache.py
scripts/check_catalyst_cache.py
scripts/network_smoke_test.py
scripts/test_ak.py
```
**不应包含**：`scripts/phase52_network_smoke_result.json`（临时文件）

### 可选提交 5：样例报告
```
docs/samples/   （需先创建此目录）
```
**不应包含**：原始 reports 目录

## 9. 不修改 ai-hedge-fund 确认

本阶段所有操作仅限于 `theme-sector-radar-dev` 项目，未修改 `E:\Workspace\ai-stock-projects\ai-hedge-fund` 中的任何文件。
