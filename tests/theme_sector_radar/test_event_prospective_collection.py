from __future__ import annotations

import copy
import json

import pytest


COLLECTED_AT = "2026-07-20T17:00:00+08:00"
AS_OF = "2026-07-20"


def _fixture_bundle():
    from theme_sector_radar.data.event_adjustment_ranking_shadow import (
        build_copper_ranking_ab_research_case,
    )
    from theme_sector_radar.data.event_adjustment_shadow import build_copper_adjustment_research_case
    from theme_sector_radar.data.event_impact_shadow import build_copper_increase_research_case
    from theme_sector_radar.data.event_enhancement import build_copper_enhancement_research_case

    event = build_copper_increase_research_case()["risk_event"]
    enhancement_case = build_copper_enhancement_research_case()
    adjustment = build_copper_adjustment_research_case()["fresh"]
    ranking = build_copper_ranking_ab_research_case()
    return {
        "events": [event],
        "enhancements": [enhancement_case["event_enhancement"]],
        "exposure_mappings": [enhancement_case["event_exposure_mapping"]],
        "adjustment": adjustment,
        "source_health": [{
            "source_id": "commodity_price_research_fixture",
            "status": "fixture",
            "event_state": "observed",
            "authority_tier": "research_only",
        }],
        "base_snapshots": {"sector": ranking["base_snapshot"]},
    }


def _archive(tmp_path, *, origin="fixture", bundle=None, collected_at=COLLECTED_AT):
    from theme_sector_radar.data.event_prospective_collection import archive_prospective_event_day

    bundle = bundle or _fixture_bundle()
    return archive_prospective_event_day(
        tmp_path / "real",
        tmp_path / "research_only",
        as_of_date=AS_OF,
        collected_at=collected_at,
        data_origin=origin,
        **bundle,
    )


def test_fixture_daily_archive_is_immutable_layered_and_a_b_ready_for_review(tmp_path):
    from theme_sector_radar.data.event_prospective_collection import load_prospective_event_day

    first = _archive(tmp_path)
    second = _archive(tmp_path)
    assert first["manifest_file_sha256"] == second["manifest_file_sha256"]
    assert first["data_origin"] == "fixture"
    assert first["review_status"] == "fixture_review_only"
    assert set(first["layer_manifests"]) == {
        "canonical_events", "enhancements", "exposure_mappings", "adjustment", "source_health", "readiness"
    }
    assert first["runner_manifests"]["sector"]["manifest_sha256"]
    assert first["runner_manifests"]["individual"]["manifest_sha256"]
    runner_payload = json.loads(
        (tmp_path / "research_only" / AS_OF / "runner_manifests" / "sector_event_adjustment_manifest.json").read_text(encoding="utf-8")
    )
    assert runner_payload["review_status"] == "pending"
    assert runner_payload["readiness_status"] == "fixture_review_only"
    assert runner_payload["approved_for_frozen_oos_ab"] is False
    assert first["ab_shadow_daily_snapshot"]["file_sha256"]
    loaded = load_prospective_event_day(first["manifest_path"])
    assert loaded["manifest_sha256"] == first["manifest_sha256"]
    assert (tmp_path / "research_only" / AS_OF / "collection_manifest.json").exists()
    assert not (tmp_path / "real" / AS_OF / "collection_manifest.json").exists()
    with pytest.raises(ValueError, match="immutable prospective artifact changed"):
        _archive(tmp_path, collected_at="2026-07-20T18:00:00+08:00")


def test_fixture_and_real_roots_are_separate_and_fixture_cannot_enter_real_root(tmp_path):
    from theme_sector_radar.data.event_prospective_collection import archive_prospective_event_day

    bundle = _fixture_bundle()
    with pytest.raises(ValueError, match="research-only event"):
        archive_prospective_event_day(
            tmp_path / "real",
            tmp_path / "research_only",
            as_of_date=AS_OF,
            collected_at=COLLECTED_AT,
            data_origin="real",
            **bundle,
        )
    with pytest.raises(ValueError, match="roots must be separate"):
        archive_prospective_event_day(
            tmp_path / "same",
            tmp_path / "same",
            as_of_date=AS_OF,
            collected_at=COLLECTED_AT,
            data_origin="fixture",
            **bundle,
        )


def test_blocked_real_provider_archives_unknown_health_and_blocks_readiness(tmp_path):
    from theme_sector_radar.data.event_adjustment_shadow import build_event_adjustment_shadow

    result = _archive(
        tmp_path,
        origin="real",
        bundle={
            "events": [],
            "enhancements": [],
            "exposure_mappings": [],
            "adjustment": build_event_adjustment_shadow([]),
            "source_health": [{
                "source_id": "csrc_notices",
                "status": "blocked",
                "event_state": "unknown_not_no_event",
                "reason": "terms_not_verified",
            }],
            "base_snapshots": {},
        },
    )
    assert result["review_status"] == "blocked_insufficient_real_event_coverage"
    assert (tmp_path / "real" / AS_OF / "collection_manifest.json").exists()
    assert result["readiness"]["relative_path"].endswith("readiness/coverage_readiness.json")
    assert result["runner_manifests"]["sector"]["manifest_sha256"]
    assert result["ab_shadow_daily_snapshot"]["file_sha256"]


def test_duplicate_revision_and_future_effective_gates_are_explicit(tmp_path):
    from theme_sector_radar.data.event_adjustment_shadow import build_event_adjustment_shadow
    from theme_sector_radar.data.risk_event_schema import build_risk_event

    refs = [{"evidence_id": "real-doc", "sha256": "1" * 64}]
    common = {
        "event_type": "announcement",
        "scope": "market",
        "entity_id": "market",
        "event_time": AS_OF,
        "published_at": AS_OF,
        "effective_from": None,
        "as_of_date": AS_OF,
        "severity": "watch",
        "status": "observed",
        "source": {"source_id": "csrc_notices", "authority_tier": "primary"},
        "evidence_refs": refs,
        "provider": {"provider_id": "csrc_notices", "provider_version": "v1"},
    }
    first = build_risk_event(**common, event_id="event-one")
    duplicate = build_risk_event(**common, event_id="event-two")
    revision = build_risk_event(**common, event_id="event-revision", revision_of="event-one")
    source_health = [{"source_id": "csrc_notices", "status": "ok", "event_state": "observed"}]
    bundle = {
        "events": [first, duplicate], "enhancements": [], "exposure_mappings": [],
        "adjustment": build_event_adjustment_shadow([]), "source_health": source_health, "base_snapshots": {},
    }
    duplicate_result = _archive(tmp_path / "duplicates", origin="real", bundle=bundle)
    duplicate_readiness = json.loads(
        (tmp_path / "duplicates" / "real" / AS_OF / "readiness" / "coverage_readiness.json").read_text(encoding="utf-8")
    )
    assert next(g for g in duplicate_readiness["gates"] if g["gate"] == "duplicate_event_gate")["status"] == "blocked"
    bundle["events"] = [first, revision]
    revision_result = _archive(tmp_path / "revision", origin="real", bundle=bundle)
    revision_readiness = json.loads(
        (tmp_path / "revision" / "real" / AS_OF / "readiness" / "coverage_readiness.json").read_text(encoding="utf-8")
    )
    assert revision_result["review_status"] == "ready_for_manual_shadow_review"
    assert next(g for g in revision_readiness["gates"] if g["gate"] == "duplicate_event_gate")["status"] == "pass"
    future_values = {**common, "effective_from": "2026-07-21"}
    future = build_risk_event(**future_values, event_id="event-future")
    bundle["events"] = [future]
    future_result = _archive(tmp_path / "future", origin="real", bundle=bundle)
    assert future_result["review_status"] == "blocked_insufficient_real_event_coverage"


def test_commodity_quality_and_unknown_mapping_gates_are_retained(tmp_path):
    bundle = _fixture_bundle()
    unknown_mapping = copy.deepcopy(bundle["exposure_mappings"][0])
    unknown_mapping["status"] = "unknown"
    unknown_mapping["unknown_mappings"] = [{"mapping_index": 0, "status": "unknown"}]
    bundle["exposure_mappings"] = [unknown_mapping]
    result = _archive(tmp_path / "unknown", bundle=bundle)
    readiness_path = tmp_path / "unknown" / "research_only" / AS_OF / "readiness" / "coverage_readiness.json"
    assert readiness_path.exists()
    assert result["review_status"] == "fixture_review_only"


def test_load_rejects_tampered_layer_sha(tmp_path):
    from theme_sector_radar.data.event_prospective_collection import load_prospective_event_day

    result = _archive(tmp_path)
    path = tmp_path / "research_only" / AS_OF / "layers" / "canonical_events.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"] = []
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="layer SHA mismatch"):
        load_prospective_event_day(result["manifest_path"])


def test_source_health_rejects_no_event_shortcut(tmp_path):
    from theme_sector_radar.data.event_prospective_collection import archive_prospective_event_day
    from theme_sector_radar.data.event_adjustment_shadow import build_event_adjustment_shadow

    with pytest.raises(ValueError, match="no_event"):
        archive_prospective_event_day(
            tmp_path / "real", tmp_path / "research",
            as_of_date=AS_OF, collected_at=COLLECTED_AT, data_origin="real",
            events=[], enhancements=[], exposure_mappings=[],
            adjustment=build_event_adjustment_shadow([]),
            source_health=[{"source_id": "csrc_notices", "status": "blocked", "event_state": "no_event"}],
            base_snapshots={},
        )
