from __future__ import annotations

import hashlib

import pytest


AS_OF = "2026-07-20"
OBSERVED_AT = "2026-07-20T15:00:00+08:00"


def _evidence(label: str = "market-fixture"):
    raw = label.encode("utf-8")
    return [{"document_id": label, "sha256": hashlib.sha256(raw).hexdigest(), "kind": "fixture"}]


def _market_observation(**overrides):
    observation = {
        "as_of_date": AS_OF,
        "observed_at": OBSERVED_AT,
        "data_quality": "complete",
        "scope": "individual",
        "entity_id": "000001",
        "sector_id": "bank",
        "return_pct": -0.10,
        "limit_down": True,
        "gap_pct": -0.08,
        "volume_ratio": 3.5,
        "volume_z": 3.2,
        "rolling_correlation": 0.10,
        "correlation_baseline": 0.80,
        "evidence_refs": _evidence(),
    }
    observation.update(overrides)
    return observation


def _build_event(**overrides):
    from theme_sector_radar.data.risk_events import build_risk_event

    values = {
        "event_type": "test_risk",
        "scope": "individual",
        "entity_id": "000001",
        "event_time": OBSERVED_AT,
        "published_at": OBSERVED_AT,
        "effective_from": AS_OF,
        "as_of_date": AS_OF,
        "severity": "high",
        "status": "observed",
        "source": {"source_id": "fixture", "authority_tier": "research_only"},
        "evidence_refs": _evidence(),
        "detector": {"detector_id": "fixture-detector", "detector_version": "v1", "mode": "deterministic"},
    }
    values.update(overrides)
    return build_risk_event(**values)


def _assert_no_forbidden_keys(value):
    forbidden = {"score", "rank", "confidence", "action", "trade", "order", "position", "price"}
    if isinstance(value, dict):
        assert not any(str(key).casefold() in forbidden or str(key).casefold().endswith("_score") for key in value)
        for child in value.values():
            _assert_no_forbidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_forbidden_keys(child)


def test_public_data_api_imports_and_schema_rejects_scores_actions_and_live_flags():
    from theme_sector_radar.data import adapt_policy_macro_fixture
    from theme_sector_radar.data.risk_events import validate_unified_risk_event

    assert callable(adapt_policy_macro_fixture)
    event = _build_event()
    assert validate_unified_risk_event(event)["event_id"] == event["event_id"]
    assert event["promotion_allowed"] is False
    assert event["live_trading_allowed"] is False
    with pytest.raises(ValueError, match="prohibited score/trade"):
        _build_event(structured_fields={"confidence": 0.9})
    with pytest.raises(ValueError, match="canonical fields"):
        validate_unified_risk_event({"event_id": "incomplete"})


def test_market_anomaly_detector_emits_four_canonical_types_and_blocks_missing_inputs():
    from theme_sector_radar.data.risk_events import detect_market_anomalies

    events = detect_market_anomalies(_market_observation())
    assert {event["event_type"] for event in events} == {
        "limit_down", "large_gap", "abnormal_volume", "sector_correlation_break"
    }
    assert all(event["status"] == "observed" for event in events)
    assert all(event["detector"]["detector_version"] == "market-anomaly-v1" for event in events)
    assert all(event["observed_at"] == OBSERVED_AT for event in events)
    assert all(event["promotion_allowed"] is False for event in events)

    blocked = detect_market_anomalies(
        {"as_of_date": AS_OF, "observed_at": OBSERVED_AT, "data_quality": "blocked", "entity_id": "000001"}
    )
    assert {event["status"] for event in blocked} == {"blocked"}
    assert blocked[0]["structured_fields"]["data_quality"] == "blocked"


def test_market_anomaly_normal_observation_has_no_risk_event_but_missing_is_not_no_event():
    from theme_sector_radar.data.risk_events import detect_market_anomalies

    events = detect_market_anomalies(
        _market_observation(
            limit_down=False,
            return_pct=0.01,
            gap_pct=0.01,
            volume_ratio=1.1,
            volume_z=0.1,
            rolling_correlation=0.8,
        )
    )
    assert events == []
    unknown = detect_market_anomalies(
        {"as_of_date": AS_OF, "observed_at": OBSERVED_AT, "data_quality": "unknown", "entity_id": "000001"}
    )
    assert unknown[0]["status"] == "unknown"
    assert unknown[0]["event_type"] == "market_data_quality"


def test_policy_macro_fixture_adapter_and_real_provider_registry_are_explicit():
    from theme_sector_radar.data.risk_events import (
        adapt_policy_macro_fixture,
        policy_macro_source_registry,
    )

    registry = policy_macro_source_registry()
    assert {row["source_id"] for row in registry["sources"]} >= {
        "mof_notices", "ndrc_notices", "policy_macro_offline_fixture"
    }
    fixture = adapt_policy_macro_fixture(
        [{
            "source_id": "policy_macro_offline_fixture",
            "as_of_date": AS_OF,
            "title": "Policy fixture",
            "event_type": "policy",
            "scope": "market",
            "entity_id": "market",
            "severity": "watch",
            "evidence_refs": _evidence("policy"),
        }]
    )
    assert fixture[0]["status"] == "observed"
    assert fixture[0]["source"]["authority_tier"] == "research_only"
    blocked = adapt_policy_macro_fixture([{"as_of_date": AS_OF, "title": ""}])
    assert blocked[0]["status"] == "blocked"
    assert "evidence_refs" in blocked[0]["structured_fields"]["missing_fields"]
    with pytest.raises(ValueError, match="no_event"):
        adapt_policy_macro_fixture([])


def test_official_announcement_normalizes_through_the_same_schema(tmp_path):
    from theme_sector_radar.data.official_announcements import archive_raw_announcement
    from theme_sector_radar.data.risk_events import normalize_risk_event

    manifest = archive_raw_announcement(
        tmp_path / "archive",
        source_id="issuer_official_announcements",
        source_url_or_path="fixture://issuer/1",
        published_at="2026-07-20",
        captured_at=OBSERVED_AT,
        raw_content=b"official announcement",
    )
    event = normalize_risk_event(
        "official_announcement",
        manifest,
        event_type="announcement",
        scope="individual",
        entity_id="000001",
        severity="watch",
        as_of_date=AS_OF,
        title="Official fixture",
    )
    assert event["schema_version"] == "canonical-risk-event-v1"
    assert event["published_time_precision"] == "date_only"
    assert event["source"]["authority_tier"] == "primary"
    assert event["evidence_refs"][0]["sha256"] == manifest["raw_sha256"]


def test_llm_shadow_is_disabled_and_carries_only_evidence():
    from theme_sector_radar.data.risk_events import extract_llm_shadow

    result = extract_llm_shadow(evidence_refs=_evidence())
    assert result["enabled"] is False
    assert result["status"] == "reserved_not_run"
    assert result["candidates"] == []
    _assert_no_forbidden_keys(result)
    with pytest.raises(RuntimeError, match="reserved and disabled"):
        extract_llm_shadow(enabled=True)


def test_ledger_supports_exact_duplicate_revision_and_conflict():
    from theme_sector_radar.data.risk_events import fuse_risk_events

    first = _build_event(event_id="risk-one")
    duplicate = _build_event(event_id="risk-duplicate")
    revision = _build_event(
        event_id="risk-revision",
        severity="critical",
        structured_fields={"return_pct": -0.2},
        revision_of="risk-one",
    )
    conflict = _build_event(
        event_id="risk-conflict",
        severity="watch",
        structured_fields={"return_pct": -0.01},
    )
    ledger = fuse_risk_events([first, duplicate, revision, conflict])
    assert ledger["duplicate_count"] == 1
    assert ledger["revision_count"] == 1
    assert ledger["conflict_count"] == 1
    assert ledger["status"] == "conflicts_present"
    assert {event["event_id"] for event in ledger["events"]} == {
        "risk-one", "risk-revision", "risk-conflict"
    }
    assert ledger["events"][-1]["status"] == "conflict"
    _assert_no_forbidden_keys(ledger)


def test_monitoring_is_three_level_paper_only_and_has_no_trade_fields():
    from theme_sector_radar.data.risk_events import (
        aggregate_risk_events,
        build_risk_monitor_report,
        fuse_risk_events,
    )

    events = [
        _build_event(event_id="individual-risk", scope="individual", entity_id="000001"),
        _build_event(event_id="sector-risk", scope="sector", entity_id="bank"),
        _build_event(event_id="market-risk", scope="market", entity_id="market"),
    ]
    ledger = fuse_risk_events(events)
    report = build_risk_monitor_report(ledger["events"], as_of_date=AS_OF)
    aggregation = aggregate_risk_events(ledger["events"])
    assert len(aggregation["individual"]) == 1
    assert len(aggregation["sector"]) == 1
    assert len(aggregation["market"]) == 1
    assert report["reminder_payload"]["delivery_status"] == "paper_shadow_only"
    assert all(alert["requires_human_review"] for alert in report["alerts"])
    assert report["promotion_allowed"] is False
    assert report["live_trading_allowed"] is False
    _assert_no_forbidden_keys(report)


def test_pit_date_only_is_retained_and_after_close_is_next_trading_date():
    from theme_sector_radar.data.official_announcements import infer_effective_from

    event = _build_event(
        event_id="date-only",
        event_time="2026-07-20",
        published_at="2026-07-20",
        effective_from=None,
    )
    assert event["published_time_precision"] == "date_only"
    assert event["event_time_precision"] == "date_only"
    assert event["effective_from"] is None
    assert infer_effective_from(
        "2026-07-20T15:30:00+08:00",
        trading_dates=["2026-07-20", "2026-07-21"],
    )["effective_from"] == "2026-07-21"
