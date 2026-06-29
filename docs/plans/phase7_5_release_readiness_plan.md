# Phase 7.5 发布前验收与打包清理计划

日期：2026-06-29  
目标：让项目从"能用"变成"可交付、可复现、可维护"

## 1. smoke test 语义调整

### 1.1 当前问题
- 默认 smoke test 使用 rotation-day2 fixture，状态为 degraded
- 不利于判断环境健康状态

### 1.2 调整方案
- 默认 smoke test 使用 `--fixture-profile full`
- 预期 status 应为 ok
- 新增 `run_daily_degraded_fixture.ps1` 用于验证 degraded 报告链路

## 2. 发布前验收清单

### 2.1 必须通过的验收项
1. pytest 全量通过
2. fixture smoke test status=ok
3. degraded fixture test 可生成 degraded 报告
4. replay-cache 可运行
5. index.md 可生成
6. run_log.json 字段完整
7. 报告不包含 buy/sell/hold
8. 报告不包含 买入、卖出、持有建议、个股推荐
9. ai-hedge-fund 未修改
10. Windows Task Scheduler 只提供文档

## 3. README 更新范围

### 3.1 必须包含
1. 项目定位
2. 明确边界
3. 快速开始
4. 输出路径说明
5. 常用命令
6. 文档入口
7. 当前状态

## 4. .gitignore 检查

### 4.1 忽略规则
- config/daily.local.json
- logs/
- data_cache/
- reports/theme_sector_radar/
- __pycache__/
- .pytest_cache/
- .venv/

## 5. 文档入口整理

### 5.1 必要文档
- README.md
- docs/runbooks/daily_workflow.md
- docs/runbooks/windows_task_scheduler.md
- docs/runbooks/troubleshooting.md
- docs/release_checklist.md

## 6. 测试与验收命令

```bash
# 默认测试
python -m pytest tests/theme_sector_radar/ -v

# smoke test
powershell -ExecutionPolicy Bypass -File scripts/run_daily_fixture.ps1

# degraded fixture test
powershell -ExecutionPolicy Bypass -File scripts/run_daily_degraded_fixture.ps1

# replay-cache
python -m theme_sector_radar.cli --replay-cache --start-date 2026-06-27 --end-date 2026-06-28 --lookback-days 5 --report-root reports/theme_sector_radar
```
