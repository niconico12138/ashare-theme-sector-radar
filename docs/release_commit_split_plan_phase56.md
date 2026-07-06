# Release Commit Split Plan - Phase 56

## 1. 推荐提交顺序

| 序号 | 提交名称 | 优先级 | 说明 |
|------|----------|--------|------|
| 1 | core source code | 高 | 核心模块源码 |
| 2 | tests | 高 | 测试代码 |
| 3 | docs/plans and docs/reviews | 高 | 项目文档 |
| 4 | scripts and operator docs | 中 | 工具脚本和操作手册 |
| 5 | curated samples（可选） | 低 | 代表性样例报告 |

## 2. 每个提交包含的文件模式

### 提交 1：core source code
```bash
git add theme_sector_radar/
git add README.md requirements.txt setup.py pytest.ini
```
**包含**：`theme_sector_radar/` 下所有 .py 文件、`README.md`、`requirements.txt`、`setup.py`、`pytest.ini`

### 提交 2：tests
```bash
git add tests/
```
**包含**：`tests/theme_sector_radar/` 下所有测试文件、`tests/fixtures/` 下所有测试固件

### 提交 3：docs/plans and docs/reviews
```bash
git add docs/plans/ docs/reviews/ docs/daily_*.md docs/release_snapshot_phase55.md docs/roadmap_after_phase51.md
```
**包含**：所有阶段计划文档、验证文档、操作手册

### 提交 4：scripts and operator docs
```bash
git add scripts/check_cache.py scripts/check_catalyst_cache.py scripts/network_smoke_test.py scripts/test_ak.py
```
**包含**：工具脚本（排除临时文件 `scripts/phase52_network_smoke_result.json`）

### 可选提交 5：curated samples
```bash
git add docs/samples/
```
**包含**：代表性样例报告（需先创建 `docs/samples/` 目录并复制样例）

## 3. 每个提交不应包含的内容

| 提交 | 不应包含 |
|------|----------|
| 提交 1 | tests、docs、scripts、reports、data_cache |
| 提交 2 | 源码、docs、reports、data_cache |
| 提交 3 | 源码、tests、reports、data_cache |
| 提交 4 | 源码、tests、reports、data_cache、`scripts/phase52_network_smoke_result.json` |
| 提交 5 | 原始 reports 目录 |

## 4. reports 处理策略

- **当前状态**：`reports/` 未在 .gitignore 中生效（被注释掉），有 12 个 M 状态文件
- **建议策略**：
  1. 本次提交**不包含** reports 目录
  2. 在 `docs/samples/` 下复制 1-2 天代表性样例
  3. 后续如需将 reports 纳入版本管理，需单独执行 `git rm --cached` 清理已跟踪文件
- **样例保留**：
  ```
  docs/samples/reports/theme_sector_radar/2026-06-28/
  docs/samples/reports/sector_research/2026-06-28/
  ```

## 5. data_cache/logs/临时文件处理策略

| 目录/文件 | 处理方式 |
|-----------|----------|
| `data_cache/` | 已在 .gitignore，不提交 |
| `logs/` | 已在 .gitignore，不提交 |
| `test_output/` | 建议添加到 .gitignore，不提交 |
| `scripts/phase52_network_smoke_result.json` | 不提交（临时文件） |

## 6. 提交前验证命令

```bash
# 验证源码无语法错误
python -c "import theme_sector_radar"

# 验证测试通过
python -m pytest tests/theme_sector_radar/ -v --tb=short

# 验证 README 可读
cat README.md | head -20

# 验证 .gitignore 规则
git status --short | grep "^??" | head -10
```

## 7. 回滚风险提示

- **低风险**：本次只是策略制定和文档生成，不做实际提交
- **如果后续执行提交**：
  - 使用 `git reset --soft HEAD~1` 可以撤销最近一次提交（保留文件）
  - 使用 `git revert <commit-hash>` 可以创建反向提交
  - **不要**使用 `git reset --hard` 或 `git clean`（会丢失文件）

## 8. 人工确认点

在执行实际提交前，需要人工确认：

1. [ ] 确认 `reports/` 不纳入本次提交
2. [ ] 确认 `docs/samples/` 样例选择（如有）
3. [ ] 确认 `scripts/phase52_network_smoke_result.json` 不提交
4. [ ] 确认 `.gitignore` 是否需要修改（建议暂不修改）
5. [ ] 确认所有测试通过
6. [ ] 确认无禁用措辞输出
