from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(r"E:\liaohua\01_projects\theme-sector-radar-dev")
SCRIPT = ROOT / "scripts" / "run_daily_ai_stock_report.py"


def _load_daily_module():
    spec = importlib.util.spec_from_file_location("run_daily_ai_stock_report", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_stock_agent_ranking_table_includes_trend_and_burst_scores():
    module = _load_daily_module()
    sector_data = {"industries": [], "concepts": []}
    stock_ranking = {
        "run_meta": {
            "agent_preset": "selected",
            "agent_count": 7,
            "requested_agents": [],
            "llm_status": {"configured": True, "available": True, "model": "mimo-v2.5-pro"},
        },
        "items": [
            {
                "rank": 1,
                "code": "000536",
                "name": "华映科技",
                "source_pool": "trend",
                "source_boards": ["光刻胶"],
                "trend_score": 62.45,
                "burst_score": 30.3,
                "relevance_score": 0.833,
                "quant_score": 61.2,
                "final_score": 70.1,
                "agent_score": 55.7,
                "risk_adjusted_score": 55.7,
                "risk_level": "low",
                "contributing_agents": 5,
                "top_positive_agents": [],
                "top_negative_agents": [],
                "fallback_agents": [],
                "bullish_count": 2,
                "neutral_count": 3,
                "bearish_count": 0,
            }
        ],
    }
    candidate_pool = {"candidates": []}
    md = module.build_markdown_report(
        "2026-07-03",
        sector_data,
        stock_ranking,
        top_n=10,
        candidate_pool=candidate_pool,
        deps={},
    )

    stock_rank_section = md.split("## 4.", 1)[1].split("## 5.", 1)[0]
    assert "来源池" in stock_rank_section
    assert "来源板块" in stock_rank_section
    assert "趋势分" in stock_rank_section
    assert "短线分" in stock_rank_section
    assert "Agent分" in stock_rank_section
    assert "风险调整" in stock_rank_section
    assert "trend" in stock_rank_section
    assert "光刻胶" in stock_rank_section
    assert "62.5" in stock_rank_section
    assert "30.3" in stock_rank_section

    assert "关联度" in stock_rank_section

    assert "量化分" in stock_rank_section

    assert "初筛综合" in stock_rank_section

    assert "0.833" in stock_rank_section

    assert "61.2" in stock_rank_section

    assert "70.1" in stock_rank_section
