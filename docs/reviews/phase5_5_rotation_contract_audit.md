# Phase 5.5 轮动追踪测试补齐与契约审计

日期：2026-06-29  
状态：审计完成，需要补齐测试

## 1. Phase 5 原计划测试文件审计

| 测试文件 | 是否存在 | 状态 |
|---------|---------|------|
| test_snapshot_loader.py | ❌ | 缺失 |
| test_rotation_tracker.py | ❌ | 缺失 |
| test_rotation_fixture_profiles.py | ❌ | 缺失 |
| test_rotation_report_contract.py | ❌ | 缺失 |
| test_cli_rotation_args.py | ❌ | 缺失 |

**结论**: Phase 5 原计划要求的 5 个专项测试文件全部缺失。

## 2. pytest 收集情况

当前测试文件共 23 个，但无轮动追踪专项测试。

## 3. snapshot_loader 功能审计

### 3.1 compare-to 报告查找
- ✅ 支持直接匹配日期目录
- ✅ 支持查找包含日期的目录（如 rotation-day1）
- ✅ 优先返回有数据的报告

### 3.2 lookback-days 查找
- ✅ 在 lookback-days 内查找最近可用报告
- ⚠️ 需要验证不会误读当天报告

## 4. rotation_tracker 功能审计

### 4.1 rank_change 计算
- ✅ rank_change = previous_rank - current_rank
- ✅ 正数表示排名上升

### 4.2 score_change 计算
- ✅ score_change = current_score - previous_score

### 4.3 分类识别
- ✅ new_entry: 今日进入 Top N，历史不存在
- ✅ dropped_out: 历史 Top N 存在，今日不存在
- ✅ rising_fast: rank_change >= 3 或 score_change >= 8
- ✅ persistent_strength: 连续两期 Top N 且 final_score >= 75
- ⚠️ risk_up: 需要验证正确性

## 5. Markdown 轮动章节审计

### 5.1 需要验证的内容
- ✅ 包含"板块轮动变化"
- ⚠️ 需要验证包含"新晋 Top N"、"快速升温"、"连续强势"、"掉出 Top N"
- ⚠️ 需要验证不包含 buy/sell/hold

## 6. 审计结论

### 6.1 需要补齐的测试文件
1. test_snapshot_loader.py
2. test_rotation_tracker.py
3. test_rotation_fixture_profiles.py
4. test_rotation_report_contract.py
5. test_cli_rotation_args.py

### 6.2 需要验证的功能
1. compare-to 报告查找
2. lookback-days 不误读当天报告
3. dropped_out 识别正确
4. rotation_summary industry/concept 分离
5. Markdown 轮动章节完整性
