from __future__ import annotations

import copy

import pytest


def _case():
    from theme_sector_radar.data.event_adjustment_ranking_shadow import build_copper_ranking_ab_research_case

    return build_copper_ranking_ab_research_case()


def _assert_no_formal_fields(value):
    forbidden = {"score", "rank", "final_score", "quant_score", "v2_score", "selection_score"}
    if isinstance(value, dict):
        for key in value:
            normalized = str(key).casefold()
            assert normalized not in forbidden
            assert not normalized.endswith("_score")
        for child in value.values():
            _assert_no_formal_fields(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_formal_fields(child)


def test_base_snapshot_sha_and_pit_are_bound_without_formal_fields():
    from theme_sector_radar.data.event_adjustment_ranking_shadow import validate_base_ranking_snapshot

    case = _case()
    base = case["base_snapshot"]
    assert base["pit_status"] == "fixture_verified"
    assert base["effective_from"] == base["as_of_date"]
    assert len(base["snapshot_sha256"]) == 64
    validate_base_ranking_snapshot(base)
    tampered = copy.deepcopy(base)
    tampered["rows"][0]["base_value"] += 1
    with pytest.raises(ValueError, match="SHA mismatch"):
        validate_base_ranking_snapshot(tampered)
    _assert_no_formal_fields(base)


def test_adjustment_manifest_sha_and_post_event_exclusion_are_bound():
    from theme_sector_radar.data.event_adjustment_ranking_shadow import (
        validate_event_adjustment_manifest,
    )

    case = _case()
    manifest = case["adjustment_manifest"]
    adjustment = case["ab_shadow"]
    assert manifest["post_event_backtest_included"] is False
    assert manifest["artifact_sha256"]
    assert manifest["manifest_sha256"]
    assert adjustment["pit_binding"]["post_event_backtest_included"] is False
    validate_event_adjustment_manifest(manifest, case["adjustment"])


def _adjustment_from_case(case):
    return case["adjustment"]


def test_ab_preserves_a_fields_and_emits_only_research_b_fields():
    case = _case()
    ab = case["ab_shadow"]
    a_rows = {row["entity_id"]: row for row in ab["a_original_snapshot"]["rows"]}
    b_rows = {row["entity_id"]: row for row in ab["b_event_adjusted_shadow"]["rows"]}
    assert a_rows["sw_nonferrous_copper"] == {
        "entity_scope": "sector",
        "entity_id": "sw_nonferrous_copper",
        "base_rank": 2,
        "base_value": 90.0,
    }
    assert b_rows["sw_nonferrous_copper"]["base_rank"] == 2
    assert b_rows["sw_nonferrous_copper"]["base_value"] == 90.0
    assert b_rows["sw_nonferrous_copper"]["adjustment"] > 0
    assert b_rows["sw_nonferrous_copper"]["research_adjusted_value"] > b_rows["sw_nonferrous_copper"]["base_value"]
    assert b_rows["sw_nonferrous_copper"]["research_rank_change"] == 1
    assert b_rows["sw_copper_processing"]["research_rank_change"] == -1
    _assert_no_formal_fields(ab)


def test_ab_rejects_snapshot_manifest_and_future_pit_mismatches():
    from theme_sector_radar.data.event_adjustment_ranking_shadow import (
        build_event_adjustment_ranking_ab_shadow,
    )

    case = _case()
    with pytest.raises(ValueError, match="snapshot SHA"):
        build_event_adjustment_ranking_ab_shadow(
            {**case["base_snapshot"], "snapshot_sha256": "0" * 64},
            _adjustment_from_case(case),
            case["adjustment_manifest"],
        )
    with pytest.raises(ValueError, match="manifest SHA"):
        build_event_adjustment_ranking_ab_shadow(
            case["base_snapshot"],
            _adjustment_from_case(case),
            {**case["adjustment_manifest"], "manifest_sha256": "0" * 64},
        )
    future_base = copy.deepcopy(case["base_snapshot"])
    future_base["effective_from"] = "2026-07-21"
    future_base["snapshot_sha256"] = _snapshot_sha(future_base)
    with pytest.raises(ValueError, match="effective_from"):
        build_event_adjustment_ranking_ab_shadow(
            future_base,
            _adjustment_from_case(case),
            case["adjustment_manifest"],
        )


def _snapshot_sha(snapshot):
    from theme_sector_radar.data.risk_event_schema import canonical_sha256

    return canonical_sha256({key: value for key, value in snapshot.items() if key != "snapshot_sha256"})


def test_metrics_are_preregistered_and_real_coverage_shortfall_blocks_effect_claim():
    from theme_sector_radar.data.event_adjustment_ranking_shadow import (
        build_event_ab_evaluation_contract,
        build_event_ab_metric_preregistration,
    )

    registration = build_event_ab_metric_preregistration()
    assert {(row["entity_scope"], row["top_n"]) for row in registration["registrations"]} == {
        ("sector", 3), ("sector", 5), ("sector", 7),
        ("individual", 1), ("individual", 3), ("individual", 5),
    }
    assert set(registration["registrations"][0]["metric_names"]) == {
        "forward_return", "rank_ic", "max_drawdown", "turnover", "transaction_cost", "event_coverage"
    }
    evaluation = build_event_ab_evaluation_contract(real_event_count=0, fixture_event_count=1)
    assert evaluation["status"] == "blocked_insufficient_real_event_coverage"
    assert evaluation["metric_results"] == []
    assert evaluation["effect_claim_allowed"] is False
    evaluation_with_real = build_event_ab_evaluation_contract(real_event_count=1)
    assert evaluation_with_real["status"] == "pre_registered_not_run"
    assert evaluation_with_real["effect_claim_allowed"] is False


def test_copper_fixture_is_research_only_and_safety_flags_are_false():
    case = _case()
    assert case["status"] == "fixture_contract_only"
    assert case["research_only"] is True
    assert case["evaluation_contract"]["fixture_event_count"] == 1
    assert case["evaluation_contract"]["real_event_count"] == 0
    assert case["ab_shadow"]["formal_ranking_allowed"] is False
    assert case["ab_shadow"]["promotion_allowed"] is False
    assert case["ab_shadow"]["live_trading_allowed"] is False
    _assert_no_formal_fields(case)
