# Phase 27.6: 轮动测试历史快照隔离修复

## 失败测试列表

| # | 测试文件 | 测试名 | 失败现象 |
|---|---------|--------|---------|
| 1 | `test_rotation_fixture_profiles.py` | `test_day2_has_rising_fast` | `rising_fast` 为空 |
| 2 | `test_rotation_fixture_profiles.py` | `test_day2_has_persistent_strength` | `persistent_strength` 为空 |
| 3 | `test_rotation_report_contract.py` | `test_markdown_has_rising_fast_section` | Markdown 无"快速升温"章节 |
| 4 | `test_rotation_report_contract.py` | `test_markdown_has_persistent_strength_section` | Markdown 无"连续强势"章节 |

## 失败原因

### 根因：`report_root` 路径与 `snapshot_loader` 搜索路径不匹配

`snapshot_loader` 在 `pipeline.py:242` 中构建搜索路径：
```python
report_dirs = [report_root] if report_root else ["reports/theme_sector_radar"]
```

然后在 `snapshot_loader.py:82` 中按日期查找快照：
```python
json_path = os.path.join(report_dir, date_str, "theme_sector_radar.json")
```

即对于 `report_root = "X"`，搜索 `X/<date>/theme_sector_radar.json`。

### 问题 1: `test_rotation_fixture_profiles.py` 的路径错位

测试设置：
```python
report_root = os.path.join(tmpdir, "reports")        # <tmpdir>/reports
output_dir = os.path.join(report_root, "theme_sector_radar", "2026-06-27")
# 实际保存路径: <tmpdir>/reports/theme_sector_radar/2026-06-27/theme_sector_radar.json
```

但 `snapshot_loader` 搜索路径：
```
<tmpdir>/reports/2026-06-27/theme_sector_radar.json   ← 不存在
```

day1 报告保存在 `<tmpdir>/reports/theme_sector_radar/2026-06-27/` 下，而 loader 在 `<tmpdir>/reports/2026-06-27/` 下搜索。路径中多了一层 `theme_sector_radar`，导致 loader 找不到 day1 快照。

### 问题 2: `test_rotation_report_contract.py` 缺少 day1 生成和隔离

测试未生成 day1 fixture，且未传入 `report_root`，导致 `snapshot_loader` 使用默认路径 `["reports/theme_sector_radar"]`，读取了全局真实报告 `reports/theme_sector_radar/2026-06-27/theme_sector_radar.json`。真实报告的轮动数据与 day2 fixture 数据比较后，不满足 `rising_fast` / `persistent_strength` 的触发条件。

## snapshot_loader 实际读取路径

| 场景 | report_root | loader 搜索路径 | day1 实际保存路径 | 是否匹配 |
|------|-------------|----------------|-------------------|---------|
| 修复前 fixture_profiles | `<tmp>/reports` | `<tmp>/reports/<date>/` | `<tmp>/reports/theme_sector_radar/<date>/` | ❌ |
| 修复后 fixture_profiles | `<tmp>/reports/theme_sector_radar` | `<tmp>/reports/theme_sector_radar/<date>/` | `<tmp>/reports/theme_sector_radar/<date>/` | ✅ |
| 修复前 report_contract | `None` → `reports/theme_sector_radar` | `reports/theme_sector_radar/<date>/` | 未生成 day1 | ❌ (读全局) |
| 修复后 report_contract | `<tmp>/reports/theme_sector_radar` | `<tmp>/reports/theme_sector_radar/<date>/` | `<tmp>/reports/theme_sector_radar/<date>/` | ✅ |

## 修复方案

### 修复 1: `test_rotation_fixture_profiles.py`

将所有测试的 `report_root` 从 `os.path.join(tmpdir, "reports")` 改为 `os.path.join(tmpdir, "reports", "theme_sector_radar")`，使 `output_dir` 和 `snapshot_loader` 搜索路径一致。

### 修复 2: `test_rotation_report_contract.py`

- 新增 `_run_day1_day2` 辅助方法，先生成 day1 fixture 再生成 day2
- 所有使用 `compare_to` 的测试均通过此辅助方法获取隔离的 day2 输出
- 传入 `report_root` 确保 `snapshot_loader` 只搜索临时目录

## 修复前后结果

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 总测试数 | 614 | 614 |
| 通过 | 610 | 614 |
| 失败 | 4 | 0 |
| 警告 | 19 | 19 |

## 是否影响真实 CLI 行为

**不影响。** 修复仅涉及测试代码，未修改任何业务逻辑：

- `snapshot_loader.py` — 未修改
- `pipeline.py` — 未修改
- `rotation_tracker.py` — 未修改
- `markdown_report.py` — 未修改
- CLI 默认行为（`report_root` 默认值）— 未修改

真实 CLI 仍然使用 `reports/theme_sector_radar` 作为默认报告根目录，日常日报对比能力不受影响。

## 修改文件列表

1. `tests/theme_sector_radar/test_rotation_fixture_profiles.py` — 修正 `report_root` 路径
2. `tests/theme_sector_radar/test_rotation_report_contract.py` — 添加 day1 生成 + 隔离 + report_root
3. `docs/reviews/phase27_6_rotation_test_isolation_fix.md` — 本审计文档
