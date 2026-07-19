import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

import scripts.audit_timing_nonstationary_profit_exit as profit_audit
from scripts.audit_timing_nonstationary_profit_exit import _long_history_veto, audit_nonstationary_profit_records
from theme_sector_radar.data.trading_calendar import (
    build_trading_calendar_report,
    load_trading_calendar,
)
from theme_sector_radar.timing.candidate_source_identity import validate_records_candidate_source_identity


@pytest.fixture(autouse=True)
def _validated_file_boundaries(monkeypatch):
    production_validate_paper_records = profit_audit.validate_paper_records_report
    monkeypatch.setattr(
        profit_audit,
        "validate_paper_records_report",
        lambda report, *, context, **kwargs: production_validate_paper_records(
            report,
            context=context,
            require_durable_entry_bars_source=False,
        ),
    )
    monkeypatch.setattr(
        profit_audit,
        "revalidate_records_candidate_source_identity",
        lambda identity, *, candidate_root, source_root, timeframe, context, **kwargs: validate_records_candidate_source_identity(
            identity,
            candidate_root=candidate_root,
            source_root=source_root,
            timeframe=timeframe,
            context=context,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        profit_audit,
        "validate_causal_paper_records",
        lambda records, **kwargs: {
            "record_count": len(records),
            "valid_record_count": sum(1 for row in records if row.get("causal_entry_valid")),
            "invalid_record_count": sum(1 for row in records if not row.get("causal_entry_valid")),
        },
        raising=False,
    )
    monkeypatch.setattr(
        profit_audit,
        "validate_paper_record_cohort",
        lambda records, **kwargs: {
            "status": "validated",
            "expected_record_count": len(records),
            "actual_record_count": len(records),
            "record_key_manifest_sha256": "b" * 64,
        },
        raising=False,
    )
    monkeypatch.setattr(
        profit_audit,
        "revalidate_records_selection_source_identity",
        lambda identity, **kwargs: dict(identity or {"status": "validated"}),
        raising=False,
    )


def _record(day, fixed_exit, factor_exit, forward):
    return {
        "as_of": day,
        "forward_return_pct": forward,
        "paper_exit_candidates": {
            "paper_fixed_exit_baseline": {
                "triggered": True,
                "fill_available": True,
                "simulated_exit_return_pct": fixed_exit,
            },
            "paper_take_profit_protect_candidate": {
                "triggered": True,
                "fill_available": True,
                "simulated_exit_return_pct": factor_exit,
            },
        },
    }


def test_profit_records_loader_requires_durable_manifest(monkeypatch, tmp_path):
    path = tmp_path / "records.json"
    path.write_text('{"records": []}', encoding="utf-8")

    def capture(_report, *, context, require_durable_entry_bars_source):
        assert context.startswith("profit records report")
        assert require_durable_entry_bars_source is True
        raise RuntimeError("durable flag captured")

    monkeypatch.setattr(profit_audit, "validate_paper_records_report", capture)
    with pytest.raises(RuntimeError, match="durable flag captured"):
        profit_audit._load_records(path)


def _calendar_path(tmp_path, dates, *, records_path=None):
    path = tmp_path / "calendar.json"
    path.write_text(
        json.dumps(
            build_trading_calendar_report(
                dates,
                source="unit-exchange-calendar",
                requested_start=min(dates),
                requested_end="2026-07-13",
            )
        ),
        encoding="utf-8",
    )
    if records_path is not None:
        records_report = json.loads(records_path.read_text(encoding="utf-8"))
        records_report["trading_calendar"] = load_trading_calendar(path, as_of="2026-07-13")
        records_path.write_text(json.dumps(records_report), encoding="utf-8")
    return path


def _observed_tail_dates(as_of="2026-07-13"):
    current = date.fromisoformat(as_of)
    dates = []
    while len(dates) < 20:
        if current.weekday() < 5:
            dates.append(current.isoformat())
        current -= timedelta(days=1)
    return sorted(dates)


def _records_report(
    *,
    snapshot_label="test",
    timeframe="1m",
    records=None,
    parameters=None,
    paper_only=True,
):
    normalized_records = [
        {
            "paper_trading_only": paper_only,
            "no_execution_signals": paper_only,
            "does_not_modify_official_scores": paper_only,
            **record,
        }
        for record in (records or [])
    ]
    normalized_parameters = dict(parameters or {})
    normalized_parameters.setdefault("candidate_root", "test-candidates")
    normalized_parameters.setdefault("candidate_source_root", "test-source-candidates")
    normalized_parameters.setdefault("selection_validation_root", None)
    normalized_parameters.setdefault("start", None)
    normalized_parameters.setdefault("end", "2026-07-13")
    normalized_parameters.setdefault("version_ids", list(profit_audit.PROFIT_ENTRY_VERSION_IDS))
    normalized_parameters.setdefault("concentration_threshold", 2)
    normalized_parameters.setdefault("factor_exit_peak_giveback_pct", 2.0)
    normalized_parameters.setdefault(
        "candidate_source_identity",
        {
            "status": "validated",
            "candidate_root": str(normalized_parameters["candidate_root"]),
            "source_root": str(normalized_parameters["candidate_source_root"]),
            "bar_interval": timeframe,
            "bar_source": {
                "1m": "complete_1m_session",
                "5m": "aggregated_from_complete_1m_session",
            }[timeframe],
            "manifest_sha256": "a" * 64,
            "document_dates": _observed_tail_dates(),
            "complete_candidate_dates": _observed_tail_dates(),
        },
    )
    return {
        "as_of": "2026-07-13",
        "snapshot_label": snapshot_label,
        "bar_interval": timeframe,
        "bar_source": {
            "1m": "complete_1m_session",
            "5m": "aggregated_from_complete_1m_session",
        }[timeframe],
        "entry_bars_source_identity": {
            "status": "validated",
            "source_kind": "in_memory_test_fixture",
            "sha256": "b" * 64,
        },
        "paper_trading_only": paper_only,
        "no_execution_signals": paper_only,
        "does_not_modify_official_scores": paper_only,
        "parameters": normalized_parameters,
        "records": normalized_records,
    }


def _long_history_report(
    *,
    strategy_linked=True,
    entry_model="next_trading_session_first_bar_open",
    version_ids=None,
    records=None,
    parameters=None,
    trading_calendar=None,
):
    report_parameters = {"version_ids": list(version_ids or profit_audit.PROFIT_ENTRY_VERSION_IDS)}
    report_parameters.update(parameters or {})
    normalized_records = [
        {
            "paper_trading_only": True,
            "no_execution_signals": True,
            "does_not_modify_official_scores": True,
            **record,
        }
        for record in (records or [])
    ]
    return {
        "as_of": "2025-12-31",
        "snapshot_label": "strategy-linked-long-history",
        "bar_interval": "1m",
        "bar_source": "complete_1m_session",
        "entry_bars_source_identity": {
            "status": "validated",
            "source_kind": "in_memory_test_fixture",
            "sha256": "b" * 64,
        },
        "entry_model": entry_model,
        "strategy_linked_entry_paths": strategy_linked,
        "trading_calendar": trading_calendar,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
        "parameters": report_parameters,
        "records": normalized_records,
    }


def _source_bindings(records_path):
    data = json.loads(records_path.read_text(encoding="utf-8"))
    parameters = data["parameters"]
    selection_root = parameters.get("selection_validation_root")
    return {
        "candidate_root": Path(parameters["candidate_root"]),
        "candidate_source_root": Path(parameters["candidate_source_root"]),
        "selection_validation_root": Path(selection_root) if selection_root else None,
    }


def test_profit_records_loader_binds_sha_to_parsed_bytes(tmp_path, monkeypatch):
    path = tmp_path / "records.json"
    first_bytes = json.dumps(_records_report()).encode("utf-8")
    path.write_bytes(first_bytes)
    expected_sha256 = hashlib.sha256(first_bytes).hexdigest()
    original_read_bytes = Path.read_bytes

    def read_then_replace(self):
        payload = original_read_bytes(self)
        if self == path:
            self.write_text("{}", encoding="utf-8")
        return payload

    monkeypatch.setattr(Path, "read_bytes", read_then_replace)

    records, _parameters, identity, actual_sha256 = profit_audit._load_records(path)

    assert records == []
    assert identity["as_of"] == "2026-07-13"
    assert actual_sha256 == expected_sha256


def test_nonstationary_profit_audit_compares_recent_and_holdout_windows():
    weekdays = []
    current = date(2026, 1, 1)
    while len(weekdays) < 100:
        if current.weekday() < 5:
            weekdays.append(current.isoformat())
        current += timedelta(days=1)
    records = [
        _record(day, 4.0, 5.0, -2.0 if index % 5 == 0 else 2.0)
        for index, day in enumerate(weekdays)
    ]

    report = audit_nonstationary_profit_records(records, holdout_days=20)

    assert report["windows"]["holdout"]["date_count"] == 20
    factor = report["candidates"]["paper_take_profit_protect_candidate"]
    assert factor["by_window"]["recent_60"]["trigger_count"] == 60
    assert factor["by_window"]["recent_60"]["avg_saved_vs_forward_pct"] > 0
    assert factor["paired_vs_fixed_by_window"]["recent_60"]["avg_paired_delta_pct"] == 1.0
    assert report["paper_trading_only"] is True


def test_nonstationary_profit_audit_reports_candidate_document_date_coverage():
    dates = [f"2026-06-{day:02d}" for day in range(1, 21)]

    report = audit_nonstationary_profit_records(
        [],
        as_of=dates[-1],
        calendar_dates=dates,
        source_document_dates=dates[:-2],
        complete_candidate_dates=dates[-5:],
        holdout_days=20,
    )

    holdout = report["windows"]["holdout"]
    assert holdout["source_document_date_count"] == 18
    assert holdout["complete_candidate_date_count"] == 5
    assert holdout["complete_candidate_date_coverage_rate"] == 0.25
    assert holdout["candidate_date_coverage_status"] == "insufficient"


def test_profit_audit_pairs_policies_on_same_deduplicated_entries():
    records = [
        {
            "as_of": "2026-01-02",
            "code": "000001",
            "forward_return_pct": 2.0,
            "path_stats": {"close_return_pct": 2.0},
            "paper_exit_candidates": {
                "paper_fixed_exit_baseline": {"triggered": True, "fill_available": True, "simulated_exit_return_pct": 4.0},
                "paper_take_profit_protect_candidate": {"triggered": False, "fill_available": False, "simulated_exit_return_pct": None},
            },
        },
        {
            "as_of": "2026-01-05",
            "code": "000002",
            "timing_version_id": "v31",
            "forward_return_pct": -2.0,
            "path_stats": {"close_return_pct": -2.0},
            "paper_exit_candidates": {
                "paper_fixed_exit_baseline": {"triggered": False, "fill_available": False, "simulated_exit_return_pct": None},
                "paper_take_profit_protect_candidate": {"triggered": True, "fill_available": True, "simulated_exit_return_pct": 5.0},
            },
        },
        {
            "as_of": "2026-01-05",
            "code": "000002",
            "timing_version_id": "v32",
            "forward_return_pct": -2.0,
            "path_stats": {"close_return_pct": -2.0},
            "paper_exit_candidates": {
                "paper_fixed_exit_baseline": {"triggered": False, "fill_available": False, "simulated_exit_return_pct": None},
                "paper_take_profit_protect_candidate": {"triggered": True, "fill_available": True, "simulated_exit_return_pct": 5.0},
            },
        },
    ]

    report = audit_nonstationary_profit_records(
        records,
        applied_giveback_pct=2.0,
        round_trip_cost_pct=0.1,
        holdout_days=0,
        recent_windows=(2,),
    )
    paired = report["candidates"]["paper_take_profit_protect_candidate"]["paired_vs_fixed_by_window"]["recent_2"]

    assert paired["paired_record_count"] == 2
    assert paired["deduplicated_record_count"] == 2
    assert paired["avg_paired_delta_pct"] == 2.5
    assert report["parameters"]["round_trip_cost_pct"] == 0.1


def test_profit_audit_rejects_conflicting_duplicate_entry_policies():
    first = _record("2026-01-02", 4.0, 5.0, 2.0)
    first.update(
        signal_date="2026-01-02",
        entry_date="2026-01-05",
        code="000001",
        entry_bars_sha256="a" * 64,
        execution_assumptions={"bar_interval": "1m"},
    )
    second = json.loads(json.dumps(first))
    second["paper_exit_candidates"]["paper_take_profit_protect_candidate"]["simulated_exit_return_pct"] = 1.0

    with pytest.raises(ValueError, match="duplicate entry policy/path conflict"):
        audit_nonstationary_profit_records(
            [first, second],
            applied_giveback_pct=2.0,
            holdout_days=0,
            recent_windows=(1,),
        )


def test_profit_audit_rejects_same_entry_with_different_path_hashes():
    first = _record("2026-01-02", 4.0, 5.0, 2.0)
    first.update(
        signal_date="2026-01-02",
        entry_date="2026-01-05",
        code="000001",
        timing_version_id="v31",
        entry_bars_sha256="a" * 64,
        execution_assumptions={"bar_interval": "1m"},
    )
    second = json.loads(json.dumps(first))
    second["timing_version_id"] = "v32"
    second["entry_bars_sha256"] = "b" * 64

    with pytest.raises(ValueError, match="duplicate entry policy/path conflict"):
        audit_nonstationary_profit_records(
            [first, second],
            applied_giveback_pct=2.0,
            holdout_days=0,
            recent_windows=(1,),
        )


def test_profit_audit_rejects_undeclared_giveback_threshold():
    with pytest.raises(ValueError, match="declared giveback"):
        audit_nonstationary_profit_records([], applied_giveback_pct=2.5)


def test_profit_policy_hold_uses_only_causal_entry_session_close_return():
    records = [
        {
            "as_of": "2026-01-02",
            "code": "000001",
            "forward_return_pct": 10.0,
            "path_stats": {"close_return_pct": 10.0},
            "paper_exit_candidates": {
                "paper_fixed_exit_baseline": {"triggered": True, "fill_available": True, "simulated_exit_return_pct": 5.0},
                "paper_take_profit_protect_candidate": {"triggered": False, "fill_available": False, "simulated_exit_return_pct": None},
            },
        }
    ]

    report = audit_nonstationary_profit_records(
        records,
        applied_giveback_pct=2.0,
        round_trip_cost_pct=0.0,
        holdout_days=0,
        recent_windows=(1,),
    )
    paired = report["candidates"]["paper_take_profit_protect_candidate"]["paired_vs_fixed_by_window"]["recent_1"]

    assert paired["avg_candidate_policy_return_pct"] == 10.0
    assert paired["avg_fixed_policy_return_pct"] == 5.0
    assert paired["avg_paired_delta_pct"] == 5.0


def test_profit_file_audit_uses_only_labeled_trading_dates(monkeypatch, tmp_path):
    tail_dates = _observed_tail_dates()
    candidate_root = tmp_path / "candidates"
    candidate_root.mkdir()
    calendar_samples = [
        {"_sample_date": tail_dates[0], "forward_return_pct": 1.0},
        {"_sample_date": "2026-07-11", "forward_return_pct": None},
        {"_sample_date": "2026-07-12", "forward_return_pct": None},
        {"_sample_date": tail_dates[-1], "forward_return_pct": -1.0},
    ]
    monkeypatch.setattr(profit_audit, "_load_samples", lambda *args: calendar_samples)
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                parameters={"candidate_root": str(candidate_root), "factor_exit_peak_giveback_pct": 2.0},
                records=[
                    _record(tail_dates[0], 1.0, 2.0, 1.0),
                    _record(tail_dates[-1], 1.0, 2.0, -1.0),
                ],
            )
        ),
        encoding="utf-8",
    )

    result = profit_audit.audit_nonstationary_profit_exit(
        records_path=records_path,
        **_source_bindings(records_path),
        trading_calendar_path=_calendar_path(
            tmp_path, tail_dates, records_path=records_path
        ),
        output_dir=tmp_path / "output",
        as_of="2026-07-13",
        snapshot_label="test",
        timeframe="1m",
        holdout_days=20,
        min_labeled_triggers=1,
    )

    assert result["report"]["windows"]["all_history"]["dates"] == tail_dates
    assert "2026-07-11" not in result["report"]["windows"]["all_history"]["dates"]
    assert "2026-07-12" not in result["report"]["windows"]["all_history"]["dates"]
    assert result["report"]["candidate_source"]["candidate_root"] == str(candidate_root)


def test_profit_file_audit_rejects_relabelled_source_snapshot(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                snapshot_label="original",
                parameters={"factor_exit_peak_giveback_pct": 2.0},
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="snapshot"):
        profit_audit.audit_nonstationary_profit_exit(
            records_path=records_path,
            **_source_bindings(records_path),
            trading_calendar_path=_calendar_path(
                tmp_path,
                ["2026-07-10", "2026-07-13"],
                records_path=records_path,
            ),
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            snapshot_label="renamed",
            timeframe="1m",
            applied_giveback_pct=2.0,
        )


def test_profit_file_audit_rejects_timeframe_not_bound_to_source_bars(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(_records_report(parameters={"factor_exit_peak_giveback_pct": 2.0})),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="timeframe"):
        profit_audit.audit_nonstationary_profit_exit(
            records_path=records_path,
            **_source_bindings(records_path),
            trading_calendar_path=_calendar_path(
                tmp_path,
                ["2026-07-10", "2026-07-13"],
                records_path=records_path,
            ),
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            snapshot_label="test",
            timeframe="5m",
            applied_giveback_pct=2.0,
        )


def test_profit_file_audit_rejects_candidate_identity_from_another_root(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                parameters={
                    "candidate_root": str(tmp_path / "trusted-candidates"),
                    "candidate_source_identity": {
                        "status": "validated",
                        "candidate_root": str(tmp_path / "different-candidates"),
                        "bar_interval": "1m",
                        "bar_source": "complete_1m_session",
                        "manifest_sha256": "a" * 64,
                    },
                    "factor_exit_peak_giveback_pct": 2.0,
                }
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="candidate root"):
        profit_audit.audit_nonstationary_profit_exit(
            records_path=records_path,
            **_source_bindings(records_path),
            trading_calendar_path=_calendar_path(
                tmp_path,
                ["2026-07-10", "2026-07-13"],
                records_path=records_path,
            ),
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            snapshot_label="test",
            timeframe="1m",
            applied_giveback_pct=2.0,
        )


def test_profit_file_audit_binds_candidate_root_from_caller(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                parameters={
                    "candidate_root": str(tmp_path / "source-candidates"),
                    "selection_validation_root": str(tmp_path / "source-selection"),
                    "factor_exit_peak_giveback_pct": 2.0,
                    "version_ids": list(profit_audit.PROFIT_ENTRY_VERSION_IDS),
                }
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="caller candidate root"):
        profit_audit.audit_nonstationary_profit_exit(
            records_path=records_path,
            candidate_root=tmp_path / "different-candidates",
            candidate_source_root=tmp_path / "source-candidates",
            selection_validation_root=tmp_path / "source-selection",
            trading_calendar_path=_calendar_path(
                tmp_path,
                ["2026-07-10", "2026-07-13"],
                records_path=records_path,
            ),
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            snapshot_label="test",
            timeframe="1m",
            applied_giveback_pct=2.0,
        )


def test_profit_file_audit_revalidates_current_candidate_root(monkeypatch, tmp_path):
    monkeypatch.setattr(
        profit_audit,
        "revalidate_records_candidate_source_identity",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("current root manifest mismatch")),
    )
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                parameters={"candidate_root": str(tmp_path / "candidates"), "factor_exit_peak_giveback_pct": 2.0},
                records=[_record("2026-07-10", 1.0, 2.0, 1.0)],
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="current root manifest"):
        profit_audit.audit_nonstationary_profit_exit(
            records_path=records_path,
            **_source_bindings(records_path),
            trading_calendar_path=_calendar_path(
                tmp_path,
                ["2026-07-10", "2026-07-13"],
                records_path=records_path,
            ),
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            snapshot_label="test",
            timeframe="1m",
            applied_giveback_pct=2.0,
        )


def test_profit_file_audit_revalidates_current_selection_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(
        profit_audit,
        "revalidate_records_selection_source_identity",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("selection source manifest SHA mismatch")),
        raising=False,
    )
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                parameters={"candidate_root": str(tmp_path / "candidates")},
                records=[_record("2026-07-10", 1.0, 2.0, 1.0)],
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="selection source manifest SHA mismatch"):
        profit_audit.audit_nonstationary_profit_exit(
            records_path=records_path,
            **_source_bindings(records_path),
            trading_calendar_path=_calendar_path(
                tmp_path,
                ["2026-07-10", "2026-07-13"],
                records_path=records_path,
            ),
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            snapshot_label="test",
            timeframe="1m",
            applied_giveback_pct=2.0,
        )


def test_profit_file_audit_rejects_non_paper_source(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                parameters={"factor_exit_peak_giveback_pct": 2.0},
                paper_only=False,
                records=[_record("2026-07-13", 1.0, 2.0, 0.0)],
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="paper-only"):
        profit_audit.audit_nonstationary_profit_exit(
            records_path=records_path,
            **_source_bindings(records_path),
            trading_calendar_path=_calendar_path(
                tmp_path, ["2026-07-13"], records_path=records_path
            ),
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            snapshot_label="test",
            timeframe="1m",
        )


def test_profit_file_audit_rejects_long_history_without_strategy_linkage(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                parameters={"factor_exit_peak_giveback_pct": 2.0},
                records=[_record("2026-07-13", 1.0, 2.0, 0.0)],
            )
        ),
        encoding="utf-8",
    )
    long_history_path = tmp_path / "long-history.json"
    long_history_path.write_text(
        json.dumps(_long_history_report(strategy_linked=False)),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="strategy-linked"):
        profit_audit.audit_nonstationary_profit_exit(
            records_path=records_path,
            **_source_bindings(records_path),
            trading_calendar_path=_calendar_path(
                tmp_path, ["2026-07-13"], records_path=records_path
            ),
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            snapshot_label="test",
            timeframe="1m",
            long_history_records_path=long_history_path,
        )


def test_profit_file_audit_rejects_long_history_entry_model_mismatch(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                parameters={"factor_exit_peak_giveback_pct": 2.0},
                records=[_record("2026-07-13", 1.0, 2.0, 0.0)],
            )
        ),
        encoding="utf-8",
    )
    long_history_path = tmp_path / "long-history.json"
    long_history_path.write_text(
        json.dumps(_long_history_report(entry_model="signal_session_first_bar_open")),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="entry model"):
        profit_audit.audit_nonstationary_profit_exit(
            records_path=records_path,
            **_source_bindings(records_path),
            trading_calendar_path=_calendar_path(
                tmp_path, ["2026-07-13"], records_path=records_path
            ),
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            snapshot_label="test",
            timeframe="1m",
            long_history_records_path=long_history_path,
        )


def test_profit_file_audit_rejects_long_history_strategy_version_mismatch(tmp_path):
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                parameters={
                    "factor_exit_peak_giveback_pct": 2.0,
                    "version_ids": ["v31", "v32"],
                },
                records=[_record("2026-07-13", 1.0, 2.0, 0.0)],
            )
        ),
        encoding="utf-8",
    )
    long_history_path = tmp_path / "long-history.json"
    long_history_path.write_text(
        json.dumps(_long_history_report(version_ids=["v29"])),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="strategy versions"):
        profit_audit.audit_nonstationary_profit_exit(
            records_path=records_path,
            **_source_bindings(records_path),
            trading_calendar_path=_calendar_path(
                tmp_path, ["2026-07-13"], records_path=records_path
            ),
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            snapshot_label="test",
            timeframe="1m",
            long_history_records_path=long_history_path,
        )


def test_profit_file_audit_binds_valid_long_history_source_hash(tmp_path, monkeypatch):
    tail_dates = _observed_tail_dates()
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                parameters={"factor_exit_peak_giveback_pct": 2.0},
                records=[_record(tail_dates[0], 1.0, 2.0, 0.0)],
            )
        ),
        encoding="utf-8",
    )
    long_history_path = tmp_path / "long-history.json"
    long_history_path.write_text(json.dumps(_long_history_report()), encoding="utf-8")
    expected_sha256 = hashlib.sha256(long_history_path.read_bytes()).hexdigest()
    monkeypatch.setattr(
        profit_audit,
        "_sha256",
        lambda *_args, **_kwargs: pytest.fail("long-history path must not be reread for SHA"),
        raising=False,
    )

    result = profit_audit.audit_nonstationary_profit_exit(
        records_path=records_path,
        **_source_bindings(records_path),
        trading_calendar_path=_calendar_path(
            tmp_path, tail_dates, records_path=records_path
        ),
        output_dir=tmp_path / "output",
        as_of="2026-07-13",
        snapshot_label="test",
        timeframe="1m",
        long_history_records_path=long_history_path,
    )

    source = result["report"]["long_history_source"]
    assert source["status"] == "not_evaluated"
    assert source["eligible_as_long_history_veto"] is False
    assert source["reason"] == "causal_records_or_external_anchors_unavailable"
    assert source["entry_model"] == "next_trading_session_first_bar_open"
    assert source["sha256"] == expected_sha256


def test_profit_long_history_requires_caller_bound_calendar_roots_and_cohort(monkeypatch, tmp_path):
    tail_dates = _observed_tail_dates()
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                parameters={"factor_exit_peak_giveback_pct": 2.0},
                records=[_record(tail_dates[0], 1.0, 2.0, 0.0)],
            )
        ),
        encoding="utf-8",
    )
    long_root = tmp_path / "long"
    long_root.mkdir()
    long_candidate_root = long_root / "candidates"
    long_candidate_source_root = long_root / "source"
    long_selection_root = long_root / "selection"
    for path in (long_candidate_root, long_candidate_source_root, long_selection_root):
        path.mkdir()
    long_calendar_path = _calendar_path(long_root, ["2025-12-30", "2025-12-31"])
    long_calendar_identity = {
        "path": str(long_calendar_path),
        "sha256": hashlib.sha256(long_calendar_path.read_bytes()).hexdigest(),
    }
    long_parameters = {
        "candidate_root": str(long_candidate_root),
        "candidate_source_root": str(long_candidate_source_root),
        "selection_validation_root": str(long_selection_root),
        "start": "2025-12-30",
        "end": "2025-12-31",
        "version_ids": list(profit_audit.PROFIT_ENTRY_VERSION_IDS),
        "concentration_threshold": 2,
        "factor_exit_peak_giveback_pct": 2.0,
        "candidate_source_identity": {
            "status": "validated",
            "candidate_root": str(long_candidate_root),
            "source_root": str(long_candidate_source_root),
            "bar_interval": "1m",
            "bar_source": "complete_1m_session",
            "manifest_sha256": "c" * 64,
        },
    }
    long_record = _record("2025-12-30", 1.0, 2.0, 0.0)
    long_record["causal_entry_valid"] = True
    long_history_path = long_root / "long-history.json"
    long_history_path.write_text(
        json.dumps(
            _long_history_report(
                records=[long_record],
                parameters=long_parameters,
                trading_calendar=long_calendar_identity,
            )
        ),
        encoding="utf-8",
    )
    cohort_calls = []

    def validate_cohort(records, **kwargs):
        cohort_calls.append(kwargs)
        return {
            "status": "validated",
            "expected_record_count": len(records),
            "actual_record_count": len(records),
            "record_key_manifest_sha256": "d" * 64,
        }

    monkeypatch.setattr(profit_audit, "validate_paper_record_cohort", validate_cohort)

    result = profit_audit.audit_nonstationary_profit_exit(
        records_path=records_path,
        **_source_bindings(records_path),
        trading_calendar_path=_calendar_path(
            tmp_path, tail_dates, records_path=records_path
        ),
        output_dir=tmp_path / "output",
        as_of="2026-07-13",
        snapshot_label="test",
        timeframe="1m",
        long_history_records_path=long_history_path,
        long_history_trading_calendar_path=long_calendar_path,
        long_history_candidate_root=long_candidate_root,
        long_history_candidate_source_root=long_candidate_source_root,
        long_history_selection_validation_root=long_selection_root,
    )

    source = result["report"]["long_history_source"]
    assert source["status"] == "validated_strategy_linked"
    assert source["eligible_as_long_history_veto"] is True
    assert source["trading_calendar"]["sha256"] == long_calendar_identity["sha256"]
    assert source["record_cohort_identity"]["status"] == "validated"
    assert cohort_calls[0]["version_ids"] == list(profit_audit.PROFIT_ENTRY_VERSION_IDS)
    assert cohort_calls[0]["snapshot_label"] == "strategy-linked-long-history"


def test_profit_long_history_rejects_self_reported_calendar_sha_without_external_match(tmp_path):
    tail_dates = _observed_tail_dates()
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _records_report(
                parameters={"factor_exit_peak_giveback_pct": 2.0},
                records=[_record(tail_dates[0], 1.0, 2.0, 0.0)],
            )
        ),
        encoding="utf-8",
    )
    long_root = tmp_path / "long"
    long_root.mkdir()
    roots = [long_root / name for name in ("candidates", "source", "selection")]
    for path in roots:
        path.mkdir()
    long_calendar_path = _calendar_path(long_root, ["2025-12-30", "2025-12-31"])
    long_parameters = {
        "candidate_root": str(roots[0]),
        "candidate_source_root": str(roots[1]),
        "selection_validation_root": str(roots[2]),
        "start": "2025-12-30",
        "end": "2025-12-31",
        "version_ids": list(profit_audit.PROFIT_ENTRY_VERSION_IDS),
        "concentration_threshold": 2,
        "factor_exit_peak_giveback_pct": 2.0,
        "candidate_source_identity": {
            "status": "validated",
            "candidate_root": str(roots[0]),
            "source_root": str(roots[1]),
            "bar_interval": "1m",
            "bar_source": "complete_1m_session",
            "manifest_sha256": "c" * 64,
        },
    }
    long_history_path = long_root / "long-history.json"
    long_history_path.write_text(
        json.dumps(
            _long_history_report(
                records=[{"causal_entry_valid": True}],
                parameters=long_parameters,
                trading_calendar={"path": str(long_calendar_path), "sha256": "f" * 64},
            )
        ),
        encoding="utf-8",
    )

    result = profit_audit.audit_nonstationary_profit_exit(
        records_path=records_path,
        **_source_bindings(records_path),
        trading_calendar_path=_calendar_path(
            tmp_path, tail_dates, records_path=records_path
        ),
        output_dir=tmp_path / "output",
        as_of="2026-07-13",
        snapshot_label="test",
        timeframe="1m",
        long_history_records_path=long_history_path,
        long_history_trading_calendar_path=long_calendar_path,
        long_history_candidate_root=roots[0],
        long_history_candidate_source_root=roots[1],
        long_history_selection_validation_root=roots[2],
    )

    source = result["report"]["long_history_source"]
    assert source["status"] == "not_evaluated"
    assert source["eligible_as_long_history_veto"] is False
    assert source["reason"] == "external_anchor_validation_failed"


def test_profit_regime_and_walk_forward_use_paired_fixed_policy_counterfactual():
    records = []
    start = date(2026, 1, 1)
    current = start
    while len(records) < 18:
        if current.weekday() < 5:
            row = _record(current.isoformat(), 6.0, 5.0, -5.0)
            row["code"] = f"{len(records):06d}"
            row["market_regime"] = "strong"
            row["path_stats"] = {"close_return_pct": -5.0}
            records.append(row)
        current += timedelta(days=1)

    report = audit_nonstationary_profit_records(
        records,
        holdout_days=0,
        recent_windows=(18, 120),
        fold_count=3,
        min_labeled_triggers=5,
        applied_giveback_pct=2.0,
        round_trip_cost_pct=0.1,
    )
    candidate = report["candidates"]["paper_take_profit_protect_candidate"]

    assert candidate["by_regime"]["strong"]["avg_paired_delta_pct"] == -1.0
    assert candidate["fold_stability"]["valid_fold_count"] == 3
    assert all(fold["avg_paired_delta_pct"] == -1.0 for fold in candidate["fold_stability"]["folds"])


def test_profit_long_history_veto_uses_same_entry_fixed_policy_pairs():
    records = []
    for index in range(6):
        row = _record(f"2026-01-{index + 5:02d}", 6.0, 5.0, -5.0)
        row["code"] = f"{index:06d}"
        row["path_stats"] = {"close_return_pct": -5.0}
        records.append(row)

    result = _long_history_veto(
        records,
        "paper_take_profit_protect_candidate",
        fold_count=3,
        min_labeled_triggers=5,
        tail_loss_pct=-5.0,
        round_trip_cost_pct=0.1,
    )

    assert result["status"] == "ok"
    assert result["metrics_complete"] is True
    assert result["paired"]["avg_paired_delta_pct"] == -1.0
    assert result["vetoed"] is True


def test_profit_same_entry_identity_includes_entry_date_cadence_and_path_hash():
    first = _record("2026-07-10", 1.0, 2.0, 0.0)
    second = _record("2026-07-10", 1.0, 3.0, 0.0)
    for index, row in enumerate((first, second), start=1):
        row.update(
            {
                "code": "600001",
                "entry_date": f"2026-07-{10 + index:02d}",
                "entry_bars_sha256": str(index) * 64,
                "execution_assumptions": {"bar_interval": "1m"},
            }
        )

    report = audit_nonstationary_profit_records(
        [first, second],
        calendar_dates=["2026-07-10"],
        holdout_days=0,
        recent_windows=(1,),
        min_labeled_triggers=1,
    )

    paired = report["candidates"]["paper_take_profit_protect_candidate"]["paired_vs_fixed_by_window"]["all_history"]
    assert paired["deduplicated_record_count"] == 2
    assert paired["paired_record_count"] == 2


def test_profit_same_entry_conflicting_policy_fails_closed():
    first = _record("2026-07-10", 1.0, 2.0, 0.0)
    second = _record("2026-07-10", 1.0, 3.0, 0.0)
    for row in (first, second):
        row.update(
            {
                "code": "600001",
                "entry_date": "2026-07-13",
                "entry_bars_sha256": "a" * 64,
                "execution_assumptions": {"bar_interval": "1m"},
            }
        )

    with pytest.raises(ValueError, match="conflict"):
        audit_nonstationary_profit_records(
            [first, second],
            calendar_dates=["2026-07-10"],
            holdout_days=0,
            recent_windows=(1,),
            min_labeled_triggers=1,
        )


def test_profit_markdown_labels_observed_tail_and_reports_date_coverage():
    tail_dates = _observed_tail_dates()
    report = {
        "as_of": tail_dates[-1],
        "calendar_source": {"dates": tail_dates},
        "candidate_source": {
            "candidate_source_identity": {
                "status": "validated",
                "document_dates": tail_dates[:18],
                "complete_candidate_dates": tail_dates[:5],
            }
        },
        "holdout_evidence": {
            "status": "observed_evaluation_tail",
            "blind": False,
            "eligible_for_oos_claim": False,
        },
        "windows": {
            "holdout": {
                "date_count": 20,
                "dates": tail_dates,
                "source_document_date_count": 18,
                "complete_candidate_date_count": 5,
                "source_document_date_coverage_rate": 0.9,
                "complete_candidate_date_coverage_rate": 0.25,
                "candidate_date_coverage_status": "insufficient",
            }
        },
        "parameters": {},
        "candidates": {},
    }

    markdown = profit_audit._markdown(report)

    assert "observed_evaluation_tail" in markdown
    assert "blind: `false`" in markdown
    assert "eligible_for_oos_claim: `false`" in markdown
    assert "source document coverage: `18/20` (`0.9`)" in markdown
    assert "complete candidate coverage: `5/20` (`0.25`)" in markdown
    assert "`holdout`" not in markdown
