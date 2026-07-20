# MCP Paper/Shadow 接入

本项目的评分、数据、Linkage V2 和 ML 模块仍是唯一事实来源。MCP 只提供
稳定的结构化调用边界，不复制评分公式，也不连接券商。

## 工具

| 工具 | 作用 | 是否写报告 |
|---|---|---:|
| `check_data_health` | 检查 market_data_service 健康状态 | 否 |
| `get_direction_candidates` | 读取指定日期方向分候选 artifact | 否 |
| `get_stock_ranking` | 读取指定日期 formal paper/shadow 排名 | 否 |
| `run_full_paper_pipeline` | 调用现有 unified pipeline | 是 |

所有工具返回以下安全状态：

```json
{
  "mode": "paper_shadow_research_only",
  "promotion_allowed": false,
  "live_trading_allowed": false,
  "formal_predictor_compatible": false,
  "broker_connected": false,
  "order_instruction_generated": false
}
```

## 运行

安装可选依赖：

```powershell
python -m pip install -e ".[mcp]"
```

启动 stdio MCP server：

```powershell
python -m theme_sector_radar.mcp.server
```

如果本机 MCP SDK 与 Python/Windows 版本不兼容，研究函数仍可直接导入和测试，
但 server 启动会明确失败并要求安装兼容的 `mcp` 版本，不会静默降级成未知协议。

## Skill 规范

Codex/Agent 的调用规范见：
`docs/skills/theme_sector_radar_research/SKILL.md`。

MCP 工具必须传入 canonical ISO 日期。报告日期不匹配、缺失或健康门禁失败时，
调用方必须保留 `unavailable` / `fail`，不得用旧报告、当前值或 fixture 冒充结果。

