import json
from pathlib import Path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_build_joint_decision_summary_preserves_watch_only_and_scores():
    from theme_sector_radar.joint_decision.builder import build_joint_decision_summary

    unified_report = {
        "run_health": {"status": "pass"},
        "data_quality": {"status": "pass"},
        "trend_top_stocks": [
            {
                "code": "600001",
                "name": "Alpha",
                "sector_name": "Semiconductor",
                "source_pool": "trend_top",
                "final_score": 76.0,
                "factor_composite_shadow_score_v2": 61.0,
                "sector_support_score": 72.0,
            }
        ],
        "burst_top_stocks": [],
    }
    sectors = [
        {
            "sector_name": "Semiconductor",
            "sector_type": "concept",
            "ranking_score": 78.0,
            "opportunity_score": 70.0,
            "confidence_score": 0.82,
            "consensus_label": "trend_confirmed",
        }
    ]
    concepts = []
    top30 = {
        "candidates": [
            {
                "code": "600001",
                "name": "Alpha",
                "sector_name": "Semiconductor",
                "final_score": 76.0,
                "factor_composite_shadow_score_v2": 61.0,
                "factor_snapshot": {"schema_version": "1.0", "factors": []},
            }
        ]
    }
    aihf_ranking = {
        "items": [
            {
                "code": "600001",
                "agent_score": 74.0,
                "risk_adjusted_score": 70.0,
                "risk_level": "medium",
                "contributing_agents": 7,
            }
        ]
    }

    summary = build_joint_decision_summary(
        as_of="2026-07-10",
        unified_report=unified_report,
        sectors=sectors,
        concepts=concepts,
        top30=top30,
        aihf_ranking=aihf_ranking,
        v2_monitor=None,
        top_n=5,
    )

    assert summary["schema_version"] == "1.0"
    assert summary["decision_mode"] == "watch_only"
    assert summary["system_status"]["run_health"] == "pass"
    assert summary["sector_decision"]["primary_watch"][0]["sector_name"] == "Semiconductor"

    stock = summary["stock_decision"]["core_watch"][0]
    assert stock["code"] == "600001"
    assert stock["action_state"] == "watch_only"
    assert stock["final_score"] == 76.0
    assert stock["v2_score"] == 61.0
    assert stock["agent_review_state"] == "confirmed"

    assert summary["agent_review"]["coverage"] == 1.0
    assert summary["agent_review"]["confirmed"][0]["code"] == "600001"
    assert summary["factor_context"]["official_score_factors"] == ["final_score"]


def test_load_joint_decision_inputs_reads_existing_artifacts_and_degrades_missing(tmp_path):
    from theme_sector_radar.joint_decision.loader import load_joint_decision_inputs

    as_of = "2026-07-10"
    _write_json(
        tmp_path / "reports" / "unified" / as_of / "unified_report.json",
        {"run_health": {"status": "warn"}, "data_quality": {"status": "pass"}},
    )
    _write_json(
        tmp_path / "reports" / "agent_bridge" / as_of / "top30_candidates.json",
        {"candidates": [{"code": "600001"}]},
    )

    loaded = load_joint_decision_inputs(as_of, project_root=tmp_path)

    assert loaded["unified_report"]["run_health"]["status"] == "warn"
    assert loaded["top30"]["candidates"][0]["code"] == "600001"
    assert loaded["aihf_ranking"] == {}
    assert "missing:reports/agent_bridge/2026-07-10/aihf_stock_ranking.json" in loaded["load_warnings"]


def test_render_joint_decision_markdown_is_compact_and_watch_only():
    from theme_sector_radar.joint_decision.report import render_joint_decision_markdown

    summary = {
        "as_of": "2026-07-10",
        "decision_mode": "watch_only",
        "system_status": {"run_health": "pass", "data_quality": "pass", "allow_observation": True},
        "sector_decision": {
            "primary_watch": [{"sector_name": "Semiconductor", "decision_bucket": "trend_confirmed"}],
            "short_burst_watch": [],
            "review": [],
            "avoid": [],
        },
        "stock_decision": {
            "core_watch": [
                {
                    "code": "600001",
                    "name": "Alpha",
                    "sector_name": "Semiconductor",
                    "opportunity_type": "trend_follow",
                    "final_score": 76.0,
                    "v2_score": 61.0,
                    "agent_review_state": "confirmed",
                    "action_state": "watch_only",
                }
            ],
            "v2_opportunity": [],
            "short_burst": [],
            "divergence_review": [],
            "blocked": [],
        },
        "risk_review": {"warnings": [], "blockers": []},
    }

    markdown = render_joint_decision_markdown(summary, top_n=5)

    assert "# Joint Decision 2026-07-10" in markdown
    assert "watch_only" in markdown
    assert "Semiconductor" in markdown
    assert "600001" in markdown
    assert "No price levels or execution actions are generated." in markdown


def test_run_joint_decision_writes_json_and_markdown(tmp_path):
    from theme_sector_radar.joint_decision.runner import run_joint_decision

    as_of = "2026-07-10"
    _write_json(
        tmp_path / "reports" / "unified" / as_of / "unified_report.json",
        {
            "run_health": {"status": "pass"},
            "data_quality": {"status": "pass"},
            "trend_top_stocks": [
                {"code": "600001", "name": "Alpha", "final_score": 70.0, "sector_name": "Semiconductor"}
            ],
            "burst_top_stocks": [],
        },
    )

    result = run_joint_decision(as_of, project_root=tmp_path, top_n=5)

    assert result["json"].exists()
    assert result["md"].exists()
    payload = json.loads(result["json"].read_text(encoding="utf-8"))
    assert payload["decision_mode"] == "watch_only"
    assert payload["stock_decision"]["core_watch"][0]["code"] == "600001"



def test_run_joint_decision_embeds_contract_validation_result(tmp_path):
    from theme_sector_radar.joint_decision.runner import run_joint_decision

    as_of = "2026-07-10"
    _write_json(
        tmp_path / "reports" / "unified" / as_of / "unified_report.json",
        {
            "run_health": {"status": "pass"},
            "data_quality": {"status": "pass"},
            "trend_top_stocks": [
                {
                    "code": "600001",
                    "name": "Alpha",
                    "final_score": 70.0,
                    "factor_composite_shadow_score_v2": 60.0,
                    "sector_name": "Semiconductor",
                }
            ],
            "burst_top_stocks": [],
        },
    )

    result = run_joint_decision(as_of, project_root=tmp_path, top_n=5)
    payload = json.loads(result["json"].read_text(encoding="utf-8"))

    assert payload["audit"]["contract_validation"] == {"status": "pass", "errors": []}


def test_joint_decision_factor_states_use_factor_snapshot_raw_values():
    from theme_sector_radar.joint_decision.policy import normalize_stock

    candidate = {
        "code": "600001",
        "name": "Alpha",
        "final_score": 72.0,
        "factor_composite_shadow_score_v2": 64.0,
        "factor_snapshot": {
            "factors": [
                {"factor_id": "sector_support_score", "raw_value": 70.0, "score": 70.0, "quality": "good"},
                {"factor_id": "breakout_distance_20", "raw_value": 2.5, "score": 85.0, "quality": "good"},
                {"factor_id": "drawdown_depth_20", "raw_value": 18.0, "score": 35.0, "quality": "good"},
                {"factor_id": "liquidity_score", "raw_value": 80.0, "score": 80.0, "quality": "good"},
                {"factor_id": "chasing_risk_score", "raw_value": 72.0, "score": 72.0, "quality": "good"},
            ]
        },
    }

    stock = normalize_stock(candidate, agent_lookup={}, source_pool="trend_top")

    assert stock["sector_support_score"] == 70.0
    assert stock["factor_states"] == {
        "trend_state": "trend_follow",
        "sector_support": "confirmed",
        "breakout_structure": "near_breakout",
        "drawdown_state": "deep",
        "liquidity_state": "available",
        "overheat_state": "high",
    }
