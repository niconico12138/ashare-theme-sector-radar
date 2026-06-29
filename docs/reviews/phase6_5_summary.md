# Phase 6.5 完成总结

日期：2026-06-29  
状态：✅ 完成

## 1. Phase 6.5 审计文档路径

```
docs/reviews/phase6_5_daily_semantics_audit.md
```

## 2. 是否确认出现 fixture / AkShare / 旧报告串台

**是，发现了问题并已修复：**

### 问题 1：replay-cache 覆盖了 daily 输出
- **修复**：确保 daily 模式和 replay-cache 模式输出到不同目录

### 问题 2：报告使用了 AkShare 数据
- **原因**：replay-cache 读取了旧的 AkShare 缓存数据
- **修复**：确保 replay-cache 使用正确的数据来源

### 问题 3：run_log 缺少数据来源信息
- **修复**：添加 run_mode、provider、offline_fixture、fixture_profile、data_source_mode 等字段

### 问题 4：index_report 扫描了所有目录
- **修复**：index_report 只扫描标准日报目录 YYYY-MM-DD

## 3. 修复了哪些文件

| 文件 | 修改内容 |
|------|---------|
| `pipeline.py` | 添加 run_mode、provider_name、offline_fixture、fixture_profile 参数 |
| `models.py` | 添加 run_mode、provider、offline_fixture、fixture_profile、data_source_mode、report_dir、generated_by_command 字段 |
| `cli.py` | 添加数据来源追踪逻辑 |
| `reports/json_report.py` | 添加数据来源字段输出 |
| `reports/index_report.py` | 只扫描标准日报目录 |

## 4. daily fixture_profile 是否正确传递

**是，已验证：**

```json
{
  "fixture_profile": "rotation-day2",
  "offline_fixture": true,
  "run_mode": "daily",
  "data_source_mode": "fixture"
}
```

## 5. index_report 默认扫描规则

- ✅ 只扫描 `YYYY-MM-DD` 标准目录
- ✅ 不扫描 `YYYY-MM-DD-phase*`、`YYYY-MM-DD-rotation*` 等实验目录
- ✅ 添加 `--include-experiments` 参数支持实验目录

## 6. run_log 新增字段示例

```json
{
  "run_mode": "daily",
  "provider": "fixture",
  "offline_fixture": true,
  "fixture_profile": "rotation-day2",
  "data_source_mode": "fixture",
  "report_dir": "reports/theme_sector_radar/2026-06-28",
  "report_root": "reports/theme_sector_radar",
  "index_included": true,
  "comparison_source": "specified_date:2026-06-27",
  "input_snapshot_source": "fixture"
}
```

## 7. theme_sector_radar.json 数据来源字段示例

```json
{
  "run_mode": "daily",
  "provider": "fixture",
  "offline_fixture": true,
  "fixture_profile": "rotation-day2",
  "data_source_mode": "fixture",
  "report_dir": "reports/theme_sector_radar/2026-06-28",
  "generated_by_command": "--daily --as-of 2026-06-28 --offline-fixture --fixture-profile rotation-day2"
}
```

## 8. 新增测试文件

| 测试文件 | 说明 |
|---------|------|
| `test_daily_data_source_semantics.py` | Daily 数据来源语义测试 |
| `test_index_scan_scope.py` | Index 扫描范围测试 |
| `test_run_log_source_traceability.py` | Run Log 数据来源追踪测试 |
| `test_replay_cache_source_integrity.py` | Replay Cache 数据来源完整性测试 |

## 9. 默认测试结果

```bash
python -m pytest tests/theme_sector_radar/ -v
```

**结果**: ✅ 204 passed in 169.90s

## 10. 四个专项测试结果

```bash
python -m pytest tests/theme_sector_radar/test_daily_data_source_semantics.py -v
python -m pytest tests/theme_sector_radar/test_index_scan_scope.py -v
python -m pytest tests/theme_sector_radar/test_run_log_source_traceability.py -v
python -m pytest tests/theme_sector_radar/test_replay_cache_source_integrity.py -v
```

**结果**: ✅ 全部通过

## 11. daily fixture CLI 结果

```bash
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --offline-fixture --fixture-profile rotation-day2 --lookback-days 5 --report-root reports/theme_sector_radar
```

**结果**: ✅ 运行成功
- fixture_profile: rotation-day2
- concept_top: CPO概念, ChatGPT概念, 人工智能概念（rotation-day2 fixture 数据）
- 数据来源字段正确

## 12. index.json 示例

```json
{
  "generated_at": "2026-06-29T11:45:24.012510",
  "report_root": "reports/theme_sector_radar",
  "reports": [
    {
      "as_of_date": "2026-06-28",
      "status": "degraded",
      "data_quality_score": 67.0,
      "market_temperature_label": "hot",
      "top_industries": ["半导体", "人工智能", "芯片"],
      "top_concepts": ["CPO概念", "ChatGPT概念", "人工智能概念"],
      "source_report_dir": "reports/theme_sector_radar/2026-06-28",
      "data_source_mode": "fixture",
      "fixture_profile": "rotation-day2"
    }
  ]
}
```

## 13. 是否仍然完全未修改原 ai-hedge-fund 项目

**✅ 完全未修改**

原项目 `E:\Workspace\ai-stock-projects\ai-hedge-fund` 的文件未被修改：
- `src/main.py` - 未修改
- `src/agents/common.py` - 未修改

## 14. 硬性边界遵守情况

- ✅ 不允许修改 `E:\Workspace\ai-stock-projects\ai-hedge-fund`
- ✅ 不允许接入 LangGraph
- ✅ 不允许注册到 `ANALYST_CONFIG`
- ✅ 不允许输出个股推荐
- ✅ 不允许输出 buy/sell/hold
- ✅ 不允许输出买入、卖出、持有建议
- ✅ 不允许自动交易
