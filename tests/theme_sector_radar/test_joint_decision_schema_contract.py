import copy
import json


def _sample_summary():
    from theme_sector_radar.joint_decision.builder import build_joint_decision_summary

    return build_joint_decision_summary(
        as_of="2026-07-10",
        unified_report={
            "run_health": {"status": "pass"},
            "data_quality": {"status": "pass"},
            "trend_top_stocks": [
                {
                    "code": "600001",
                    "name": "Alpha",
                    "sector_name": "Semiconductor",
                    "final_score": 76.0,
                    "factor_composite_shadow_score_v2": 61.0,
                    "selection_score": 71.5,
                    "selection_score_adjusted": 73.0,
                    "sector_support_score": 72.0,
                    "liquidity_score": 64.0,
                    "breakout_distance_20": 0.08,
                    "drawdown_depth_20": -0.05,
                    "chasing_risk_score": 18.0,
                }
            ],
            "burst_top_stocks": [],
        },
        sectors=[
            {
                "sector_name": "Semiconductor",
                "sector_type": "concept",
                "ranking_score": 78.0,
                "trend_continuation_score": 71.0,
                "confidence_score": 0.82,
                "consensus_label": "trend_confirmed",
            }
        ],
        top30={"candidates": []},
        aihf_ranking={"items": [{"code": "600001", "agent_score": 74.0, "risk_level": "medium"}]},
        v2_monitor={"status_light": {"status": "ok"}},
        top_n=5,
    )


def test_joint_decision_summary_has_stable_watch_only_contract():
    summary = _sample_summary()

    assert summary["schema_version"] == "1.0"
    assert summary["decision_mode"] == "watch_only"
    risk_gate = summary["risk_gate"]
    assert risk_gate["allow_observation"] is True
    assert risk_gate["allow_trade_candidate_generation"] is False
    assert risk_gate["blockers"] == []
    assert risk_gate["warnings"] == []
    assert risk_gate["gate_details"] == {
        "data_quality_gate": {"status": "pass", "allow_observation": True, "blockers": [], "warnings": []},
        "run_health_gate": {"status": "pass", "allow_observation": True, "blockers": [], "warnings": []},
        "market_regime_gate": {"status": "unknown", "allow_observation": True, "blockers": [], "warnings": []},
        "factor_quality_gate": {"status": "ok", "allow_observation": True, "blockers": [], "warnings": []},
        "agent_consensus_gate": {"status": "confirmed", "allow_observation": True, "blockers": [], "warnings": []},
    }
    assert summary["audit"]["source_artifacts"] == {
        "unified_report": True,
        "top30_candidates": True,
        "aihf_ranking": True,
        "v2_monitor": True,
    }
    assert summary["audit"]["shadow_only"] is True
    assert isinstance(summary["audit"]["generated_at"], str)
    assert summary["audit"]["generated_at"].endswith("Z")


def test_stock_decision_items_keep_scores_nested_and_watch_only():
    stock = _sample_summary()["stock_decision"]["core_watch"][0]

    assert stock["decision_bucket"] == "core_watch"
    assert stock["action_state"] == "watch_only"
    assert stock["scores"] == {
        "final_score": 76.0,
        "v2_score": 61.0,
        "selection_score": 71.5,
        "selection_score_adjusted": 73.0,
    }
    assert stock["factor_states"] == {
        "trend_state": "trend_follow",
        "sector_support": "confirmed",
        "breakout_structure": "near_breakout",
        "drawdown_state": "controlled",
        "liquidity_state": "available",
        "overheat_state": "normal",
    }
    assert stock["invalidation_flags"] == []
    assert stock["manual_review_reason"] == []


def test_joint_decision_summary_avoids_trade_trigger_language():
    text = json.dumps(_sample_summary(), ensure_ascii=False).lower()

    forbidden_terms = [
        "buy_point",
        "entry_price",
        "trigger_price",
        "stop_loss",
        "take_profit",
        "order",
        "execute_trade",
    ]
    for term in forbidden_terms:
        assert term not in text


def test_risk_gate_details_surface_blockers_without_trade_generation():
    from theme_sector_radar.joint_decision.builder import build_joint_decision_summary

    summary = build_joint_decision_summary(
        as_of="2026-07-10",
        unified_report={
            "run_health": {"status": "fail", "reasons": ["pipeline_failed"]},
            "data_quality": {"status": "fail", "warnings": ["coverage_low"]},
            "trend_top_stocks": [],
            "burst_top_stocks": [],
        },
        top30={},
        aihf_ranking={},
        v2_monitor={},
        top_n=5,
        load_warnings=["missing:upstream_artifact"],
    )

    risk_gate = summary["risk_gate"]

    assert risk_gate["allow_observation"] is False
    assert risk_gate["allow_trade_candidate_generation"] is False
    assert risk_gate["gate_details"]["run_health_gate"] == {
        "status": "fail",
        "allow_observation": False,
        "blockers": ["run_health_fail"],
        "warnings": ["pipeline_failed"],
    }
    assert risk_gate["gate_details"]["data_quality_gate"] == {
        "status": "fail",
        "allow_observation": False,
        "blockers": ["data_quality_fail"],
        "warnings": ["coverage_low"],
    }
    assert risk_gate["gate_details"]["factor_quality_gate"] == {
        "status": "missing",
        "allow_observation": True,
        "blockers": [],
        "warnings": ["v2_monitor_missing"],
    }
    assert "run_health_fail" in risk_gate["blockers"]
    assert "data_quality_fail" in risk_gate["blockers"]
    assert "coverage_low" in risk_gate["warnings"]
    assert "missing:upstream_artifact" in risk_gate["warnings"]



def test_joint_decision_schema_runbook_documents_watch_only_contract():
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent.parent
    doc_path = project_root / "docs" / "runbooks" / "joint_decision_schema.md"

    assert doc_path.exists(), f"missing schema runbook: {doc_path}"
    content = doc_path.read_text(encoding="utf-8")

    required_terms = [
        "joint_decision_summary",
        "schema_version",
        "decision_mode",
        "watch_only",
        "risk_gate",
        "gate_details",
        "allow_trade_candidate_generation",
        "false",
        "audit",
        "shadow_only",
        "scores",
        "factor_states",
        "contract_validation",
        "validate_joint_decision_summary",
        "show_daily_result",
    ]
    for term in required_terms:
        assert term in content

    forbidden_terms = ["buy_point", "entry_price", "trigger_price", "stop_loss", "take_profit", "execute_trade"]
    for term in forbidden_terms:
        assert term in content


def test_validate_joint_decision_summary_accepts_current_contract():
    from theme_sector_radar.joint_decision.contract import validate_joint_decision_summary

    errors = validate_joint_decision_summary(_sample_summary())

    assert errors == []


def test_validate_joint_decision_summary_rejects_trade_semantics():
    from theme_sector_radar.joint_decision.contract import validate_joint_decision_summary

    summary = copy.deepcopy(_sample_summary())
    summary["decision_mode"] = "trade_ready"
    summary["risk_gate"]["allow_trade_candidate_generation"] = True
    stock = summary["stock_decision"]["core_watch"][0]
    stock["action_state"] = "trade_ready"
    stock["buy_point"] = 10.0

    errors = validate_joint_decision_summary(summary)

    assert "decision_mode must be watch_only" in errors
    assert "risk_gate.allow_trade_candidate_generation must be false" in errors
    assert "stock_decision.core_watch[0].action_state must be watch_only" in errors
    assert "forbidden trade field present: buy_point" in errors



def test_joint_decision_package_exports_contract_validator():
    from theme_sector_radar.joint_decision import validate_joint_decision_summary

    assert validate_joint_decision_summary(_sample_summary()) == []



def test_joint_decision_phase_completion_runbook_exists():
    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent.parent
    doc_path = project_root / "docs" / "runbooks" / "joint_decision_phase_completion.md"

    assert doc_path.exists(), f"missing phase completion runbook: {doc_path}"
    content = doc_path.read_text(encoding="utf-8")

    required_terms = [
        "90%",
        "watch_only",
        "validate_joint_decision_summary",
        "audit.contract_validation",
        "show_daily_result",
        "allow_trade_candidate_generation",
        "false",
        "final_score",
        "v2_score",
        "selection_score",
        "non-LLM",
        "not implemented",
        "automatic trading",
    ]
    for term in required_terms:
        assert term in content
