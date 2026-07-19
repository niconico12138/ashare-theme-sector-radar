import copy
import sys
from pathlib import Path

import pytest

from theme_sector_radar.scoring.stock_sector_linkage import (
    build_formal_candidate_selection,
)
from unified_pipeline import _activate_formal_candidate_chain


PROTECTED_FIELDS = {
    "quant_score",
    "final_score",
    "v2_score",
    "selection_score",
    "selection_score_adjusted",
}


def _selected_row(code="600001"):
    return {
        "code": code,
        "name": "Test Stock",
        "sector_name": "Test Sector",
        "sector_type": "industry",
        "candidate_tier": "core",
        "sector_direction_score": 78.0,
        "direction_score_shadow": 78.0,
        "quant_score": 81.0,
        "final_score": 72.0,
        "v2_score": 0.88,
        "selection_score": 69.0,
        "selection_score_adjusted": 68.0,
        "linkage_v2_shadow": {"status": "ok", "score": 0.88},
    }


def _direction_source(status="ok"):
    return {
        "status": status,
        "mode": "paper_shadow_research_only",
        "path": "direction.json",
        "sha256": "a" * 64,
    }


def _linkage_selection(rows):
    return {
        "schema_version": "direction_linkage_v2_selection_shadow.v1",
        "mode": "paper_shadow_research_only",
        "selected": rows,
        "selected_count": len(rows),
        "policy": {"ranking_weights": {"linkage_v2": 0.70, "quant_score": 0.30}},
    }


def test_formal_replacement_uses_direction_and_v2_selected_rows_without_score_mutation():
    rows = [_selected_row()]
    before = copy.deepcopy(rows)

    result = build_formal_candidate_selection(
        direction_source=_direction_source(),
        linkage_selection=_linkage_selection(rows),
    )

    assert result["status"] == "active_for_paper_research"
    assert result["candidate_chain"] == "direction_score_then_linkage_v2"
    assert result["selected_count"] == 1
    assert result["selected"][0]["code"] == "600001"
    assert rows == before
    assert {
        field: result["selected"][0][field]
        for field in PROTECTED_FIELDS
    } == {
        field: before[0][field]
        for field in PROTECTED_FIELDS
    }


@pytest.mark.parametrize(
    "direction_source,linkage_selection",
    [
        (_direction_source("unavailable"), _linkage_selection([_selected_row()])),
        (_direction_source(), {"schema_version": "wrong", "selected": []}),
        (_direction_source(), _linkage_selection([])),
    ],
)
def test_formal_replacement_fails_closed_without_usable_verified_inputs(
    direction_source, linkage_selection
):
    result = build_formal_candidate_selection(
        direction_source=direction_source,
        linkage_selection=linkage_selection,
    )

    assert result["status"] == "unavailable"
    assert result["selected"] == []
    assert result["fallback_used"] is False
    assert result["candidate_chain"] == "direction_score_then_linkage_v2"


def test_formal_replacement_rejects_selected_row_without_direction_identity():
    row = _selected_row()
    row.pop("sector_direction_score")
    row.pop("direction_score_shadow")

    with pytest.raises(ValueError, match="direction score"):
        build_formal_candidate_selection(
            direction_source=_direction_source(),
            linkage_selection=_linkage_selection([row]),
        )


def test_pipeline_activation_routes_active_candidate_pool_to_replacement_chain():
    result = _activate_formal_candidate_chain(
        candidate_chain="direction_linkage_v2",
        direction_source=_direction_source(),
        linkage_selection=_linkage_selection([_selected_row()]),
    )

    assert result["status"] == "active_for_paper_research"
    assert result["selected"][0]["code"] == "600001"


def test_pipeline_activation_does_not_fallback_to_legacy_when_replacement_is_unavailable():
    result = _activate_formal_candidate_chain(
        candidate_chain="direction_linkage_v2",
        direction_source=_direction_source("unavailable"),
        linkage_selection=_linkage_selection([_selected_row()]),
    )

    assert result["status"] == "unavailable"
    assert result["selected"] == []
    assert result["fallback_used"] is False


def test_pipeline_legacy_mode_exposes_deduplicated_active_pool_only_when_explicit():
    first = _selected_row("600001")
    second = _selected_row("600002")
    duplicate = copy.deepcopy(first)

    result = _activate_formal_candidate_chain(
        candidate_chain="legacy",
        direction_source={},
        linkage_selection={},
        legacy_candidates=[first, second, duplicate],
    )

    assert result["status"] == "legacy_active_for_paper_research"
    assert [row["code"] for row in result["selected"]] == ["600001", "600002"]
    assert result["selected_count"] == 2


def test_unified_pipeline_publishes_direction_linkage_v2_as_active_pool(
    tmp_path, monkeypatch
):
    import unified_pipeline as pipeline

    sectors = []
    for index, name in enumerate(("Sector A", "Sector B", "Sector C"), 1):
        sectors.append(
            {
                "sector_name": name,
                "sector_type": "industry",
                "trend_score": 60.0,
                "burst_score": 50.0,
                "candidate_tier": "core",
                "direction_score_shadow": 75.0 + index,
                "direction_state": "stable_core",
                "shadow_prefilter_stocks": [
                    {
                        "code": f"60000{index}",
                        "name": f"Stock {index}",
                        "relevance_score": 0.5,
                        "quote_available": True,
                    }
                ],
            }
        )
    bridge_result = {
        "status": "ok",
        "as_of_date": "2026-07-17",
        "trend_sectors": [
            {
                "sector_name": "Legacy Trend",
                "trend_score": 90.0,
                "burst_score": 80.0,
                "stocks": [
                    {
                        "code": "600099",
                        "name": "Legacy Stock",
                        "relevance_score": 0.9,
                    }
                ],
            }
        ],
        "burst_sectors": [],
        "direction_shadow_sectors": sectors,
        "direction_confirmation_sectors": [],
        "cross_sectors": [],
        "constituent_source_summary": {},
        "api_status": {},
        "linkage_research": {
            "direction_shadow_input": _direction_source(),
        },
    }
    validated = (
        "2026-07-17",
        tmp_path / "sector_scores.json",
        {"as_of_date": "2026-07-17", "scores": []},
    )

    def fake_quant(stocks, **_kwargs):
        for row in stocks:
            row["quant_score"] = 70.0
            row["quant_source"] = "fixture"
            row["quant_breakdown"] = {}
            row["linkage_v2_shadow"] = {
                "schema_version": "stock_sector_linkage_v2_shadow.v1",
                "mode": "paper_shadow_research_only",
                "status": "ok",
                "score": 0.8,
            }
        pipeline.compute_quant_scores._last_fund_flow_source = "fixture"
        pipeline.compute_quant_scores._last_bars_audit = {
            "source": "fixture",
            "reason": "fixture",
            "latest_daily_date": "20260717",
            "requested_stock_count": len(stocks),
            "usable_stock_count": len(stocks),
            "requested_relation_count": len(stocks),
            "usable_relation_count": len(stocks),
            "coverage_ratio": 1.0,
            "minimum_bars": 5,
        }
        return stocks

    monkeypatch.setattr(
        pipeline,
        "validate_explicit_score_report",
        lambda _date: (True, validated, None),
    )
    bridge_calls = []

    def fake_bridge(**kwargs):
        bridge_calls.append(kwargs)
        return bridge_result

    monkeypatch.setattr(pipeline, "run_bridge", fake_bridge)
    monkeypatch.setattr(pipeline, "_get_http_client", lambda: None)
    monkeypatch.setattr(pipeline, "compute_quant_scores", fake_quant)
    monkeypatch.setattr(
        pipeline,
        "load_sector_cluster_map",
        lambda _path: (
            {"Sector A": "A", "Sector B": "B", "Sector C": "C"},
            {
                "schema_version": "path_a_sector_cluster_map.v1",
                "mode": "paper_shadow_research_only",
                "status": "ok",
                "mapping": {"Sector A": "A", "Sector B": "B", "Sector C": "C"},
            },
        ),
    )

    result = pipeline.run_pipeline(
        as_of_date="2026-07-17",
        output_dir=str(tmp_path / "out"),
    )

    assert result["status"] == "ok"
    assert result["candidate_chain"] == "direction_linkage_v2"
    assert result["legacy_sector_paths_enabled"] is False
    assert result["active_sector_path"] == "direction_score"
    assert result["trend_top_stocks"] == []
    assert result["burst_top_stocks"] == []
    assert bridge_calls[0]["include_legacy_sector_paths"] is False
    assert result["formal_candidate_selection"]["status"] == (
        "active_for_paper_research"
    )
    assert [row["code"] for row in result["active_candidates_all"]] == [
        "600001",
        "600002",
        "600003",
    ]
    assert all(
        row["sector_direction_score"] >= 76.0
        for row in result["active_candidates_all"]
    )


def test_daily_wrapper_activates_direction_linkage_v2_child_chain(monkeypatch):
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root / "scripts"))
    import run_daily_unified_pipeline as daily

    calls = []
    monkeypatch.setattr(
        daily.subprocess,
        "run",
        lambda cmd, **kwargs: calls.append((cmd, kwargs)),
    )

    daily._run_unified_pipeline(as_of="2026-07-17", mode="quick")

    command = calls[0][0]
    assert command[command.index("--candidate-chain") + 1] == (
        "direction_linkage_v2"
    )
