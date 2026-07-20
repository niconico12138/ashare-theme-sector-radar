import json
from pathlib import Path

import pytest


def test_tool_contract_is_paper_only_and_exposes_stable_research_tools():
    from theme_sector_radar.mcp.server import TOOL_SPECS, safety_envelope

    names = [item["name"] for item in TOOL_SPECS]
    assert names == [
        "check_data_health",
        "get_direction_candidates",
        "get_stock_ranking",
        "run_full_paper_pipeline",
    ]
    assert all(item["read_only"] for item in TOOL_SPECS[:3])
    assert TOOL_SPECS[3]["mode"] == "paper_shadow_research_only"
    assert safety_envelope() == {
        "mode": "paper_shadow_research_only",
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "broker_connected": False,
        "order_instruction_generated": False,
    }


def test_report_tool_fails_closed_when_report_date_does_not_match(tmp_path: Path):
    from theme_sector_radar.mcp.server import get_stock_ranking

    report = tmp_path / "unified_report.json"
    report.write_text(
        json.dumps({"as_of_date": "2026-07-19", "formal_candidate_selection": {}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="report date mismatch"):
        get_stock_ranking("2026-07-20", report_path=str(report))


def test_direction_tool_returns_empty_research_result_for_missing_source(tmp_path: Path):
    from theme_sector_radar.mcp.server import get_direction_candidates

    result = get_direction_candidates(
        "2026-07-20", candidates_path=str(tmp_path / "missing.json")
    )

    assert result["status"] == "unavailable"
    assert result["selected_count"] == 0
    assert result["promotion_allowed"] is False

