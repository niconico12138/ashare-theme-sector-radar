from __future__ import annotations

import hashlib

import pytest


AS_OF = "2026-07-20"
TIMESTAMP = "2026-07-20T16:00:00+08:00"


def _refs(label="enhancement-fixture"):
    return [{"evidence_id": label, "sha256": hashlib.sha256(label.encode("ascii")).hexdigest()}]


def _event(**overrides):
    from theme_sector_radar.data.risk_events import build_risk_event

    values = {
        "event_type": "policy_macro",
        "scope": "market",
        "entity_id": "market",
        "event_time": AS_OF,
        "published_at": AS_OF,
        "effective_from": None,
        "as_of_date": AS_OF,
        "observed_at": TIMESTAMP,
        "severity": "watch",
        "status": "observed",
        "source": {"source_id": "fixture", "authority_tier": "research_only"},
        "evidence_refs": _refs(),
        "provider": {"provider_id": "fixture", "provider_version": "v1"},
    }
    values.update(overrides)
    return build_risk_event(**values)


def _assert_safe(value):
    forbidden = {
        "event_score", "quant_score", "final_score", "v2_score", "selection_score",
        "confidence", "rank", "action", "trade", "order", "position", "price",
    }
    if isinstance(value, dict):
        assert not any(str(key).casefold() in forbidden or str(key).casefold().endswith("_score") for key in value)
        for child in value.values():
            _assert_safe(child)
    elif isinstance(value, list):
        for child in value:
            _assert_safe(child)


def test_default_enhancement_has_four_views_and_unknown_is_explicit():
    from theme_sector_radar.data.event_enhancement import (
        build_event_enhancement,
        validate_event_enhancement,
    )

    enhancement = build_event_enhancement(_event())
    assert validate_event_enhancement(enhancement)["schema_version"] == "event-enhancement-v1"
    assert enhancement["fact_view"]["impact_direction"] == "unknown"
    assert enhancement["fact_view"]["value_chain_stage"] == "unknown"
    assert enhancement["lifecycle_view"]["duration_type"] == "unknown"
    assert enhancement["lifecycle_view"]["effective_until"] is None
    assert enhancement["evidence_quality_view"]["authority_tier"] == "research_only"
    assert enhancement["evidence_quality_view"]["evidence_completeness"] == "complete"
    assert enhancement["evidence_quality_view"]["timestamp_quality"] == "date_only"
    assert enhancement["market_feedback_view"]["as_of_snapshot"]["as_of_date"] == AS_OF
    assert enhancement["market_feedback_view"]["post_event_backtest"]["status"] == "reserved_not_run"
    assert enhancement["llm_shadow"]["enabled"] is False
    assert enhancement["llm_shadow"]["status"] == "reserved_not_run"
    _assert_safe(enhancement)


def test_enhancement_accepts_all_fact_event_families_without_scoring():
    from theme_sector_radar.data.event_enhancement import build_event_enhancement

    for event_type in ("announcement", "policy_macro", "commodity_price_increase", "limit_down"):
        enhancement = build_event_enhancement(
            _event(event_type=event_type),
            fact_view={
                "impact_direction": "unknown",
                "value_chain_stage": "unknown",
                "transmission_channel": "unknown",
                "impact_scope": ["unknown"],
            },
        )
        assert enhancement["event_type"] == event_type
        _assert_safe(enhancement)


def test_enhancement_pit_revision_duplicate_and_expiry_metadata():
    from theme_sector_radar.data.event_enhancement import build_event_enhancement

    revised = _event(revision_of="risk-original")
    enhancement = build_event_enhancement(
        revised,
        lifecycle_view={
            "duration_type": "temporary",
            "effective_until": "2026-08-19",
            "novelty": {
                "status": "revised",
                "revision_of": "risk-original",
                "duplicate_of": None,
            },
            "decay_metadata": {"method": "metadata_only", "half_life_days": 15},
        },
    )
    assert enhancement["lifecycle_view"]["effective_until"] == "2026-08-19"
    assert enhancement["lifecycle_view"]["novelty"]["status"] == "revised"
    assert enhancement["lifecycle_view"]["novelty"]["revision_of"] == "risk-original"
    assert enhancement["lifecycle_view"]["decay_metadata"]["half_life_days"] == 15
    duplicate = build_event_enhancement(
        _event(), lifecycle_view={"novelty": {"status": "duplicate", "duplicate_of": "risk-original"}}
    )
    assert duplicate["lifecycle_view"]["novelty"]["duplicate_of"] == "risk-original"


def test_enhancement_evidence_binding_unknown_blocked_and_pit_rejection():
    from theme_sector_radar.data.event_enhancement import build_event_enhancement
    from theme_sector_radar.data.risk_events import build_risk_event

    with pytest.raises(ValueError, match="bound to the validated event"):
        build_event_enhancement(_event(), evidence_refs=_refs("unbound"))
    blocked = build_risk_event(
        event_type="policy_provider_status",
        scope="market",
        entity_id="market",
        event_time=None,
        published_at=None,
        effective_from=None,
        as_of_date=AS_OF,
        severity="unknown",
        status="blocked",
        source={"source_id": "blocked", "authority_tier": "primary"},
        evidence_refs=[],
        provider={"provider_id": "blocked", "provider_version": "v1"},
    )
    blocked_view = build_event_enhancement(blocked)
    assert blocked_view["evidence_quality_view"]["evidence_completeness"] == "incomplete"
    assert blocked_view["evidence_quality_view"]["manual_review_required"] is True
    with pytest.raises(ValueError, match="as_of_snapshot"):
        build_event_enhancement(
            _event(),
            market_feedback={"as_of_snapshot": {"as_of_date": "2026-07-19"}},
        )
    with pytest.raises(ValueError, match="after event day"):
        build_event_enhancement(
            _event(),
            market_feedback={"post_event_backtest": {"evaluation_as_of_date": AS_OF}},
        )


def test_market_feedback_keeps_as_of_and_post_event_backtest_separate():
    from theme_sector_radar.data.event_enhancement import build_event_enhancement

    enhancement = build_event_enhancement(
        _event(),
        market_feedback={
            "as_of_snapshot": {
                "as_of_date": AS_OF,
                "status": "observed",
                "pre_event_reaction": {"window": "prior_5d", "status": "unknown"},
            },
            "post_event_backtest": {
                "status": "observed",
                "evaluation_as_of_date": "2026-07-27",
                "post_event_reaction": {"window": "next_5d", "status": "observed"},
                "breadth_propagation": {"status": "unknown"},
            },
        },
    )
    view = enhancement["market_feedback_view"]
    assert view["as_of_snapshot"]["as_of_date"] == AS_OF
    assert view["post_event_backtest"]["evaluation_as_of_date"] == "2026-07-27"
    assert view["post_event_backtest"]["is_backtest"] is True
    assert "as_of_date" not in view["post_event_backtest"]


def test_llm_shadow_cannot_enable_or_emit_candidates():
    from theme_sector_radar.data.event_enhancement import build_event_enhancement

    with pytest.raises(ValueError, match="disabled"):
        build_event_enhancement(_event(), llm_shadow={"enabled": True, "status": "running"})
    with pytest.raises(ValueError, match="candidates"):
        build_event_enhancement(
            _event(),
            llm_shadow={"enabled": False, "status": "reserved_not_run", "candidates": [{"event_type": "x"}]},
        )


def test_exposure_mapping_contract_supports_three_directions_and_unknown_rows():
    from theme_sector_radar.data.event_enhancement import (
        build_event_enhancement,
        build_event_exposure_mapping,
    )

    enhancement = build_event_enhancement(_event())
    mapping = build_event_exposure_mapping(
        enhancement,
        [
            {"entity_scope": "sector", "entity_id": "upstream", "exposure_type": "direct", "value_chain_stage": "upstream", "impact_direction": "positive", "mapping_quality": "exact"},
            {"entity_scope": "sector", "entity_id": "downstream", "exposure_type": "indirect", "value_chain_stage": "downstream", "impact_direction": "negative", "mapping_quality": "partial"},
            {"entity_scope": "individual", "entity_id": "mixed-stock", "exposure_type": "value_chain", "value_chain_stage": "mixed", "impact_direction": "mixed", "mapping_quality": "unknown"},
            {"entity_scope": "sector", "entity_id": "", "exposure_type": "unknown", "value_chain_stage": "unknown", "impact_direction": "unknown"},
        ],
    )
    assert mapping["status"] == "partial_unknown"
    assert {(row["value_chain_stage"], row["impact_direction"]) for row in mapping["exposures"]} == {
        ("upstream", "positive"), ("downstream", "negative"), ("mixed", "mixed")
    }
    assert mapping["unknown_mappings"][0]["status"] == "unknown"
    _assert_safe(mapping)


def test_copper_enhancement_fixture_is_research_only_and_has_three_mapping_views():
    from theme_sector_radar.data.event_enhancement import build_copper_enhancement_research_case

    case = build_copper_enhancement_research_case()
    assert case["research_only"] is True
    impacts = case["event_exposure_mapping"]["exposures"]
    assert {(row["value_chain_stage"], row["impact_direction"]) for row in impacts} == {
        ("upstream", "positive"), ("midstream", "unknown"),
        ("downstream", "negative"), ("mixed", "mixed")
    }
    assert case["event_enhancement"]["fact_view"]["mapping_basis"] == "research_fixture_only"
    _assert_safe(case)


def test_enhancement_rejects_illegal_protected_fields():
    from theme_sector_radar.data.event_enhancement import build_event_enhancement

    with pytest.raises(ValueError, match="protected"):
        build_event_enhancement(_event(), fact_view={"impact_direction": "unknown", "final_score": 1.0})
