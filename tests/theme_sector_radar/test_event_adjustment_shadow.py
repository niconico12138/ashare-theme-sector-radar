from __future__ import annotations

import hashlib

import pytest


AS_OF = "2026-07-20"
TIMESTAMP = "2026-07-20T10:00:00+08:00"


def _refs(label="adjustment-fixture"):
    return [{"evidence_id": label, "sha256": hashlib.sha256(label.encode("ascii")).hexdigest()}]


def _event(**overrides):
    from theme_sector_radar.data.risk_events import build_risk_event

    values = {
        "event_type": "announcement",
        "scope": "market",
        "entity_id": "market",
        "event_time": TIMESTAMP,
        "published_at": TIMESTAMP,
        "effective_from": AS_OF,
        "as_of_date": AS_OF,
        "observed_at": TIMESTAMP,
        "severity": "critical",
        "status": "observed",
        "source": {"source_id": "official-fixture", "authority_tier": "primary"},
        "evidence_refs": _refs(),
        "provider": {"provider_id": "official-fixture", "provider_version": "v1"},
    }
    values.update(overrides)
    return build_risk_event(**values)


def _enhancement(event=None, *, post=None, reflection_status="unreflected", novelty="novel"):
    from theme_sector_radar.data.event_enhancement import build_event_enhancement

    market = {
        "as_of_snapshot": {
            "as_of_date": AS_OF,
            "status": "observed",
            "pre_event_reaction": {"reflection_status": reflection_status},
        }
    }
    if post is not None:
        market["post_event_backtest"] = post
    return build_event_enhancement(
        event or _event(),
        fact_view={
            "impact_direction": "mixed",
            "value_chain_stage": "mixed",
            "transmission_channel": "fixture",
            "impact_scope": ["sector", "individual"],
            "mapping_basis": "deterministic_fixture",
        },
        lifecycle_view={
            "duration_type": "ongoing",
            "effective_until": "2026-08-19",
            "decay_metadata": {"method": "exponential", "half_life_days": 30},
            "novelty": {"status": novelty},
        },
        evidence_view={"mapping_quality": "exact"},
        market_feedback=market,
    )


def _mapping(enhancement, rules=None):
    from theme_sector_radar.data.event_enhancement import build_event_exposure_mapping

    return build_event_exposure_mapping(
        enhancement,
        rules or [
            {
                "entity_scope": "sector",
                "entity_id": "sector-a",
                "exposure_type": "direct",
                "value_chain_stage": "upstream",
                "impact_direction": "positive",
                "mapping_quality": "exact",
                "valid_from": AS_OF,
            }
        ],
    )


def _build(enhancement, mapping, config=None):
    from theme_sector_radar.data.event_adjustment_shadow import build_event_adjustment_shadow

    kwargs = {"config": config} if config is not None else {}
    return build_event_adjustment_shadow(
        [{"enhancement": enhancement, "exposure_mapping": mapping}], **kwargs
    )


def _assert_no_protected(value):
    forbidden = {
        "quant_score", "final_score", "v2_score", "selection_score", "event_score",
        "confidence", "rank", "action", "trade", "order", "position", "target_price",
    }
    if isinstance(value, dict):
        assert not any(str(key).casefold() in forbidden or str(key).casefold().endswith("_score") for key in value)
        for child in value.values():
            _assert_no_protected(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_protected(child)


def test_default_caps_and_sector_stock_outputs_are_separate():
    from theme_sector_radar.data.event_adjustment_shadow import EventAdjustmentShadowConfig

    enhancement = _enhancement()
    mapping = _mapping(
        enhancement,
        [
            {"entity_scope": "sector", "entity_id": "sector-a", "exposure_type": "direct", "value_chain_stage": "upstream", "impact_direction": "positive", "mapping_quality": "exact", "valid_from": AS_OF},
            {"entity_scope": "individual", "entity_id": "000001", "exposure_type": "direct", "value_chain_stage": "upstream", "impact_direction": "positive", "mapping_quality": "exact", "valid_from": AS_OF},
        ],
    )
    result = _build(enhancement, mapping)
    assert result["config"] == {
        "sector_min_adjustment": -12.0,
        "sector_max_adjustment": 8.0,
        "stock_min_adjustment": -10.0,
        "stock_max_adjustment": 6.0,
        "default_half_life_days": 30,
    }
    assert result["sector_event_adjustment_shadow"][0]["adjustment_value"] == 8.0
    assert result["stock_event_adjustment_shadow"][0]["adjustment_value"] == 6.0
    limited = _build(
        enhancement,
        mapping,
        EventAdjustmentShadowConfig(
            sector_min_adjustment=-2,
            sector_max_adjustment=2,
            stock_min_adjustment=-1,
            stock_max_adjustment=1,
        ),
    )
    assert limited["sector_event_adjustment_shadow"][0]["adjustment_value"] == 2
    assert limited["stock_event_adjustment_shadow"][0]["adjustment_value"] == 1


def test_decomposition_is_deterministic_and_explainable():
    enhancement = _enhancement(event=_event(severity="high"))
    mapping = _mapping(enhancement)
    first = _build(enhancement, mapping)
    second = _build(enhancement, mapping)
    assert first == second
    decomposition = first["sector_event_adjustment_shadow"][0]["decomposition"]
    assert decomposition["direction_sign"] == 1.0
    assert decomposition["impact_magnitude_band"] == "high"
    assert decomposition["exposure_band"] == "high"
    assert decomposition["persistence_type"] == "ongoing"
    assert decomposition["novelty_status"] == "novel"
    assert decomposition["market_reflection_status"] == "unreflected"
    assert decomposition["time_decay_factor"] == 1.0


def test_post_event_backtest_is_excluded_and_cannot_change_lineage_or_adjustment():
    base = _enhancement()
    post = _enhancement(
        post={
            "status": "observed",
            "evaluation_as_of_date": "2026-07-27",
            "post_event_reaction": {"return_pct": 0.25},
            "breadth_propagation": {"breadth_count": 42},
        }
    )
    base_result = _build(base, _mapping(base))
    post_result = _build(post, _mapping(post))
    assert base_result["sector_event_adjustment_shadow"] == post_result["sector_event_adjustment_shadow"]
    assert base_result["adjustment_lineage"] == post_result["adjustment_lineage"]
    excluded = post_result["excluded_post_event_backtests"][0]
    assert excluded["excluded"] is True
    assert excluded["contained_numeric_metadata"] is True
    assert post_result["adjustment_lineage"][0]["post_event_backtest_included"] is False


@pytest.mark.parametrize(
    ("mutator", "expected_reason"),
    [
        (lambda item: item.update(event_status="blocked"), "event_status_blocked"),
        (lambda item: item["evidence_quality_view"].update(conflict_status="conflict"), "event_conflict_or_unknown"),
        (lambda item: item["evidence_quality_view"].update(authority_tier="unknown"), "evidence_quality_unknown"),
    ],
)
def test_blocked_conflict_or_unknown_quality_is_zero(mutator, expected_reason):
    enhancement = _enhancement()
    mutator(enhancement)
    result = _build(enhancement, _mapping(enhancement))
    record = result["sector_event_adjustment_shadow"][0]
    assert record["adjustment_value"] == 0
    assert expected_reason in record["zero_adjustment_reasons"]
    assert record["manual_review_required"] is True


def test_unknown_mapping_and_reflection_do_not_add_adjustment():
    enhancement = _enhancement(reflection_status="unknown")
    mapping = _mapping(
        enhancement,
        [{"entity_scope": "sector", "entity_id": "sector-a", "exposure_type": "indirect", "value_chain_stage": "midstream", "impact_direction": "unknown", "mapping_quality": "unknown", "valid_from": AS_OF}],
    )
    result = _build(enhancement, mapping)
    record = result["sector_event_adjustment_shadow"][0]
    assert record["adjustment_value"] == 0
    assert "impact_direction_not_directional" in record["zero_adjustment_reasons"]
    assert "mapping_quality_unknown_or_blocked" in record["zero_adjustment_reasons"]
    assert "market_reflection_unknown" in record["zero_adjustment_reasons"]


def test_logical_event_and_direct_exposure_are_deduplicated():
    from theme_sector_radar.data.event_adjustment_shadow import build_event_adjustment_shadow

    enhancement = _enhancement()
    mapping = _mapping(
        enhancement,
        [
            {"entity_scope": "individual", "entity_id": "000001", "exposure_type": "indirect", "value_chain_stage": "downstream", "impact_direction": "negative", "mapping_quality": "partial", "valid_from": AS_OF},
            {"entity_scope": "individual", "entity_id": "000001", "exposure_type": "direct", "value_chain_stage": "downstream", "impact_direction": "negative", "mapping_quality": "exact", "valid_from": AS_OF},
        ],
    )
    result = build_event_adjustment_shadow(
        [
            {"enhancement": enhancement, "exposure_mapping": mapping},
            {"enhancement": enhancement, "exposure_mapping": mapping},
        ]
    )
    assert len(result["event_deduplication"]) == 1
    assert len(result["exposure_deduplication"]) == 1
    assert len(result["stock_event_adjustment_shadow"]) == 1
    assert result["stock_event_adjustment_shadow"][0]["decomposition"]["exposure_band"] == "high"


def test_direct_company_event_beats_sector_transmission_for_shared_evidence():
    from theme_sector_radar.data.event_adjustment_shadow import build_event_adjustment_shadow

    direct_enhancement = _enhancement(
        event=_event(scope="individual", entity_id="000001")
    )
    direct_mapping = _mapping(
        direct_enhancement,
        [{"entity_scope": "individual", "entity_id": "000001", "exposure_type": "direct", "value_chain_stage": "downstream", "impact_direction": "negative", "mapping_quality": "exact", "valid_from": AS_OF}],
    )
    sector_enhancement = _enhancement(
        event=_event(scope="sector", entity_id="sector-a")
    )
    sector_mapping = _mapping(
        sector_enhancement,
        [{"entity_scope": "individual", "entity_id": "000001", "exposure_type": "indirect", "value_chain_stage": "downstream", "impact_direction": "negative", "mapping_quality": "partial", "valid_from": AS_OF}],
    )
    result = build_event_adjustment_shadow(
        [
            {"enhancement": direct_enhancement, "exposure_mapping": direct_mapping},
            {"enhancement": sector_enhancement, "exposure_mapping": sector_mapping},
        ]
    )
    assert len(result["stock_event_adjustment_shadow"]) == 1
    assert result["stock_event_adjustment_shadow"][0]["source_event_scope"] == "individual"
    assert result["cross_event_deduplication"][0]["reason"] == "direct_company_event_preferred_over_sector_transmission"


def test_copper_fixture_has_signed_unknown_and_decayed_adjustments():
    from theme_sector_radar.data.event_adjustment_shadow import build_copper_adjustment_research_case

    case = build_copper_adjustment_research_case()
    fresh = {row["entity_id"]: row for row in case["fresh"]["sector_event_adjustment_shadow"]}
    decayed = {row["entity_id"]: row for row in case["decayed"]["sector_event_adjustment_shadow"]}
    assert fresh["sw_nonferrous_copper"]["adjustment_value"] > 0
    assert fresh["sw_electrical_cable"]["adjustment_value"] < 0
    assert fresh["sw_copper_processing"]["adjustment_value"] == 0
    assert fresh["sw_integrated_copper_chain"]["adjustment_value"] == 0
    assert abs(decayed["sw_nonferrous_copper"]["adjustment_value"]) < abs(fresh["sw_nonferrous_copper"]["adjustment_value"])
    assert abs(decayed["sw_electrical_cable"]["adjustment_value"]) < abs(fresh["sw_electrical_cable"]["adjustment_value"])
    assert case["research_only"] is True
    _assert_no_protected(case)


def test_output_rejects_protected_fields_and_keeps_all_safety_gates_false():
    from theme_sector_radar.data.event_adjustment_shadow import validate_event_adjustment_shadow

    enhancement = _enhancement()
    result = _build(enhancement, _mapping(enhancement))
    assert result["research_only"] is True
    assert result["formal_ranking_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["live_trading_allowed"] is False
    _assert_no_protected(result)
    with pytest.raises(ValueError, match="protected"):
        validate_event_adjustment_shadow({**result, "selection_score": 1.0})
