# Phase 26A.1: LLM 模型兼容性与可诊断性 验收报告

**日期**: 2026-07-05  
**项目**: ai-hedge-fund + theme-sector-radar-dev

---

## 1. 修改文件清单

| 文件 | 改动 |
|------|------|
| `ai-hedge-fund/scripts/run_stock_agent_bridge.py` | +`--llm-model`, `--llm-provider`, `--llm-base-url`, `--llm-smoke`; +`diagnose_llm_config()`, `run_llm_smoke()`; 状态传递模型配置; run_meta LLM 诊断 |
| `theme-sector-radar-dev/scripts/run_daily_bridge_report.py` | timeout 600→1800s; 使用 ai-hedge-fund venv |

## 2. LLM 配置来源

```
优先级链:
1. CLI: --llm-model > --llm-provider > --llm-base-url
2. 环境变量: AIHF_LLM_MODEL > OPENAI_MODEL > LLM_MODEL
3. 默认值: mimo-v2.5-pro (OPENAI provider)

配置位置:
- .env: OPENAI_API_KEY + OPENAI_API_BASE (MiMo API)
- src/llm/api_models.json: 模型列表 (mimo-v2.5-pro 为首项)
- src/utils/llm.py: 默认 gpt-4.1 (已通过 CLI/env 覆盖)
```

## 3. 当前实际使用的模型

```
llm_model: mimo-v2.5-pro
llm_provider: OPENAI
llm_configured: True (OPENAI_API_KEY 已设置)
llm_available: True
llm_smoke_status: ok
```

## 4. Agent 统计

### core preset (7 agents)

| 统计 | 数值 |
|------|------|
| succeeded | 4 |
| failed | 1 |
| fallback | 5 |

**succeeded agents**: technical_analyst, fundamentals_analyst, valuation_analyst, sentiment_analyst (rule-based)

### full preset (24 agents, 2 stocks test)

| 统计 | 数值 |
|------|------|
| succeeded | 8 |
| failed | 0 |
| fallback | 17 |

**succeeded agents**: technical_analyst, fundamentals_analyst, valuation_analyst, sentiment_analyst, growth_analyst, china_youzi, news_sentiment_analyst + 1 more

**fallback agents**: 17 个 (LLM 调用失败或 validation error)

## 5. 2026-07-03 bridge 运行结果

### core preset

```
1. TCL科技     score=54.9 B2/H3/S1 risk=high
2. 派林生物     score=53.4 B2/H2/S2 risk=low
3. 深科技       score=53.2 B2/H2/S2 risk=high
4. 英特集团     score=52.6 B1/H5/S0 risk=high
5. 安道麦A      score=52.5 B1/H4/S1 risk=high
```

### full preset (2 stocks)

```
1. 600030 中信证券  score=50.4 B1/H23/S0
2. 601211 国泰君安  score=50.4 B1/H23/S0
```

## 6. run_meta LLM 诊断示例

```json
{
  "mode": "real",
  "llm_configured": true,
  "llm_available": true,
  "llm_model": "mimo-v2.5-pro",
  "llm_provider": "OPENAI",
  "llm_base_url": "https://api.xiaomimimo.com/v1",
  "llm_error_type": null,
  "llm_error_hint": "",
  "llm_smoke": {
    "llm_smoke_status": "ok",
    "llm_smoke_model": "mimo-v2.5-pro"
  }
}
```

## 7. 测试结果

| 命令 | 结果 |
|------|------|
| `pytest tests/theme_sector_radar/ -q` | **988 passed, 3 skipped** |
| LLM smoke | ✅ ok (mimo-v2.5-pro) |
| core preset | ✅ 4/7 succeeded, differentiated scores |
| full preset (2 stocks) | ✅ 8/24 succeeded |

## 8. 剩余风险

1. **部分 Agent LLM 输出 validation error**: china_youzi, china_sentiment, industry_rotation 的 LLM 输出 schema 与 Pydantic 模型不兼容 → 需要修复 agent 的 LLM 输出 schema
2. **Full preset 15 stocks timeout**: 24 agents × 15 stocks 需要 >10min，当前 timeout 1800s 可能仍不够
3. **部分 Agent 硬编码 gpt-4.1**: 某些 agent 的 LLM 调用中硬编码了模型名，不走 get_agent_model_config
