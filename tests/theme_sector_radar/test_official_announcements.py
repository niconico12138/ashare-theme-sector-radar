from __future__ import annotations

import hashlib

import pytest


def test_source_registry_covers_official_tiers_and_probe_is_offline_only():
    from theme_sector_radar.data.official_announcements import (
        default_source_registry,
        probe_source_registry,
        validate_source_registry,
    )

    registry = default_source_registry()
    validate_source_registry(registry)
    source_ids = {row["source_id"] for row in registry["sources"]}
    assert {"sse_announcements", "szse_announcements", "bse_announcements"} <= source_ids
    assert {"csrc_notices", "mof_notices", "sta_notices", "ndrc_notices", "miit_notices"} <= source_ids
    assert {"issuer_official_announcements", "fund_official_disclosures"} <= source_ids
    assert {row["authority_tier"] for row in registry["sources"]} == {
        "primary", "secondary", "research_only"
    }
    probe = probe_source_registry(registry)
    assert probe["probe_mode"] == "no_network"
    assert all(row["probe_status"] in {"blocked", "fixture_ready"} for row in probe["sources"])


def test_after_close_uses_next_trading_date_but_date_only_stays_unresolved():
    from theme_sector_radar.data.official_announcements import infer_effective_from

    after_close = infer_effective_from(
        "2026-07-20T15:01:00+08:00",
        trading_dates=["2026-07-20", "2026-07-21"],
    )
    assert after_close["effective_from"] == "2026-07-21"
    assert after_close["inference_status"] == "after_close_next_trading_day"

    date_only = infer_effective_from("2026-07-20")
    assert date_only["effective_from"] is None
    assert date_only["inference_status"] == "date_only_unresolved"


def test_raw_archive_is_content_addressed_and_immutable(tmp_path):
    from theme_sector_radar.data.official_announcements import (
        archive_raw_announcement,
        load_archived_announcement,
    )

    first = archive_raw_announcement(
        tmp_path / "archive",
        source_id="announcement_research_fixture",
        source_url_or_path="fixture://announcement/1",
        published_at="2026-07-20",
        captured_at="2026-07-20T10:00:00+08:00",
        effective_from=None,
        raw_content=b"raw announcement bytes",
    )
    second = archive_raw_announcement(
        tmp_path / "archive",
        source_id="announcement_research_fixture",
        source_url_or_path="fixture://announcement/1",
        published_at="2026-07-20",
        captured_at="2026-07-20T10:00:00+08:00",
        effective_from=None,
        raw_content=b"raw announcement bytes",
    )
    assert first["document_id"] == second["document_id"]
    manifest, content = load_archived_announcement(first["manifest_path"], archive_root=tmp_path / "archive")
    assert content == b"raw announcement bytes"
    assert manifest["raw_sha256"] == hashlib.sha256(content).hexdigest()
    with pytest.raises(ValueError, match="immutable announcement manifest"):
        archive_raw_announcement(
            tmp_path / "archive",
            source_id="announcement_research_fixture",
            source_url_or_path="fixture://announcement/changed",
            published_at="2026-07-20",
            captured_at="2026-07-20T10:00:00+08:00",
            raw_content=b"raw announcement bytes",
        )


def test_event_ledger_deduplicates_versions_and_surfaces_conflicts_without_scores(tmp_path):
    from theme_sector_radar.data.official_announcements import (
        archive_raw_announcement,
        build_event_ledger,
        build_event_record,
    )

    archived = archive_raw_announcement(
        tmp_path / "archive",
        source_id="announcement_research_fixture",
        source_url_or_path="fixture://announcement/2",
        published_at="2026-07-20T10:00:00+08:00",
        captured_at="2026-07-20T10:01:00+08:00",
        raw_content=b"event v1",
    )
    revised_archived = archive_raw_announcement(
        tmp_path / "archive",
        source_id="announcement_research_fixture",
        source_url_or_path="fixture://announcement/2-revised",
        published_at="2026-07-20T10:00:00+08:00",
        captured_at="2026-07-20T10:02:00+08:00",
        raw_content=b"event v2",
        document_version="v2",
        revision_of=archived["document_id"],
    )
    kwargs = dict(
        source_id="announcement_research_fixture",
        event_type="announcement",
        title="A structured announcement",
        issuer="Example Co",
        published_at="2026-07-20T10:00:00+08:00",
        evidence_refs=[{"document_id": archived["document_id"], "raw_sha256": archived["raw_sha256"]}],
        structured_fields={"announcement_kind": "notice"},
    )
    first = build_event_record(**kwargs, event_id="event-first")
    duplicate = build_event_record(**kwargs, event_id="event-duplicate")
    conflict_kwargs = {
        **kwargs,
        "evidence_refs": [
            {
                "document_id": revised_archived["document_id"],
                "raw_sha256": revised_archived["raw_sha256"],
            }
        ],
    }
    conflict = build_event_record(**conflict_kwargs, event_id="event-conflict")
    ledger = build_event_ledger([first, duplicate, conflict])
    assert ledger["duplicate_count"] == 1
    assert ledger["conflict_count"] == 1
    assert ledger["status"] == "conflicts_present"
    assert all(
        not any(str(key).casefold().endswith("_score") for key in event["structured_fields"])
        for event in ledger["events"]
    )
    with pytest.raises(ValueError, match="prohibited score/action"):
        build_event_record(**{**kwargs, "structured_fields": {"impact_score": 1.0}})


def test_source_health_never_turns_failed_or_unobserved_sources_into_no_event():
    from theme_sector_radar.data.official_announcements import build_source_health_report

    report = build_source_health_report(
        [
            {
                "source_id": "sse_announcements",
                "retrieval_status": "retrieval_failed",
                "error_code": "network_disabled",
            },
            {
                "source_id": "announcement_research_fixture",
                "retrieval_status": "parse_failed",
                "parse_status": "parse_failed",
                "event_count": 0,
            },
        ]
    )
    assert all(row["event_state"] != "no_event" for row in report["sources"])
    assert report["summary"]["blocked_or_unavailable_count"] >= 1
    assert report["summary"]["parse_failed_count"] == 1
    with pytest.raises(ValueError, match="no_event"):
        build_source_health_report(
            [{"source_id": "sse_announcements", "event_state": "no_event"}]
        )
