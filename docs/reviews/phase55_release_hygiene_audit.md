# Phase 55 Release Hygiene Audit

## 1. Phase 55 目标

本次不做功能扩张，只做发布前整理：审计工作区文件、定义交付分层、验证关键测试、生成发布快照文档。

## 2. 当前 Git 工作区概览

- **已修改 (M)**：38 个文件
- **未跟踪 (??)**：199 个文件
- **总计变更文件**：237 个

## 3. 文件分类结果

### 3.1 Source Code（建议纳入版本管理）

| 类别 | 文件数 | 说明 |
|------|--------|------|
| `theme_sector_radar/` 核心模块 | ~30 | agents、scoring、reports、data、backtest 等源码 |
| `theme_sector_radar/agents/sector_research/` | ~15 | 智能体模块 |
| `theme_sector_radar/data/catalyst_events/` | ~8 | 催化事件数据模块 |
| `theme_sector_radar/reports/` | ~15 | 报告生成器 |
| `theme_sector_radar/backtest/` | ~8 | 回测模块 |
| `theme_sector_radar/scoring/` | ~5 | 评分模块 |

### 3.2 Tests（建议纳入版本管理）

| 类别 | 文件数 |
|------|--------|
| `tests/theme_sector_radar/` 测试文件 | ~90 |
| `tests/fixtures/` 测试固件 | ~5 |

### 3.3 Docs（建议纳入版本管理）

| 类别 | 文件数 | 说明 |
|------|--------|------|
| `docs/plans/phase*.md` | ~25 | 各阶段计划文档 |
| `docs/reviews/phase*.md` | ~30 | 各阶段验证文档 |
| `docs/daily_*.md` | ~2 | 日常操作指南 |
| `README.md` | 1 | 项目说明 |

### 3.4 Scripts（部分建议纳入）

| 文件 | 是否纳入 | 说明 |
|------|----------|------|
| `scripts/check_cache.py` | 建议纳入 | 缓存检查工具 |
| `scripts/check_catalyst_cache.py` | 建议纳入 | 催化事件缓存检查 |
| `scripts/network_smoke_test.py` | 可选 | 网络冒烟测试 |
| `scripts/test_ak.py` | 可选 | AkShare 测试脚本 |

### 3.5 运行产物（建议不纳入或后续归档）

| 类别 | 说明 |
|------|------|
| `reports/` | 所有 reports 运行产物，包括 daily radar、sector_research、backtests、daily_health 等 |
| `data_cache/` | 缓存数据 |
| `logs/` | 运行日志 |
| `test_output/` | 测试输出 |
| `scripts/phase52_network_smoke_result.json` | 单次运行结果 |

### 3.6 临时文件

| 文件 | 说明 |
|------|------|
| `scripts/phase52_network_smoke_result.json` | 临时网络测试结果 |

## 4. 建议纳入版本管理的内容

- `theme_sector_radar/` 下所有源码
- `tests/theme_sector_radar/` 下所有测试
- `docs/plans/phase*.md` 和 `docs/reviews/phase*.md`
- `README.md`
- `scripts/check_cache.py`、`scripts/check_catalyst_cache.py`
- `requirements.txt`、`setup.py`、`pytest.ini`
- `.gitignore`

## 5. 建议不纳入版本管理或后续归档的内容

- `reports/` 目录下所有运行产物（daily radar、sector_research、backtests、daily_health 等）
- `data_cache/` 缓存数据
- `logs/` 运行日志
- `test_output/` 测试输出
- `scripts/phase52_network_smoke_result.json` 临时结果

## 6. 当前关键验证结果

- **最近全量测试**：815 passed, 26 warnings
- **Phase 55 专项测试**：45 passed（catalyst_event_historical_collector、catalyst_events、report_contract、report_quality）
- **CatalystEventAgent**：仍 report-only，不参与生产决策
- **禁止措辞扫描**：theme_sector_radar/ 下未发现生产代码禁用措辞

## 7. 风险点

1. 工作区很大（237 个变更文件），直接提交会混入大量运行产物
2. `reports/` 是否纳入版本管理需要项目策略决定
3. 某些历史审计文档可能包含旧术语，但非生产生成器输出
4. 部分 scripts 可能只在特定环境下使用

## 8. 建议的后续操作

1. **建立 release snapshot 文档**（本文档）
2. **决定 reports 保留策略**：建议 `reports/` 在 .gitignore 中保持忽略，关键样本报告可在 `docs/samples/` 下单独保存
3. **做一次干净提交或分批提交**：
   - 提交 1：源码 + 测试 + 文档
   - 提交 2：scripts（如果需要）
   - 不提交 reports/data_cache/logs
4. **Phase 56**：可以做 reports 策略和提交拆分，或继续真实 Catalyst 多日观察

## 9. 不修改 ai-hedge-fund 确认

本阶段未修改 `E:\Workspace\ai-stock-projects\ai-hedge-fund` 中的任何文件。所有操作仅限于 `theme-sector-radar-dev` 项目。
