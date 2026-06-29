# 发布前验收清单

日期：2026-06-29

## 验收项

### 1. 测试通过
- [ ] pytest 全量通过
- [ ] fixture smoke test status=ok
- [ ] degraded fixture test 可生成 degraded 报告

### 2. 功能验证
- [ ] replay-cache 可运行
- [ ] index.md 可生成
- [ ] run_log.json 字段完整

### 3. 报告内容
- [ ] 报告不包含 buy/sell/hold
- [ ] 报告不包含 买入、卖出、持有建议、个股推荐
- [ ] 报告包含 disclaimer 声明

### 4. 项目边界
- [ ] ai-hedge-fund 未修改
- [ ] 不接入 LangGraph
- [ ] 不注册 ANALYST_CONFIG
- [ ] 不输出个股推荐
- [ ] 不自动创建 Windows 任务计划

### 5. 文档完整性
- [ ] README.md 更新
- [ ] docs/runbooks/daily_workflow.md 存在
- [ ] docs/runbooks/windows_task_scheduler.md 存在
- [ ] docs/runbooks/troubleshooting.md 存在
- [ ] docs/release_checklist.md 存在

### 6. 配置和脚本
- [ ] config/daily.example.json 存在
- [ ] scripts/run_daily.ps1 存在
- [ ] scripts/run_daily_fixture.ps1 存在
- [ ] scripts/run_daily_degraded_fixture.ps1 存在

### 7. .gitignore
- [ ] 忽略 config/daily.local.json
- [ ] 忽略 logs/
- [ ] 忽略 data_cache/
- [ ] 忽略 reports/theme_sector_radar/

## 验收命令

```bash
# 运行全量测试
python -m pytest tests/theme_sector_radar/ -v

# 运行 smoke test
powershell -ExecutionPolicy Bypass -File scripts/run_daily_fixture.ps1

# 运行 degraded fixture test
powershell -ExecutionPolicy Bypass -File scripts/run_daily_degraded_fixture.ps1

# 运行 replay-cache
python -m theme_sector_radar.cli --replay-cache --start-date 2026-06-27 --end-date 2026-06-28 --lookback-days 5 --report-root reports/theme_sector_radar
```
