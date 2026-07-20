from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import copy
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture
def capture_time(monkeypatch):
    def set_capture_time(value: datetime) -> None:
        monkeypatch.setattr(
            "theme_sector_radar.ml.accumulation._capture_now",
            lambda value=value: value,
        )

    return set_capture_time


def _candidate(code: str, *, quant: float, linkage_status: str, linkage: float | None):
    candidate = {
        "code": code,
        "name": f"stock-{code}",
        "sector_name": "医疗服务",
        "sector_type": "industry",
        "pe": 12.0,
        "pb": 1.5,
        "total_mv": 100.0,
        "sector_trend_score": 72.0,
        "sector_burst_score": 68.0,
        "direction_score_shadow": 75.0,
        "data_quality_score": 95.0,
        "factor_coverage": 0.9,
        "quant_score": quant,
        "linkage_v2_shadow": {
            "status": linkage_status,
            "score": linkage,
            "components": {},
        },
    }
    if linkage is not None:
        candidate["linkage_selection_score"] = round(
            0.70 * linkage * 100.0 + 0.30 * quant, 6
        )
    return candidate


def test_extract_candidate_snapshot_uses_active_direction_linkage_selection_only():
    from theme_sector_radar.ml.accumulation import extract_candidate_snapshot

    report = {
        "as_of_date": "2026-07-16",
        "candidate_chain": "direction_linkage_v2",
        "direction_shadow_candidates_all": [
            _candidate("999999", quant=99.0, linkage_status="ok", linkage=1.0)
        ],
        "direction_linkage_v2_selection_shadow": {
            "schema_version": "direction_linkage_v2_selection_shadow.v1",
            "mode": "paper_shadow_research_only",
            "policy": {"ranking_weights": {"linkage_v2": 0.70, "quant_score": 0.30}},
            "selected_count": 2,
            "selected": [
                _candidate("000001", quant=80.0, linkage_status="ok", linkage=0.7),
                _candidate("000002", quant=60.0, linkage_status="partial", linkage=0.4),
            ],
        },
    }

    snapshot = extract_candidate_snapshot(report)

    assert snapshot["selection_source_field"] == "direction_linkage_v2_selection_shadow"
    assert [row["code"] for row in snapshot["feature_candidates"]] == [
        "000001",
        "000002",
    ]
    assert snapshot["baseline_rows"] == [
        {
            "as_of_date": "2026-07-16",
            "stock_code": "000001",
            "sector_name": "医疗服务",
            "sector_type": "industry",
            "quant_baseline_score_shadow": 80.0,
            "linkage_v2_baseline_score_shadow": 70.0,
            "linkage_v2_status": "ok",
            "rule_eligible": True,
        },
        {
            "as_of_date": "2026-07-16",
            "stock_code": "000002",
            "sector_name": "医疗服务",
            "sector_type": "industry",
            "quant_baseline_score_shadow": 60.0,
            "linkage_v2_baseline_score_shadow": 40.0,
            "linkage_v2_status": "partial",
            "rule_eligible": True,
        },
    ]
    assert "quant_score" not in snapshot["feature_candidates"][0]


def test_extract_candidate_snapshot_rejects_unselected_relation_pool():
    from theme_sector_radar.ml.accumulation import extract_candidate_snapshot

    with pytest.raises(ValueError, match="active direction/linkage V2 selection"):
        extract_candidate_snapshot(
            {
                "as_of_date": "2026-07-16",
                "direction_shadow_candidates_all": [
                    _candidate("000001", quant=80.0, linkage_status="ok", linkage=0.7)
                ],
            }
        )


def test_extract_candidate_snapshot_rejects_formal_selection_count_drift():
    from theme_sector_radar.ml.accumulation import extract_candidate_snapshot

    with pytest.raises(ValueError, match="formal candidate selected_count mismatch"):
        extract_candidate_snapshot(
            {
                "as_of_date": "2026-07-16",
                "formal_candidate_selection": {
                    "status": "active_for_paper_research",
                    "selected_count": 2,
                    "selected": [
                        _candidate("000001", quant=80.0, linkage_status="ok", linkage=0.7)
                    ],
                },
            }
        )


def test_archive_capture_time_is_not_caller_injectable():
    import inspect

    from theme_sector_radar.ml.accumulation import (
        archive_daily_snapshot,
        archive_mature_label_snapshot,
    )

    assert "captured_at" not in inspect.signature(archive_daily_snapshot).parameters
    assert "captured_at" not in inspect.signature(
        archive_mature_label_snapshot
    ).parameters


def test_candidate_selection_requires_replayable_policy_contract():
    from theme_sector_radar.ml.accumulation import extract_candidate_snapshot

    report = _active_report()
    report["direction_linkage_v2_selection_shadow"]["policy"]["ranking_weights"] = {
        "linkage_v2": 0.4,
        "quant_score": 0.6,
    }

    with pytest.raises(ValueError, match="ranking weights|selection contract"):
        extract_candidate_snapshot(report)


def _bars(as_of: str, *, count: int = 25):
    from datetime import date, timedelta

    end = date.fromisoformat(as_of)
    days = []
    cursor = end
    while len(days) < count:
        if cursor.weekday() < 5:
            days.append(cursor.isoformat())
        cursor -= timedelta(days=1)
    return [
        {
            "date": day,
            "open": 10.0 + index * 0.1,
            "high": 10.2 + index * 0.1,
            "low": 9.8 + index * 0.1,
            "close": 10.1 + index * 0.1,
            "volume": 1000.0 + index,
            "amount": 10000.0 + index,
        }
        for index, day in enumerate(reversed(days))
    ]


def _active_report(as_of: str = "2026-07-16"):
    from theme_sector_radar.scoring.stock_sector_linkage import (
        build_formal_candidate_selection,
    )

    linkage = {
        "schema_version": "direction_linkage_v2_selection_shadow.v1",
        "mode": "paper_shadow_research_only",
        "policy": {"ranking_weights": {"linkage_v2": 0.70, "quant_score": 0.30}},
        "selected_count": 2,
        "selected": [
            _candidate("000001", quant=80.0, linkage_status="ok", linkage=0.7),
            _candidate("000002", quant=60.0, linkage_status="partial", linkage=0.4),
        ],
    }
    direction_source = {
        "status": "ok",
        "mode": "paper_shadow_research_only",
        "path": "direction.json",
        "sha256": "a" * 64,
    }
    formal = build_formal_candidate_selection(
        direction_source=direction_source,
        linkage_selection=linkage,
    )
    return {
        "as_of_date": as_of,
        "candidate_chain": "direction_linkage_v2",
        "direction_linkage_v2_selection_shadow": linkage,
        "formal_candidate_selection": formal,
    }


def _physical_daily_sources(
    root: Path,
    *,
    as_of: str,
    report: dict,
    calendar_dates: list[str],
    generated_at: str,
):
    from theme_sector_radar.data.trading_calendar import load_trading_calendar
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json_with_sha256,
        write_strict_json_atomic,
    )

    source_root = root / "physical_sources"
    candidate_path = source_root / "candidates" / f"{as_of}.json"
    write_strict_json_atomic(candidate_path, report)
    _candidate_doc, candidate_sha = load_strict_json_with_sha256(candidate_path)

    selected = report["direction_linkage_v2_selection_shadow"]["selected"]
    sector_name = str(selected[0]["sector_name"])
    sector_type = str(selected[0].get("sector_type") or "industry")
    constituent_path = source_root / "constituents" / f"{as_of}.json"
    write_strict_json_atomic(
        constituent_path,
        {
            "as_of_date": as_of,
            "sector_name": sector_name,
            "sector_type": sector_type,
            "source": "http_em",
            "stocks": [{"code": str(row["code"])} for row in selected],
        },
    )
    _constituent_doc, constituent_sha = load_strict_json_with_sha256(
        constituent_path
    )

    calendar_path = source_root / "calendar.json"
    write_strict_json_atomic(
        calendar_path,
        {
            "schema_version": "a_share_trading_calendar.v1",
            "market": "CN_A",
            "source": "akshare.tool_trade_date_hist_sina",
            "requested_start": calendar_dates[0],
            "requested_end": calendar_dates[-1],
            "dates": calendar_dates,
            "date_count": len(calendar_dates),
        },
    )
    calendar = load_trading_calendar(calendar_path, as_of=as_of, include_future=True)
    return {
        "candidate_source": {
            "path": str(candidate_path.resolve()),
            "sha256": candidate_sha,
            "generated_at": generated_at,
            "as_of_date": as_of,
            "source": "unified_pipeline_direction_linkage_v2",
        },
        "constituent_sources": [
            {
                "path": str(constituent_path.resolve()),
                "sha256": constituent_sha,
                "as_of_date": as_of,
                "sector_name": sector_name,
                "sector_type": sector_type,
                "source": "http_em",
            }
        ],
        "trading_calendar": calendar,
    }


def _physical_label_source(
    root: Path,
    *,
    signal_date: str,
    label_as_of_date: str,
    stock_prices: dict,
    sector_prices: dict,
):
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json_with_sha256,
        write_strict_json_atomic,
    )

    source_root = root / "physical_sources" / "labels" / signal_date
    stock_sources = {}
    for code, rows in stock_prices.items():
        path = source_root / "stocks" / f"{code}.json"
        write_strict_json_atomic(path, {"stock_code": code, "bars": rows})
        _payload, sha256 = load_strict_json_with_sha256(path)
        stock_sources[code] = {
            "requested_source": "stockdb-sdk",
            "actual_source": "stockdb-sdk",
            "path": str(path.resolve()),
            "sha256": sha256,
        }
    sector_sources = {}
    for sector_name, rows in sector_prices.items():
        filename = hashlib.sha256(sector_name.encode("utf-8")).hexdigest()
        path = source_root / "sectors" / f"{filename}.json"
        write_strict_json_atomic(
            path,
            {
                "sector_name": sector_name,
                "sector_type": "industry",
                "source": "sector_history/ths_industry_index",
                "records": rows,
            },
        )
        _payload, sha256 = load_strict_json_with_sha256(path)
        sector_sources[sector_name] = {
            "sector_type": "industry",
            "source": "sector_history/ths_industry_index",
            "path": str(path.resolve()),
            "sha256": sha256,
        }
    return {
        "provider": "stockdb-sdk",
        "adjustment": "qfq",
        "frequency": "1d",
        "query_end": label_as_of_date,
        "stock_bars_by_code": stock_sources,
        "sector_bars_by_name": sector_sources,
    }


def _physical_daily_bars_source(
    root: Path,
    *,
    as_of: str,
    bars_by_code: dict,
    provider: str = "stockdb-sdk",
):
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json_with_sha256,
        write_strict_json_atomic,
    )

    by_code = {}
    for code, rows in bars_by_code.items():
        path = root / "physical_sources" / "daily_bars" / as_of / f"{code}.json"
        write_strict_json_atomic(
            path,
            {
                "code": code,
                "as_of": as_of,
                "source": provider,
                "bars": rows,
            },
        )
        _payload, sha256 = load_strict_json_with_sha256(path)
        by_code[code] = {
            "requested_source": provider,
            "actual_source": provider,
            "path": str(path.resolve()),
            "sha256": sha256,
        }
    return {
        "provider": provider,
        "adjustment": "qfq",
        "frequency": "1d",
        "query_end": as_of,
        "by_code": by_code,
    }


def test_daily_snapshot_archive_is_prospective_content_bound_and_immutable(
    tmp_path, capture_time
):
    from theme_sector_radar.ml.accumulation import archive_daily_snapshot

    as_of = "2026-07-16"
    report = _active_report(as_of)
    calendar_dates = [
        as_of,
        "2026-07-17",
        "2026-07-20",
        "2026-07-21",
        "2026-07-22",
        "2026-07-23",
    ]
    physical = _physical_daily_sources(
        tmp_path,
        as_of=as_of,
        report=report,
        calendar_dates=calendar_dates,
        generated_at="2026-07-16T16:30:00+08:00",
    )
    bars_by_code = {"000001": _bars(as_of), "000002": _bars(as_of)}
    bars_source = _physical_daily_bars_source(
        tmp_path, as_of=as_of, bars_by_code=bars_by_code
    )
    kwargs = {
        "archive_root": tmp_path,
        "candidate_report": report,
        "candidate_source": physical["candidate_source"],
        "constituent_sources": physical["constituent_sources"],
        "bars_by_code": bars_by_code,
        "bars_source": bars_source,
        "trading_calendar": physical["trading_calendar"],
    }

    capture_time(datetime(2026, 7, 16, 18, 0, tzinfo=timezone.utc))
    created = archive_daily_snapshot(**kwargs)
    repeated = archive_daily_snapshot(**kwargs)

    assert created["created"] is True
    assert repeated["created"] is False
    assert created["snapshot_sha256"] == repeated["snapshot_sha256"]
    assert created["snapshot"]["strict_pit_eligible"] is True
    assert created["snapshot"]["pit_evidence_status"] == "prospective_pre_label_capture"
    assert created["snapshot"]["candidate_count"] == 2
    assert created["snapshot"]["feature_row_count"] == 2
    assert set(created["snapshot"]["bars_by_code"]) == {"000001", "000002"}
    assert set(created["snapshot"]["bars_source_by_code"]) == {
        "000001",
        "000002",
    }
    assert all(
        row["actual_source"] == "stockdb-sdk"
        and row["query_end"] == as_of
        and len(row["bars_sha256"]) == 64
        for row in created["snapshot"]["bars_source_by_code"].values()
    )
    assert created["snapshot"]["promotion_allowed"] is False

    changed = dict(kwargs)
    changed["bars_by_code"] = dict(kwargs["bars_by_code"])
    changed["bars_by_code"]["000001"] = list(_bars(as_of))
    changed["bars_by_code"]["000001"][-1] = {
        **changed["bars_by_code"]["000001"][-1],
        "close": 99.0,
    }
    with pytest.raises(
        ValueError, match="immutable daily snapshot input changed|daily bars source"
    ):
        archive_daily_snapshot(**changed)


@pytest.mark.parametrize(
    ("fixture_target", "expected_reason"),
    (
        ("candidate", "candidate_source_not_approved_for_observed_research"),
        ("constituent", "constituent_source_not_approved_for_observed_research"),
        ("bars", "daily_bars_source_not_approved_for_observed_research"),
    ),
)
def test_fixture_sources_can_never_claim_prospective_pit(
    tmp_path, fixture_target, expected_reason, capture_time
):
    from theme_sector_radar.ml.accumulation import archive_daily_snapshot

    as_of = "2026-07-16"
    report = _active_report(as_of)
    physical = _physical_daily_sources(
        tmp_path,
        as_of=as_of,
        report=report,
        calendar_dates=[
            as_of,
            "2026-07-17",
            "2026-07-20",
            "2026-07-21",
            "2026-07-22",
            "2026-07-23",
        ],
        generated_at="2026-07-16T16:30:00+08:00",
    )
    bars_by_code = {"000001": _bars(as_of), "000002": _bars(as_of)}
    bars_source = _physical_daily_bars_source(
        tmp_path, as_of=as_of, bars_by_code=bars_by_code
    )
    if fixture_target == "candidate":
        physical["candidate_source"]["source"] = "synthetic_fixture"
    elif fixture_target == "constituent":
        physical["constituent_sources"][0]["source"] = "fixture"
    else:
        bars_source = _physical_daily_bars_source(
            tmp_path,
            as_of=as_of,
            bars_by_code=bars_by_code,
            provider="synthetic_fixture",
        )

    capture_time(datetime(2026, 7, 16, 18, 0, tzinfo=timezone.utc))
    captured = archive_daily_snapshot(
        archive_root=tmp_path / "archive",
        candidate_report=report,
        candidate_source=physical["candidate_source"],
        constituent_sources=physical["constituent_sources"],
        bars_by_code=bars_by_code,
        bars_source=bars_source,
        trading_calendar=physical["trading_calendar"],
    )

    assert captured["snapshot"]["strict_pit_eligible"] is False
    assert expected_reason in captured["snapshot"]["pit_blocking_reasons"]


def test_relative_source_identities_can_never_claim_strict_pit(tmp_path, capture_time):
    from theme_sector_radar.ml.accumulation import archive_daily_snapshot

    as_of = "2026-07-16"
    report = _active_report(as_of)
    sector_name = report["direction_linkage_v2_selection_shadow"]["selected"][0][
        "sector_name"
    ]
    capture_time(datetime(2026, 7, 16, 18, 0, tzinfo=timezone.utc))
    result = archive_daily_snapshot(
        archive_root=tmp_path,
        candidate_report=report,
        candidate_source={
            "path": "logical-only-candidate.json",
            "sha256": "a" * 64,
            "generated_at": "2026-07-16T16:30:00+08:00",
            "as_of_date": as_of,
        },
        constituent_sources=[
            {
                "path": "logical-only-constituents.json",
                "sha256": "b" * 64,
                "as_of_date": as_of,
                "sector_name": sector_name,
            }
        ],
        bars_by_code={"000001": _bars(as_of), "000002": _bars(as_of)},
        bars_source={
            "provider": "stockdb-sdk",
            "adjustment": "qfq",
            "frequency": "1d",
            "query_end": as_of,
        },
        trading_calendar={
            "dates": [
                as_of,
                "2026-07-17",
                "2026-07-20",
                "2026-07-21",
                "2026-07-22",
                "2026-07-23",
            ],
            "source": "logical-only-calendar",
            "path": "logical-only-calendar.json",
            "sha256": "c" * 64,
            "requested_start": as_of,
            "requested_end": "2026-07-23",
        },
    )

    assert result["snapshot"]["strict_pit_eligible"] is False
    assert set(result["snapshot"]["pit_blocking_reasons"]) >= {
        "candidate_source_not_content_addressable",
        "constituent_source_not_content_addressable",
        "calendar_source_not_content_addressable",
    }


def test_physical_candidate_source_must_reproduce_the_passed_selection(
    tmp_path, capture_time
):
    from theme_sector_radar.ml.accumulation import archive_daily_snapshot
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json_with_sha256,
        write_strict_json_atomic,
    )

    as_of = "2026-07-16"
    report = _active_report(as_of)
    calendar_dates = [
        as_of,
        "2026-07-17",
        "2026-07-20",
        "2026-07-21",
        "2026-07-22",
        "2026-07-23",
    ]
    physical = _physical_daily_sources(
        tmp_path,
        as_of=as_of,
        report=report,
        calendar_dates=calendar_dates,
        generated_at="2026-07-16T16:30:00+08:00",
    )
    source_report = copy.deepcopy(report)
    source_report["direction_linkage_v2_selection_shadow"]["selected"].pop()
    source_report["direction_linkage_v2_selection_shadow"]["selected_count"] = 1
    candidate_path = Path(physical["candidate_source"]["path"])
    write_strict_json_atomic(candidate_path, source_report)
    _source_doc, source_sha = load_strict_json_with_sha256(candidate_path)
    physical["candidate_source"]["sha256"] = source_sha
    bars_by_code = {"000001": _bars(as_of), "000002": _bars(as_of)}
    bars_source = _physical_daily_bars_source(
        tmp_path, as_of=as_of, bars_by_code=bars_by_code
    )

    capture_time(datetime(2026, 7, 16, 18, 0, tzinfo=timezone.utc))
    with pytest.raises(
        ValueError,
        match="formal candidate selection contract|candidate source contents",
    ):
        archive_daily_snapshot(
            archive_root=tmp_path / "archive",
            candidate_report=report,
            candidate_source=physical["candidate_source"],
            constituent_sources=physical["constituent_sources"],
            bars_by_code=bars_by_code,
            bars_source=bars_source,
            trading_calendar=physical["trading_calendar"],
        )


def test_archive_verifier_recomputes_pit_status_instead_of_trusting_flag(
    tmp_path, capture_time
):
    from theme_sector_radar.ml.accumulation import (
        archive_daily_snapshot,
        verify_accumulation_archive,
    )
    from theme_sector_radar.ml.contract import canonical_sha256
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json_with_sha256,
        write_strict_json_atomic,
    )

    as_of = "2026-07-16"
    kwargs = {
        "archive_root": tmp_path,
        "candidate_report": _active_report(as_of),
        "candidate_source": {
            "path": "reports/2026-07-16/unified_report.json",
            "sha256": "a" * 64,
            "generated_at": "2026-07-18T16:30:00+08:00",
            "as_of_date": as_of,
        },
        "constituent_sources": [
            {
                "path": "data_cache/sector_stocks/2026-07-16_industry_医疗服务.json",
                "sha256": "b" * 64,
                "as_of_date": as_of,
                "sector_name": "医疗服务",
            }
        ],
        "bars_by_code": {"000001": _bars(as_of), "000002": _bars(as_of)},
        "bars_source": {
            "provider": "stockdb-sdk",
            "adjustment": "qfq",
            "frequency": "1d",
            "query_end": as_of,
        },
        "trading_calendar": {
            "dates": [as_of, "2026-07-17", "2026-07-20", "2026-07-21", "2026-07-22", "2026-07-23"],
            "source": "test-calendar",
            "path": "calendar.json",
            "sha256": "c" * 64,
            "requested_start": as_of,
            "requested_end": "2026-07-23",
        },
    }
    capture_time(datetime(2026, 7, 18, 18, 0, tzinfo=timezone.utc))
    archive_daily_snapshot(**kwargs)
    snapshot_path = tmp_path / "snapshots" / f"{as_of}.json"
    snapshot, _ = load_strict_json_with_sha256(snapshot_path)
    snapshot["strict_pit_eligible"] = True
    snapshot["pit_evidence_status"] = "prospective_pre_label_capture"
    snapshot["pit_blocking_reasons"] = []
    write_strict_json_atomic(snapshot_path, snapshot)

    index_path = tmp_path / "index.json"
    index, _ = load_strict_json_with_sha256(index_path)
    snapshot_sha = load_strict_json_with_sha256(snapshot_path)[1]
    entry = dict(index["entries"][0])
    entry["snapshot_sha256"] = snapshot_sha
    entry_core = {key: value for key, value in entry.items() if key != "entry_sha256"}
    entry["entry_sha256"] = canonical_sha256(entry_core)
    index["entries"] = [entry]
    index["chain_head_sha256"] = entry["entry_sha256"]
    write_strict_json_atomic(index_path, index)

    with pytest.raises(ValueError, match="PIT|pit|identity"):
        verify_accumulation_archive(tmp_path)


def test_historical_daily_snapshot_never_claims_strict_pit(tmp_path, capture_time):
    from theme_sector_radar.ml.accumulation import archive_daily_snapshot

    as_of = "2026-07-16"
    capture_time(datetime(2026, 7, 18, 18, 0, tzinfo=timezone.utc))
    result = archive_daily_snapshot(
        archive_root=tmp_path,
        candidate_report=_active_report(as_of),
        candidate_source={
            "path": "reports/2026-07-16/unified_report.json",
            "sha256": "a" * 64,
            "generated_at": "2026-07-18T16:30:00+08:00",
        },
        constituent_sources=[
            {
                "path": "data_cache/sector_stocks/2026-07-16_industry_医疗服务.json",
                "sha256": "b" * 64,
                "as_of_date": as_of,
                "sector_name": "医疗服务",
            }
        ],
        bars_by_code={"000001": _bars(as_of), "000002": _bars(as_of)},
        bars_source={
            "provider": "stockdb-sdk",
            "adjustment": "qfq",
            "frequency": "1d",
            "query_end": as_of,
        },
        trading_calendar={
            "dates": [as_of, "2026-07-17", "2026-07-20", "2026-07-21", "2026-07-22", "2026-07-23"],
            "source": "test-calendar",
            "path": "calendar.json",
            "sha256": "c" * 64,
            "requested_start": as_of,
            "requested_end": "2026-07-23",
        },
    )

    assert result["snapshot"]["strict_pit_eligible"] is False
    assert result["snapshot"]["pit_evidence_status"] == "historical_reconstruction"
    assert "capture_after_signal_date" in result["snapshot"]["pit_blocking_reasons"]
    assert "candidate_source_generated_after_signal_date" in result["snapshot"][
        "pit_blocking_reasons"
    ]

    from theme_sector_radar.ml.accumulation import build_archive_readiness_report

    readiness = build_archive_readiness_report(tmp_path)
    assert readiness["historical_candidate_universe_versioned"] is False
    assert readiness["historical_candidate_universe_verified"] is False


def test_same_day_naive_source_time_uses_timezone_aware_archive_witness(
    tmp_path, capture_time
):
    from theme_sector_radar.ml.accumulation import archive_daily_snapshot

    as_of = "2026-07-16"
    report = _active_report(as_of)
    calendar_dates = [
        as_of,
        "2026-07-17",
        "2026-07-20",
        "2026-07-21",
        "2026-07-22",
        "2026-07-23",
    ]
    physical = _physical_daily_sources(
        tmp_path,
        as_of=as_of,
        report=report,
        calendar_dates=calendar_dates,
        generated_at="2026-07-16T16:30:00",
    )
    bars_by_code = {"000001": _bars(as_of), "000002": _bars(as_of)}
    bars_source = _physical_daily_bars_source(
        tmp_path, as_of=as_of, bars_by_code=bars_by_code
    )
    capture_time(datetime(2026, 7, 16, 18, 0, tzinfo=timezone.utc))
    result = archive_daily_snapshot(
        archive_root=tmp_path,
        candidate_report=report,
        bars_by_code=bars_by_code,
        bars_source=bars_source,
        candidate_source=physical["candidate_source"],
        constituent_sources=physical["constituent_sources"],
        trading_calendar=physical["trading_calendar"],
    )

    assert result["snapshot"]["strict_pit_eligible"] is True
    assert result["snapshot"]["source_timestamp_quality"] == {
        "status": "naive",
        "accepted_as_ordering_witness": False,
        "archive_witness": "timezone_aware_capture_bound_to_source_sha_and_as_of_date",
    }
    assert result["snapshot"]["pit_blocking_reasons"] == []


def test_label_archive_waits_for_five_day_maturity_then_binds_snapshot(
    tmp_path, capture_time
):
    from theme_sector_radar.ml.accumulation import (
        archive_daily_snapshot,
        archive_mature_label_snapshot,
    )

    as_of = "2026-07-16"
    calendar_dates = [
        as_of,
        "2026-07-17",
        "2026-07-20",
        "2026-07-21",
        "2026-07-22",
        "2026-07-23",
    ]
    report = _active_report(as_of)
    physical = _physical_daily_sources(
        tmp_path,
        as_of=as_of,
        report=report,
        calendar_dates=calendar_dates,
        generated_at="2026-07-16T16:30:00+08:00",
    )
    feature_bars = {"000001": _bars(as_of), "000002": _bars(as_of)}
    feature_bars_source = _physical_daily_bars_source(
        tmp_path, as_of=as_of, bars_by_code=feature_bars
    )
    calendar = physical["trading_calendar"]
    capture_time(datetime(2026, 7, 16, 18, 0, tzinfo=timezone.utc))
    archived = archive_daily_snapshot(
        archive_root=tmp_path,
        candidate_report=report,
        candidate_source=physical["candidate_source"],
        constituent_sources=physical["constituent_sources"],
        bars_by_code=feature_bars,
        bars_source=feature_bars_source,
        trading_calendar=calendar,
    )
    prices = {
        code: [
            {"date": day, "close": 10.0 + index + (0.2 if code == "000001" else 0.0)}
            for index, day in enumerate(calendar_dates)
        ]
        for code in ("000001", "000002")
    }
    sector_prices = {
        "医疗服务": [
            {"date": day, "close": 100.0 + index}
            for index, day in enumerate(calendar_dates)
        ]
    }
    mature_label_source = _physical_label_source(
        tmp_path,
        signal_date=as_of,
        label_as_of_date="2026-07-23",
        stock_prices=prices,
        sector_prices=sector_prices,
    )

    capture_time(datetime(2026, 7, 22, 18, 0, tzinfo=timezone.utc))
    pending = archive_mature_label_snapshot(
        archive_root=tmp_path,
        signal_date=as_of,
        label_as_of_date="2026-07-22",
        stock_bars_by_code=prices,
        sector_bars_by_name=sector_prices,
        label_source={
            "provider": "stockdb-sdk",
            "adjustment": "qfq",
            "frequency": "1d",
            "query_end": "2026-07-22",
        },
    )
    assert pending == {
        "status": "pending_label_maturity",
        "signal_date": as_of,
        "target_5d": "2026-07-23",
        "promotion_allowed": False,
        "live_trading_allowed": False,
    }

    capture_time(datetime(2026, 7, 23, 18, 0, tzinfo=timezone.utc))
    mature = archive_mature_label_snapshot(
        archive_root=tmp_path,
        signal_date=as_of,
        label_as_of_date="2026-07-23",
        stock_bars_by_code=prices,
        sector_bars_by_name=sector_prices,
        label_source=mature_label_source,
    )
    assert mature["status"] == "captured"
    assert mature["label_snapshot"]["feature_snapshot_sha256"] == archived[
        "snapshot_sha256"
    ]
    assert mature["label_snapshot"]["strict_pit_eligible"] is True
    assert mature["label_snapshot"]["label_row_count"] == 2
    assert all(
        row["training_label_end_date"] == "2026-07-23"
        for row in mature["label_snapshot"]["label_rows"]
    )

    from theme_sector_radar.ml.accumulation import verify_accumulation_archive

    evidence = verify_accumulation_archive(tmp_path)
    assert evidence["status"] == "verified"
    assert evidence["counts"] == {
        "candidate_snapshot_dates": 1,
        "prospective_candidate_snapshot_dates": 1,
        "mature_label_dates": 1,
        "strict_mature_label_dates": 1,
        "verified_training_dates": 1,
        "candidate_rows": 2,
        "verified_training_rows": 2,
    }
    assert evidence["verified_training_dates"] == [as_of]
    assert evidence["strict_pit_eligible"] is False
    assert evidence["minimum_60_dates_satisfied"] is False
    assert len(evidence["evidence_sha256"]) == 64

    project_root = Path(__file__).resolve().parents[2]
    dataset_path = tmp_path / "blocked_dataset.json"
    baseline_path = tmp_path / "blocked_baseline.json"
    readiness_path = tmp_path / "blocked_readiness.json"
    report_path = tmp_path / "blocked_build_report.json"
    blocked = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "build_ml_stock_dataset_from_archive.py"),
            "--archive-root", str(tmp_path),
            "--dataset-output", str(dataset_path),
            "--baseline-output", str(baseline_path),
            "--readiness-output", str(readiness_path),
            "--report-output", str(report_path),
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert blocked.returncode == 0, blocked.stderr
    from theme_sector_radar.reporting.strict_json import load_strict_json

    assert load_strict_json(dataset_path)["status"] == "blocked"
    assert load_strict_json(readiness_path)["model_training_ready"] is False

    from theme_sector_radar.ml.contract import canonical_sha256
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json_with_sha256,
        write_strict_json_atomic,
    )

    label_path = tmp_path / "labels" / f"{as_of}.json"
    label_snapshot, _ = load_strict_json_with_sha256(label_path)
    label_snapshot["captured_at"] = "2026-07-23T18:00:00"
    write_strict_json_atomic(label_path, label_snapshot)
    label_sha = load_strict_json_with_sha256(label_path)[1]
    labels_index_path = tmp_path / "labels_index.json"
    labels_index, _ = load_strict_json_with_sha256(labels_index_path)
    entry = dict(labels_index["entries"][0])
    entry["label_snapshot_sha256"] = label_sha
    entry_core = {key: value for key, value in entry.items() if key != "entry_sha256"}
    entry["entry_sha256"] = canonical_sha256(entry_core)
    labels_index["entries"] = [entry]
    labels_index["chain_head_sha256"] = entry["entry_sha256"]
    write_strict_json_atomic(labels_index_path, labels_index)

    with pytest.raises(ValueError, match="captured_at must be timezone-aware"):
        verify_accumulation_archive(tmp_path)


def test_sixty_day_archive_builds_strict_dataset_and_enters_train_evaluate(
    tmp_path, capture_time
):
    from theme_sector_radar.ml.accumulation import (
        archive_daily_snapshot,
        archive_mature_label_snapshot,
    )
    from theme_sector_radar.ml.contract import canonical_sha256
    from theme_sector_radar.ml.dataset import validate_training_dataset
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json,
        load_strict_json_with_sha256,
    )

    project_root = Path(__file__).resolve().parents[2]
    trading_dates = []
    cursor = date(2026, 1, 5)
    while len(trading_dates) < 72:
        if cursor.weekday() < 5:
            trading_dates.append(cursor.isoformat())
        cursor += timedelta(days=1)
    archive_root = tmp_path / "archive"
    for day_index, day in enumerate(trading_dates[:67]):
        report = _active_report(day)
        physical = _physical_daily_sources(
            tmp_path,
            as_of=day,
            report=report,
            calendar_dates=trading_dates,
            generated_at=f"{day}T16:30:00+00:00",
        )
        feature_bars = {"000001": _bars(day), "000002": _bars(day)}
        feature_bars_source = _physical_daily_bars_source(
            tmp_path, as_of=day, bars_by_code=feature_bars
        )
        capture_day = date.fromisoformat(day) + timedelta(days=day_index == 0)
        capture_time(datetime.combine(capture_day, time(18, 0), tzinfo=timezone.utc))
        archive_daily_snapshot(
            archive_root=archive_root,
            candidate_report=report,
            candidate_source=physical["candidate_source"],
            constituent_sources=physical["constituent_sources"],
            bars_by_code=feature_bars,
            bars_source=feature_bars_source,
            trading_calendar=physical["trading_calendar"],
        )
    for index, day in enumerate(trading_dates[:67]):
        label_dates = trading_dates[index : index + 6]
        target = label_dates[-1]
        stock_prices = {
            code: [
                {
                    "date": label_day,
                    "close": 10.0 + offset + stock_offset * (offset + 1),
                }
                for offset, label_day in enumerate(label_dates)
            ]
            for stock_offset, code in enumerate(("000001", "000002"), start=1)
        }
        sector_prices = {
            "医疗服务": [
                {"date": label_day, "close": 100.0 + offset}
                for offset, label_day in enumerate(label_dates)
            ]
        }
        label_source = _physical_label_source(
            tmp_path,
            signal_date=day,
            label_as_of_date=target,
            stock_prices=stock_prices,
            sector_prices=sector_prices,
        )
        capture_time(
            datetime.combine(
                date.fromisoformat(target), time(18, 0), tzinfo=timezone.utc
            )
        )
        archive_mature_label_snapshot(
            archive_root=archive_root,
            signal_date=day,
            label_as_of_date=target,
            stock_bars_by_code=stock_prices,
            sector_bars_by_name=sector_prices,
            label_source=label_source,
        )

    dataset_path = tmp_path / "dataset.json"
    baseline_path = tmp_path / "baseline.json"
    readiness_path = tmp_path / "readiness.json"
    build_report_path = tmp_path / "build_report.json"
    build = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "build_ml_stock_dataset_from_archive.py"),
            "--archive-root", str(archive_root),
            "--dataset-output", str(dataset_path),
            "--baseline-output", str(baseline_path),
            "--readiness-output", str(readiness_path),
            "--report-output", str(build_report_path),
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    dataset = load_strict_json(dataset_path)
    assert dataset["strict_pit_eligible"] is True
    assert dataset["date_range"]["date_count"] == 66
    baseline = load_strict_json(baseline_path)
    assert baseline["strict_pit_eligible"] is True
    assert len(baseline["records"]) == 132
    assert load_strict_json(readiness_path)[
        "historical_candidate_universe_verified"
    ] is True
    _dataset_doc, dataset_file_sha = load_strict_json_with_sha256(dataset_path)

    model_dir = tmp_path / "model"
    training_report_path = tmp_path / "training_report.json"
    walk_forward_path = tmp_path / "walk_forward.json"
    train = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "train_ml_stock_ranker_shadow.py"),
            "--dataset", str(dataset_path),
            "--expected-dataset-file-sha256", dataset_file_sha,
            "--model-dir", str(model_dir),
            "--report", str(training_report_path),
            "--walk-forward-output", str(walk_forward_path),
            "--model-version", "stock_ranker_lgbm_v1_prospective_test",
            "--min-train-dates", "60",
            "--test-dates", "1",
            "--purge-dates", "5",
            "--n-estimators", "2",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert train.returncode == 0, train.stderr
    assert load_strict_json(training_report_path)["strict_pit_eligible"] is True

    from theme_sector_radar.ml.registry import load_model_bundle, save_model_bundle
    from theme_sector_radar.reporting.strict_json import write_strict_json_atomic

    registry_path = model_dir / "registry.json"
    training_report = load_strict_json(training_report_path)
    registry_before_load = load_strict_json(registry_path)
    assert date.fromisoformat(registry_before_load["model_available_from"]) > max(
        datetime.fromisoformat(registry_before_load["registered_at"]).date(),
        max(
            datetime.fromisoformat(row["captured_at"]).date()
            for row in (
                load_strict_json(archive_root / "labels" / f"{day}.json")
                for day in dataset["pit_evidence"]["verified_training_dates"]
            )
        ),
    )
    loaded_model = load_model_bundle(
        model_dir,
        expected_registry_sha256=training_report["model_bundle"]["registry_sha256"],
    )
    with pytest.raises(ValueError, match="dataset does not match"):
        save_model_bundle(
            loaded_model,
            tmp_path / "mismatched-model",
            model_version="mismatched_strict_dataset",
            dataset_sha256="a" * 64,
            strict_pit_eligible=True,
            dataset_classification="observed_research",
            model_available_from=loaded_model.metadata["model_available_from"],
            pit_evidence=dataset["pit_evidence"],
            experiment_config=loaded_model.metadata["experiment"]["config"],
            experiment_config_sha256=loaded_model.metadata["experiment"]["config_sha256"],
        )

    registry = load_strict_json(registry_path)
    registry["training_records_sha256"] = "0" * 64
    write_strict_json_atomic(registry_path, registry)
    _registry_doc, tampered_registry_sha = load_strict_json_with_sha256(
        registry_path
    )
    with pytest.raises(ValueError, match="training records"):
        load_model_bundle(
            model_dir,
            expected_registry_sha256=tampered_registry_sha,
        )

    evaluation_path = tmp_path / "evaluation.json"
    evaluate = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "evaluate_rule_vs_ml_shadow.py"),
            "--predictions", str(walk_forward_path),
            "--dataset", str(dataset_path),
            "--expected-dataset-file-sha256", dataset_file_sha,
            "--rule-rows", str(baseline_path),
            "--output", str(evaluation_path),
            "--top-k", "1", "2",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert evaluate.returncode == 0, evaluate.stderr
    evaluation = load_strict_json(evaluation_path)
    assert evaluation["strict_pit_eligible"] is True
    assert {row["strategy"] for row in evaluation["results"]} == {
        "A_quant", "B_linkage_v2", "C_hybrid", "D_ml"
    }

    tampered_source_dataset = copy.deepcopy(dataset)
    tampered_source_dataset["source_manifest"]["archive_root"] = str(
        (archive_root.parent / "another-archive").resolve()
    )
    with pytest.raises(ValueError, match="source and PIT archives"):
        validate_training_dataset(tampered_source_dataset)

    from theme_sector_radar.ml.evaluation import evaluate_rule_vs_ml_shadow

    walk_forward = load_strict_json(walk_forward_path)
    truncated_predictions = copy.deepcopy(walk_forward)
    truncated_predictions["predictions"].pop()
    truncated_predictions["prediction_rows_sha256"] = canonical_sha256(
        truncated_predictions["predictions"]
    )
    with pytest.raises(ValueError, match="prediction universe"):
        evaluate_rule_vs_ml_shadow(
            truncated_predictions,
            dataset,
            baseline["records"],
            top_ks=(1,),
            baseline_strict_pit_eligible=True,
        )

    tampered_baseline = copy.deepcopy(baseline["records"])
    tampered_baseline[0]["quant_baseline_score_shadow"] += 1.0
    with pytest.raises(ValueError, match="verified archive baseline"):
        evaluate_rule_vs_ml_shadow(
            walk_forward,
            dataset,
            tampered_baseline,
            top_ks=(1,),
            baseline_strict_pit_eligible=True,
        )

    tampered_folds = copy.deepcopy(walk_forward)
    tampered_folds["split"]["folds"][0]["purged_dates"] = []
    with pytest.raises(ValueError, match="canonical split"):
        evaluate_rule_vs_ml_shadow(
            tampered_folds,
            dataset,
            baseline["records"],
            top_ks=(1,),
            baseline_strict_pit_eligible=True,
        )

    cycle_root = tmp_path / "cycle"
    cycle_model_dir = tmp_path / "cycle-model"
    cycle = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "run_ml_stock_training_cycle.py"),
            "--archive-root", str(archive_root),
            "--output-root", str(cycle_root),
            "--model-dir", str(cycle_model_dir),
            "--model-version", "stock_ranker_lgbm_v1_cycle_test",
            "--min-train-dates", "60",
            "--test-dates", "1",
            "--purge-dates", "5",
            "--n-estimators", "2",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert cycle.returncode == 0, cycle.stderr
    cycle_report = load_strict_json(cycle_root / "cycle_report.json")
    assert cycle_report["status"] == "trained_shadow"
    assert (cycle_model_dir / "registry.json").is_file()

    tampered_dataset = copy.deepcopy(dataset)
    tampered_dataset["feature_universe_records"][0]["features"]["momentum_1d"] += 0.01
    tampered_dataset["records"][0]["features"]["momentum_1d"] += 0.01
    dataset_core = {
        key: tampered_dataset[key]
        for key in (
            "schema_version",
            "feature_schema_version",
            "feature_schema_sha256",
            "feature_names",
            "label_definition",
            "max_label_horizon",
            "mode",
            "strict_pit_eligible",
            "pit_evidence_status",
            "eligible_for_oos_claim",
            "promotion_allowed",
            "fixture_only",
            "feature_universe_records",
            "evaluation_label_records",
            "records",
        )
    }
    tampered_dataset["dataset_sha256"] = canonical_sha256(dataset_core)
    with pytest.raises(ValueError, match="does not match the verified archive"):
        validate_training_dataset(tampered_dataset)


def test_readiness_accepts_only_sealed_sixty_day_pit_evidence(monkeypatch, tmp_path):
    from datetime import date, timedelta

    from theme_sector_radar.ml.contract import canonical_sha256
    from theme_sector_radar.ml.readiness import build_data_readiness_report

    dates = [
        (date(2026, 1, 1) + timedelta(days=index)).isoformat()
        for index in range(60)
    ]
    snapshots = [
        {
            "as_of_date": day,
            "candidate_count": 30,
            "stock_count": 30,
            "feature_buildable": True,
        }
        for day in dates
    ]
    evidence_core = {
        "schema_version": "ml-stock-pit-evidence-v1",
        "mode": "paper_shadow_research_only",
        "status": "verified",
        "verifier": "theme_sector_radar.ml.accumulation.verify_accumulation_archive",
        "snapshots": [
            {"as_of_date": day, "strict_pit_eligible": True}
            for day in dates
        ],
        "labels": [
            {"signal_date": day, "strict_pit_eligible": True}
            for day in dates
        ],
        "verified_training_dates": dates,
        "counts": {
            "candidate_snapshot_dates": 60,
            "prospective_candidate_snapshot_dates": 60,
            "mature_label_dates": 60,
            "strict_mature_label_dates": 60,
            "verified_training_dates": 60,
            "candidate_rows": 1800,
            "verified_training_rows": 1800,
        },
        "minimum_60_dates_satisfied": True,
        "strict_pit_eligible": True,
        "historical_candidate_universe_versioned": True,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
    }
    evidence = {
        **evidence_core,
        "evidence_sha256": canonical_sha256(evidence_core),
    }
    monkeypatch.setattr(
        "theme_sector_radar.ml.readiness.optional_ml_dependency_readiness",
        lambda: {
            "status": "ready",
            "backend": "lightgbm_lambdarank",
            "versions": {},
            "missing_packages": [],
            "import_errors": {},
            "reason": "optional_ml_dependencies_ready",
        },
    )

    with pytest.raises(ValueError, match="archive|verifier"):
        build_data_readiness_report(
            candidate_snapshots=snapshots,
            forward_stock_return_dates_by_horizon={horizon: dates for horizon in ("1d", "3d", "5d")},
            forward_excess_label_dates_by_horizon={horizon: dates for horizon in ("1d", "3d", "5d")},
            forward_label_coverage_by_horizon={"1d": 0.95, "3d": 0.95, "5d": 0.95},
            sector_history_date_count=120,
            historical_candidate_universe_versioned=True,
            source_manifest={"archive": "verified"},
            pit_evidence=evidence,
        )

    monkeypatch.setattr(
        "theme_sector_radar.ml.readiness.verify_accumulation_archive",
        lambda _root: evidence,
    )
    report = build_data_readiness_report(
        candidate_snapshots=snapshots,
        forward_stock_return_dates_by_horizon={horizon: dates for horizon in ("1d", "3d", "5d")},
        forward_excess_label_dates_by_horizon={horizon: dates for horizon in ("1d", "3d", "5d")},
        forward_label_coverage_by_horizon={"1d": 0.95, "3d": 0.95, "5d": 0.95},
        sector_history_date_count=120,
        historical_candidate_universe_versioned=True,
        source_manifest={
            "archive_root": str(tmp_path.resolve()),
            "pit_evidence_sha256": evidence["evidence_sha256"],
        },
        pit_evidence=evidence,
    )

    assert report["status"] == "ready"
    assert report["model_training_ready"] is True
    assert report["strict_pit_eligible"] is True
    assert report["counts"]["verified_training_dates"] == 60
    assert report["blocking_reasons"] == []

    self_attested_minimum = dict(evidence)
    self_attested_minimum["minimum_60_dates_satisfied"] = False
    self_attested_core = {
        key: value
        for key, value in self_attested_minimum.items()
        if key != "evidence_sha256"
    }
    self_attested_minimum["evidence_sha256"] = canonical_sha256(self_attested_core)
    blocked_self_attested = build_data_readiness_report(
        candidate_snapshots=snapshots,
        forward_stock_return_dates_by_horizon={
            horizon: dates for horizon in ("1d", "3d", "5d")
        },
        forward_excess_label_dates_by_horizon={
            horizon: dates for horizon in ("1d", "3d", "5d")
        },
        forward_label_coverage_by_horizon={"1d": 0.95, "3d": 0.95, "5d": 0.95},
        sector_history_date_count=120,
        historical_candidate_universe_versioned=True,
        source_manifest={
            "archive_root": str(tmp_path.resolve()),
            "pit_evidence_sha256": self_attested_minimum["evidence_sha256"],
        },
        pit_evidence=self_attested_minimum,
    )
    assert blocked_self_attested["model_training_ready"] is False
    assert "pit_evidence_minimum_history_not_verified" in blocked_self_attested[
        "blocking_reasons"
    ]

    tampered = dict(evidence)
    tampered["verified_training_dates"] = dates[:-1]
    with pytest.raises(ValueError, match="PIT evidence SHA mismatch"):
        build_data_readiness_report(
            candidate_snapshots=snapshots,
            forward_stock_return_dates_by_horizon={horizon: dates for horizon in ("1d", "3d", "5d")},
            forward_excess_label_dates_by_horizon={horizon: dates for horizon in ("1d", "3d", "5d")},
            forward_label_coverage_by_horizon={"1d": 0.95, "3d": 0.95, "5d": 0.95},
            sector_history_date_count=120,
            historical_candidate_universe_versioned=True,
            source_manifest={
                "archive_root": str(tmp_path.resolve()),
                "pit_evidence_sha256": evidence["evidence_sha256"],
            },
            pit_evidence=tampered,
        )


def test_archive_verifier_rejects_non_false_archive_safety_flags(tmp_path):
    from theme_sector_radar.ml.accumulation import verify_accumulation_archive
    from theme_sector_radar.reporting.strict_json import write_strict_json_atomic

    index = {
        "schema_version": "ml-stock-daily-archive-index-v1",
        "mode": "paper_shadow_research_only",
        "status": "active",
        "entry_count": 0,
        "chain_head_sha256": None,
        "entries": [],
        "promotion_allowed": False,
        "live_trading_allowed": True,
    }
    write_strict_json_atomic(tmp_path / "index.json", index)

    with pytest.raises(ValueError, match="live_trading_allowed"):
        verify_accumulation_archive(tmp_path)


def test_archive_missing_index_safety_fields_only_downgrades_strictness(
    tmp_path, capture_time
):
    from theme_sector_radar.ml.accumulation import (
        archive_daily_snapshot,
        archive_mature_label_snapshot,
        verify_accumulation_archive,
    )
    from theme_sector_radar.reporting.strict_json import (
        load_strict_json_with_sha256,
        write_strict_json_atomic,
    )

    as_of = "2026-07-16"
    calendar_dates = [
        as_of,
        "2026-07-17",
        "2026-07-20",
        "2026-07-21",
        "2026-07-22",
        "2026-07-23",
    ]
    report = _active_report(as_of)
    physical = _physical_daily_sources(
        tmp_path,
        as_of=as_of,
        report=report,
        calendar_dates=calendar_dates,
        generated_at="2026-07-16T16:30:00+08:00",
    )
    bars_by_code = {"000001": _bars(as_of), "000002": _bars(as_of)}
    capture_time(datetime(2026, 7, 16, 18, 0, tzinfo=timezone.utc))
    archive_daily_snapshot(
        archive_root=tmp_path,
        candidate_report=report,
        candidate_source=physical["candidate_source"],
        constituent_sources=physical["constituent_sources"],
        bars_by_code=bars_by_code,
        bars_source=_physical_daily_bars_source(
            tmp_path, as_of=as_of, bars_by_code=bars_by_code
        ),
        trading_calendar=physical["trading_calendar"],
    )
    prices = {
        code: [
            {"date": day, "close": 10.0 + index}
            for index, day in enumerate(calendar_dates)
        ]
        for code in bars_by_code
    }
    sectors = {
        "医疗服务": [
            {"date": day, "close": 100.0 + index}
            for index, day in enumerate(calendar_dates)
        ]
    }
    capture_time(datetime(2026, 7, 23, 18, 0, tzinfo=timezone.utc))
    archive_mature_label_snapshot(
        archive_root=tmp_path,
        signal_date=as_of,
        label_as_of_date="2026-07-23",
        stock_bars_by_code=prices,
        sector_bars_by_name=sectors,
        label_source=_physical_label_source(
            tmp_path,
            signal_date=as_of,
            label_as_of_date="2026-07-23",
            stock_prices=prices,
            sector_prices=sectors,
        ),
    )

    index_path = tmp_path / "index.json"
    index, _ = load_strict_json_with_sha256(index_path)
    index.pop("promotion_allowed")
    index.pop("live_trading_allowed")
    write_strict_json_atomic(index_path, index)

    evidence = verify_accumulation_archive(tmp_path)
    assert evidence["status"] == "verified"
    assert evidence["strict_pit_eligible"] is False
    assert evidence["counts"]["prospective_candidate_snapshot_dates"] == 0
    assert evidence["counts"]["verified_training_dates"] == 0


def test_multi_baseline_evaluation_quant_linkage_hybrid_and_ml_are_independent():
    from theme_sector_radar.ml.evaluation import evaluate_rule_vs_ml_shadow

    days = ("2026-07-16", "2026-07-17")
    predictions = []
    labels = []
    baselines = []
    inputs = {
        "000001": (90.0, None, "unavailable", 10.0),
        "000002": (80.0, 20.0, "ok", 20.0),
        "000003": (20.0, 90.0, "partial", 90.0),
        "000004": (50.0, 50.0, "ok", 100.0),
    }
    for day in days:
        for index, (code, (quant, linkage, status, ml)) in enumerate(inputs.items()):
            predictions.append(
                {
                    "as_of_date": day,
                    "stock_code": code,
                    "sector_name": "sector-a" if index < 2 else "sector-b",
                    "ml_quant_score_shadow": ml,
                    "prediction": ml + (100.0 if day == days[1] else 0.0),
                }
            )
            labels.append(
                {
                    "as_of_date": day,
                    "stock_code": code,
                    "sector_name": "sector-a" if index < 2 else "sector-b",
                    "labels": {
                        "future_return_5d": 0.01 * (index + 1),
                        "future_excess_return_5d": 0.005 * (index + 1),
                    },
                }
            )
            baselines.append(
                {
                    "as_of_date": day,
                    "stock_code": code,
                    "sector_name": "sector-a" if index < 2 else "sector-b",
                    "quant_baseline_score_shadow": quant,
                    "linkage_v2_baseline_score_shadow": linkage,
                    "linkage_v2_status": status,
                    "rule_eligible": True,
                }
            )

    report = evaluate_rule_vs_ml_shadow(
        {
            "status": "ok",
            "fixture_only": False,
            "strict_pit_eligible": False,
            "predictions": predictions,
        },
        {
            "fixture_only": False,
            "strict_pit_eligible": False,
            "evaluation_label_records": labels,
        },
        baselines,
        top_ks=(2,),
        horizons=(5,),
        hybrid_quant_weight=0.65,
        hybrid_linkage_weight=0.35,
        hybrid_partial_linkage_weight=0.20,
    )

    assert {row["strategy"] for row in report["results"]} == {
        "A_quant",
        "B_linkage_v2",
        "C_hybrid",
        "D_ml",
    }
    first = next(row for row in report["ranking_audit"] if row["as_of_date"] == days[0])
    assert first["selections"]["A_quant"] == ["000001", "000002"]
    assert first["selections"]["B_linkage_v2"] == ["000003", "000004"]
    assert first["selections"]["D_ml"] == ["000004", "000003"]
    assert first["hybrid_rows"]["000001"] == {
        "score": 100.0,
        "confidence": "low",
        "effective_quant_weight": 1.0,
        "effective_linkage_weight": 0.0,
        "degradation_reason": "linkage_v2_unavailable_quant_only",
    }
    assert first["hybrid_rows"]["000003"]["effective_linkage_weight"] == 0.2
    assert report["baseline_configuration"]["hybrid"] == {
        "quant_weight": 0.65,
        "linkage_v2_weight": 0.35,
        "partial_linkage_v2_weight": 0.2,
        "method": "same_day_percentile_weighted",
    }
    assert report["prediction_drift"]["status"] == "ok"
    assert report["prediction_drift"]["method"] == "raw_prediction_distribution_shift"
    assert report["prediction_drift"]["mean_shift"] == 100.0
    assert report["promotion_allowed"] is False
