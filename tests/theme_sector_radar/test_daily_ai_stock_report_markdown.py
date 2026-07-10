from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "run_daily_ai_stock_report.py"


def _load_daily_module():
    spec = importlib.util.spec_from_file_location("run_daily_ai_stock_report", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_stock_agent_ranking_table_includes_v3_scores():
    """v3 报告应包含综合分、量化分、Agent分、共振加分等字段"""
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

    # v3 新报告结构
    assert "快速决策" in md
    assert "综合分" in md
    assert "量化" in md
    assert "Agent" in md
    assert "共振" in md
    assert "板块" in md
    assert "000536" in md
    assert "华映科技" in md
    assert "光刻胶" in md


def test_report_has_quick_decision_sections():
    """报告应包含快速决策分类"""
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

    # 应包含快速决策分类
    assert "重点关注" in md or "观察" in md or "谨慎" in md
    assert "个股完整排名" in md
    assert "个股分析明细" in md
    assert "Agent 运行统计" in md
    assert "数据源" in md

