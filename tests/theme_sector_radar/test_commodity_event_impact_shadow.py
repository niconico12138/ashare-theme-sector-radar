from __future__ import annotations

import hashlib

import pytest


AS_OF = "2026-07-20"
OBSERVED_AT = "2026-07-20T16:00:00+08:00"


def _evidence(label: str):
    return [{"evidence_id": label, "sha256": hashlib.sha256(label.encode("ascii")).hexdigest()}]


def _fixture(**overrides):
    from theme_sector_radar.data.commodity_prices import normalize_commodity_fixture

    payload = {
        "as_of_date": AS_OF,
        "price_date": AS_OF,
        "observed_at": OBSERVED_AT,
        "published_at": AS_OF,
        "effective_from": AS_OF,
        "commodity_id": "copper_cathode",
        "commodity_name": "Copper cathode",
        "unit": "CNY/metric_ton",
        "currency": "CNY",
        "market_type": "spot",
        "price": 100.0,
        "evidence_refs": _evidence("copper-current"),
    }
    payload.update(overrides)
    return normalize_commodity_fixture(payload, stale_after_days=30)


def _assert_flags_false(value):
    if isinstance(value, dict):
        for key in ("eligible_for_oos_claim", "promotion_allowed", "live_trading_allowed"):
            if key in value:
                assert value[key] is False
        for child in value.values():
            _assert_flags_false(child)
    elif isinstance(value, list):
        for child in value:
            _assert_flags_false(child)


def test_commodity_registry_and_real_sources_are_explicitly_blocked():
    from theme_sector_radar.data.commodity_prices import (
        BlockedCommodityPriceProvider,
        OfflineCommodityPriceProvider,
        build_commodity_source_health,
        commodity_price_source_registry,
    )

    registry = commodity_price_source_registry()
    assert {row["source_id"] for row in registry["sources"]} >= {
        "ndrc_price_monitoring", "shfe_official_market_data", "commodity_price_research_fixture"
    }
    result = BlockedCommodityPriceProvider(
        "ndrc_price_monitoring", "terms_and_format_unverified"
    ).fetch(as_of_date=AS_OF)
    assert result["status"] == "blocked"
    assert result["event_state"] == "unknown_not_no_event"
    empty_fixture = OfflineCommodityPriceProvider([]).fetch(as_of_date=AS_OF)
    assert empty_fixture["status"] == "unknown"
    assert empty_fixture["event_state"] == "unknown_not_no_event"
    health = build_commodity_source_health([result, empty_fixture])
    assert health["status"] == "blocked_sources_present"
    with pytest.raises(ValueError, match="no_event"):
        build_commodity_source_health(
            [{"provider_id": "invalid", "status": "failed", "event_state": "no_event"}]
        )


def test_commodity_raw_evidence_is_immutable_and_sha_bound(tmp_path):
    from theme_sector_radar.data.commodity_prices import archive_commodity_price_evidence

    raw = b"date,commodity,price,unit\n2026-07-20,copper,100,CNY/t\n"
    first = archive_commodity_price_evidence(
        tmp_path,
        source_id="commodity_price_research_fixture",
        source_url_or_path="fixture://copper.csv",
        retrieved_at=OBSERVED_AT,
        raw_content=raw,
        provider_version="fixture-v1",
    )
    second = archive_commodity_price_evidence(
        tmp_path,
        source_id="commodity_price_research_fixture",
        source_url_or_path="fixture://copper.csv",
        retrieved_at=OBSERVED_AT,
        raw_content=raw,
        provider_version="fixture-v1",
    )
    assert first["evidence_id"] == second["evidence_id"]
    assert first["raw_sha256"] == hashlib.sha256(raw).hexdigest()


def test_commodity_quality_missing_stale_and_abnormal_are_fail_closed():
    missing = _fixture(unit=None)
    assert missing["status"] == "unknown"
    assert "missing_unit" in missing["quality_issues"]
    missing_currency = _fixture(currency=None)
    assert missing_currency["status"] == "unknown"
    assert "missing_currency" in missing_currency["quality_issues"]
    stale = _fixture(price_date="2026-06-01")
    assert stale["status"] == "unknown"
    assert "stale_data" in stale["quality_issues"]
    abnormal = _fixture(price=-1)
    assert abnormal["status"] == "blocked"
    assert abnormal["price"] is None
    with pytest.raises(ValueError, match="ISO date"):
        _fixture(price_date="not-a-date")


def test_commodity_ledger_tracks_duplicate_revision_and_conflict():
    from theme_sector_radar.data.commodity_prices import build_commodity_observation_ledger

    first = _fixture(observation_id="commodity-one")
    duplicate = {**first, "observation_id": "commodity-duplicate"}
    revision = _fixture(
        observation_id="commodity-revision",
        price=101.0,
        revision_of="commodity-one",
        evidence_refs=_evidence("copper-revision"),
    )
    conflict = _fixture(
        observation_id="commodity-conflict",
        price=102.0,
        evidence_refs=_evidence("copper-conflict"),
    )
    ledger = build_commodity_observation_ledger([first, duplicate, revision, conflict])
    assert ledger["duplicate_count"] == 1
    assert ledger["revision_count"] == 1
    assert ledger["conflict_count"] == 1
    assert ledger["observations"][-1]["status"] == "conflict"


def test_copper_increase_case_maps_opposite_value_chain_directions_without_scores():
    from theme_sector_radar.data.event_impact_shadow import build_copper_increase_research_case

    case = build_copper_increase_research_case()
    assert case["research_only"] is True
    assert case["risk_event"]["event_type"] == "commodity_price_increase"
    impacts = case["event_impact_shadow"]["impacts"]
    assert {(row["industry_stage"], row["impact_direction"]) for row in impacts} == {
        ("upstream", "positive"), ("downstream", "negative")
    }
    serialized_keys = str(case.keys()) + str(case["event_impact_shadow"].keys())
    assert "quant_score" not in serialized_keys
    assert "final_score" not in serialized_keys
    _assert_flags_false(case)


def test_event_impact_unmapped_is_unknown_and_protected_fields_are_rejected():
    from theme_sector_radar.data.event_impact_shadow import (
        build_copper_increase_research_case,
        map_event_impact_shadow,
        validate_event_impact_shadow,
    )

    event = build_copper_increase_research_case()["risk_event"]
    unmapped = map_event_impact_shadow(
        event, [], as_of_date=AS_OF, valid_from=AS_OF
    )
    assert unmapped["status"] == "unknown"
    assert unmapped["impacts"] == []
    with pytest.raises(ValueError, match="protected field"):
        validate_event_impact_shadow({**unmapped, "quant_score": 1.0})
