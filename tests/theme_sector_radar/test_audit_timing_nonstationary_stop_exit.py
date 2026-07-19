import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

import scripts.audit_timing_nonstationary_stop_exit as stop_audit
import scripts.run_local_stop_loss_path_validation as stop_path_validation
from scripts.audit_timing_nonstationary_stop_exit import (
    audit_nonstationary_stop_samples,
    build_current_stop_trigger_records,
    validate_long_history_identity,
)
from theme_sector_radar.data.trading_calendar import (
    build_trading_calendar_report,
    load_trading_calendar,
)
from theme_sector_radar.timing.candidate_source_identity import validate_records_candidate_source_identity


@pytest.fixture(autouse=True)
def _validated_file_boundaries(monkeypatch):
    production_validate_paper_records = stop_audit.validate_paper_records_report
    monkeypatch.setattr(
        stop_audit,
        "validate_paper_records_report",
        lambda report, *, context, **kwargs: production_validate_paper_records(
            report,
            context=context,
            require_durable_entry_bars_source=False,
        ),
    )
    monkeypatch.setattr(
        stop_audit,
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
        stop_audit,
        "validate_causal_paper_records",
        lambda records, **kwargs: {
            "record_count": len(records),
            "valid_record_count": sum(1 for row in records if row.get("causal_entry_valid")),
            "invalid_record_count": sum(1 for row in records if not row.get("causal_entry_valid")),
        },
        raising=False,
    )
    monkeypatch.setattr(
        stop_audit,
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
        stop_audit,
        "revalidate_records_selection_source_identity",
        lambda identity, **kwargs: dict(identity or {"status": "validated"}),
        raising=False,
    )


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


def test_stop_records_loader_requires_durable_manifest(monkeypatch, tmp_path):
    path = tmp_path / "records.json"
    path.write_text('{"records": []}', encoding="utf-8")

    def capture(_report, *, context, require_durable_entry_bars_source):
        assert context == "stop entry records report"
        assert require_durable_entry_bars_source is True
        raise RuntimeError("durable flag captured")

    monkeypatch.setattr(stop_audit, "validate_paper_records_report", capture)
    with pytest.raises(RuntimeError, match="durable flag captured"):
        stop_audit._load_entry_records_report(
            path,
            as_of="2026-07-13",
            timeframe="1m",
            candidate_root=tmp_path / "candidate",
            candidate_source_root=tmp_path / "source",
        )


def _observed_tail_dates(as_of="2026-07-13"):
    current = date.fromisoformat(as_of)
    dates = []
    while len(dates) < 20:
        if current.weekday() < 5:
            dates.append(current.isoformat())
        current -= timedelta(days=1)
    return sorted(dates)


def _long_history_envelope(events_path, **overrides):
    report = {
        "schema_version": "timing_stop_trigger_factor_validation.v1",
        "bar_interval": "1m",
        "sample_scope": "unconditional_stock_day_stress",
        "strategy_linked_entry_paths": False,
        "trigger_events_path": str(events_path),
        "trigger_events_sha256": hashlib.sha256(events_path.read_bytes()).hexdigest(),
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    report.update(overrides)
    return report


def _entry_records_report(*, candidate_root, timeframe="1m", bar_source=None, paper_only=True, records=None):
    expected_source = {
        "1m": "complete_1m_session",
        "5m": "aggregated_from_complete_1m_session",
    }[timeframe]
    normalized_records = [
        {
            "paper_trading_only": paper_only,
            "no_execution_signals": paper_only,
            "does_not_modify_official_scores": paper_only,
            **record,
        }
        for record in (records or [])
    ]
    return {
        "as_of": "2026-07-13",
        "bar_interval": timeframe,
        "bar_source": bar_source or expected_source,
        "entry_bars_source_identity": {
            "status": "validated",
            "source_kind": "in_memory_test_fixture",
            "sha256": "b" * 64,
        },
        "paper_trading_only": paper_only,
        "no_execution_signals": paper_only,
        "does_not_modify_official_scores": paper_only,
        "parameters": {
            "candidate_root": str(candidate_root),
            "candidate_source_root": str(candidate_root.parent / "source"),
            "selection_validation_root": None,
            "start": None,
            "end": "2026-07-13",
            "version_ids": list(stop_audit.ENTRY_RECORD_VERSION_IDS),
            "concentration_threshold": 2,
            "factor_exit_peak_giveback_pct": 2.0,
            "candidate_source_identity": {
                "status": "validated",
                "candidate_root": str(candidate_root),
                "source_root": str(candidate_root.parent / "source"),
                "bar_interval": timeframe,
                "bar_source": expected_source,
                "manifest_sha256": "a" * 64,
                "document_dates": _observed_tail_dates(),
                "complete_candidate_dates": _observed_tail_dates(),
            }
        },
        "records": normalized_records,
    }


def _bars(day, falling):
    key = day.replace("-", "")
    prices = [10.0, 9.6, 9.4, 9.3, 9.2, 9.1, 9.0] if falling else [10.0] * 7
    rows = []
    for index, close in enumerate(prices):
        rows.append(
            {
                "time": f"{key}09{30 + index:02d}00",
                "open": prices[index - 1] if index else close,
                "close": close,
                "high": close + 0.1,
                "low": close - 0.1,
                "volume": 100.0 if index != 1 else 200.0,
                "amount": 1000.0 if index != 1 else 2000.0,
            }
        )
    return rows


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_number_rejects_nonfinite_values(value):
    assert stop_audit._number(value) is None


def _selected_entry(
    signal_day,
    entry_day,
    code,
    falling,
    version="v31_expanded_balanced_tail_guard",
):
    return {
        "as_of": signal_day,
        "entry_date": entry_day,
        "code": code,
        "timing_version_id": version,
        "causal_entry_valid": True,
        "selection_forward_return_pct": -1.0,
        "path_stats": {"entry_reference_price": 10.0},
        "entry_bars": _bars(entry_day, falling),
        "execution_assumptions": {"bar_interval": "1m"},
    }


def test_nonstationary_stop_audit_splits_recent_holdout_and_factor_coverage():
    samples = []
    selected_entries = []
    start = date(2025, 1, 1)
    for index in range(100):
        day = (start + timedelta(days=index * 2)).isoformat()
        entry_day = (start + timedelta(days=index * 2 + 1)).isoformat()
        samples.extend(
            [
                {"_sample_date": day, "code": "000001", "forward_return_pct": -1.0},
                {"_sample_date": day, "code": "000002", "forward_return_pct": 1.0},
            ]
        )
        selected_entries.extend(
            [
                _selected_entry(day, entry_day, "000001", True),
                _selected_entry(day, entry_day, "000002", False),
            ]
        )

    report = audit_nonstationary_stop_samples(
        samples,
        selected_entries=selected_entries,
        as_of=selected_entries[-1]["entry_date"],
        calendar_dates=sorted({row["_sample_date"] for row in samples}),
        holdout_days=20,
        horizons=(5,),
        fold_count=2,
        min_signals=1,
        timeframe="1m",
    )

    assert report["windows"]["holdout"]["date_count"] == 20
    assert report["windows"]["recent_60"]["date_count"] == 60
    relative = report["factors"]["relative_weakness"]["by_window"]["recent_60"]
    assert relative["by_horizon"]["5"]["signal_count"] == 60
    board = report["factors"]["board_synchronous_weakness"]["by_window"]["recent_60"]
    assert board["eligible_count"] == 0
    assert board["data_status"] == "data_unavailable"
    assert board["data_reason"] == "causal_board_minute_series_not_supplied"
    assert report["paper_trading_only"] is True


def test_nonstationary_stop_audit_reports_candidate_document_date_coverage():
    dates = [f"2026-06-{day:02d}" for day in range(1, 21)]

    report = audit_nonstationary_stop_samples(
        [],
        selected_entries=[],
        as_of=dates[-1],
        calendar_dates=dates,
        source_document_dates=dates[:-2],
        complete_candidate_dates=dates[-5:],
        holdout_days=20,
        timeframe="1m",
    )

    holdout = report["windows"]["holdout"]
    assert holdout["source_document_date_count"] == 18
    assert holdout["complete_candidate_date_count"] == 5
    assert holdout["complete_candidate_date_coverage_rate"] == 0.25
    assert holdout["candidate_date_coverage_status"] == "insufficient"


def test_stop_audit_filters_to_deduplicated_strategy_selected_entries():
    samples = [
        {"_sample_date": "2026-01-02", "code": "000001", "intraday_bars": _bars("2026-01-02", True)},
        {"_sample_date": "2026-01-02", "code": "000002", "intraday_bars": _bars("2026-01-02", False)},
        {"_sample_date": "2026-01-03", "code": "000001", "intraday_bars": _bars("2026-01-03", True)},
    ]
    selected_entries = [
        _selected_entry("2026-01-02", "2026-01-03", "000001", True, "v31_expanded_balanced_tail_guard"),
        _selected_entry("2026-01-02", "2026-01-03", "000001", True, "v32_expanded_defensive_breakdown_guard"),
        _selected_entry("2026-01-02", "2026-01-03", "000002", True, "v26_relative_watch_late_surge_cap"),
    ]

    report = audit_nonstationary_stop_samples(
        samples,
        selected_entries=selected_entries,
        as_of="2026-01-03",
        calendar_dates=["2026-01-02", "2026-01-03"],
        holdout_days=0,
        horizons=(5,),
        min_signals=1,
        timeframe="1m",
    )

    assert report["summary"]["strategy_linked_entry_count"] == 1
    assert report["parameters"]["allowed_entry_version_ids"] == [
        "v31_expanded_balanced_tail_guard",
        "v32_expanded_defensive_breakdown_guard",
    ]
    assert report["summary"]["triggered_record_count"] == 1
    assert report["summary"]["strategy_linked_entry_paths"] is True
    assert report["summary"]["entry_reference_is_actual_fill"] is False
    assert report["summary"]["entry_reference_is_causal_simulated_fill"] is True
    relative = report["factors"]["relative_weakness"]["by_window"]["all_history"]
    assert relative["eligible_count"] == 0


def test_stop_long_history_rejects_timeframe_mismatch_and_marks_stress_auxiliary(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text("{}\n", encoding="utf-8")
    stress = _long_history_envelope(events_path)

    with pytest.raises(ValueError, match="bar interval"):
        validate_long_history_identity(stress, timeframe="5m")

    validated = validate_long_history_identity(stress, timeframe="1m")
    assert validated["status"] == "auxiliary_only"
    assert validated["trigger_events_sha256"] == stress["trigger_events_sha256"]

    events_path.write_text('{"tampered":true}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="trigger events SHA mismatch"):
        validate_long_history_identity(stress, timeframe="1m")


def test_stop_long_history_requires_trigger_event_provenance():
    stress = {
        "schema_version": "timing_stop_trigger_factor_validation.v1",
        "bar_interval": "1m",
        "sample_scope": "unconditional_stock_day_stress",
        "strategy_linked_entry_paths": False,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }

    with pytest.raises(ValueError, match="trigger events path and SHA"):
        validate_long_history_identity(stress, timeframe="1m")


def test_stop_long_history_does_not_accept_truthy_strategy_linkage(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text("", encoding="utf-8")
    report = _long_history_envelope(events_path, strategy_linked_entry_paths="yes")

    validated = validate_long_history_identity(report, timeframe="1m")

    assert validated["status"] == "auxiliary_only"
    assert validated["eligible_as_long_history_veto"] is False


def test_stop_long_history_recomputes_metrics_from_verified_jsonl(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text("", encoding="utf-8")
    report = _long_history_envelope(
        events_path,
        parameters={"horizons": [5], "fold_count": 1, "min_signals": 1},
        summary={"triggered_record_count": 999},
        baseline={"forged": True},
        factors={"forged": True},
    )

    compact = stop_audit._compact_long_history(report, timeframe="1m")

    assert compact["summary"]["triggered_record_count"] == 0
    assert compact["parameters"]["horizons"] == [5, 15, 30]
    assert compact["parameters"]["fold_count"] == 5
    assert compact["parameters"]["min_signals"] == 30
    assert "forged" not in compact["baseline"]
    assert "forged" not in compact["factors"]


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("schema_version", "forged.v1", "schema"),
        ("paper_trading_only", "yes", "paper-only"),
        ("no_execution_signals", 1, "paper-only"),
        ("does_not_modify_official_scores", None, "paper-only"),
    ],
)
def test_stop_long_history_requires_strict_paper_envelope(tmp_path, field, value, match):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text("", encoding="utf-8")
    report = _long_history_envelope(events_path)
    report[field] = value

    with pytest.raises(ValueError, match=match):
        validate_long_history_identity(report, timeframe="1m")


def test_stop_long_history_requires_strict_paper_identity_on_every_event(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text('{"paper_research_only":"yes"}\n', encoding="utf-8")
    report = _long_history_envelope(events_path)

    with pytest.raises(ValueError, match="event.*paper_research_only"):
        stop_audit._compact_long_history(report, timeframe="1m")


def test_stop_long_history_rejects_executable_fields_in_event_jsonl(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        '{"paper_research_only":true,"nested":{"orders":[{"side":"buy","quantity":1}]}}\n',
        encoding="utf-8",
    )
    report = _long_history_envelope(events_path)

    with pytest.raises(ValueError, match="executable instruction fields"):
        stop_audit._compact_long_history(report, timeframe="1m")


def test_stop_long_history_accepts_production_observed_trigger_price(tmp_path):
    event = stop_path_validation._compact_trigger_event(
        {
            "date": "2024-01-02",
            "code": "000001",
            "next_day_return_pct": -1.0,
            "fixed_stop_path": {
                "triggered": True,
                "trigger_price": 9.6,
                "horizons": {},
            },
            "trigger_factor_features": {},
        }
    )
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    report = _long_history_envelope(events_path)

    compact = stop_audit._compact_long_history(report, timeframe="1m")

    assert compact["summary"]["triggered_record_count"] == 1


def test_stop_long_history_rejects_structured_trigger_price_exemption(tmp_path):
    event = stop_path_validation._compact_trigger_event(
        {
            "date": "2024-01-02",
            "code": "000001",
            "next_day_return_pct": -1.0,
            "fixed_stop_path": {
                "triggered": True,
                "trigger_price": 9.6,
                "horizons": {},
            },
            "trigger_factor_features": {},
        }
    )
    event["fixed_stop_path"]["trigger_price"] = {
        "orders": [{"side": "buy", "quantity": 1}]
    }
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    report = _long_history_envelope(events_path)

    with pytest.raises(ValueError, match="trigger_price"):
        stop_audit._compact_long_history(report, timeframe="1m")


def test_stop_long_history_requires_complete_event_paper_guards_for_new_files(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        json.dumps({"paper_research_only": True}) + "\n",
        encoding="utf-8",
    )
    report = _long_history_envelope(events_path)

    with pytest.raises(ValueError, match="no_execution_signals"):
        stop_audit._compact_long_history(report, timeframe="1m")


@pytest.mark.parametrize(
    "field",
    ["no_execution_signals", "does_not_modify_official_scores"],
)
def test_stop_long_history_rejects_false_event_paper_guard(tmp_path, field):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        json.dumps(
            {
                "paper_research_only": True,
                "no_execution_signals": True,
                "does_not_modify_official_scores": True,
                field: False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    report = _long_history_envelope(events_path)

    with pytest.raises(ValueError, match=rf"event.*{field}"):
        stop_audit._compact_long_history(report, timeframe="1m")


def test_stop_long_history_binds_recomputed_events_to_declared_sha(tmp_path, monkeypatch):
    events_path = tmp_path / "events.jsonl"
    first_bytes = b'{"paper_research_only":true}\n'
    events_path.write_bytes(first_bytes)
    report = _long_history_envelope(events_path)
    original_read_bytes = Path.read_bytes

    def read_then_replace(self):
        payload = original_read_bytes(self)
        if self == events_path:
            self.write_bytes(b'{"paper_research_only":true,"date":"2024-01-02"}\n')
        return payload

    monkeypatch.setattr(Path, "read_bytes", read_then_replace)

    with pytest.raises(ValueError, match="trigger events SHA mismatch"):
        stop_audit._compact_long_history(report, timeframe="1m")


def test_stop_long_history_downgrades_unverifiable_strategy_linkage(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        json.dumps(
            {
                "paper_research_only": True,
                "no_execution_signals": True,
                "does_not_modify_official_scores": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    report = _long_history_envelope(
        events_path,
        strategy_linked_entry_paths=True,
        entry_model="next_trading_session_first_bar_open",
        parameters={"version_ids": list(stop_audit.STOP_ENTRY_VERSION_IDS)},
    )

    compact = stop_audit._compact_long_history(report, timeframe="1m")

    assert compact["status"] == "auxiliary_only"
    assert compact["eligible_as_long_history_veto"] is False
    assert compact["reason"] == "strategy_linked_external_anchors_unavailable"


def test_stop_long_history_downgrades_self_reported_strategy_identity_without_external_anchors(tmp_path):
    events_path = tmp_path / "events.jsonl"
    event = {
        "date": "2024-01-03",
        "signal_date": "2024-01-02",
        "entry_date": "2024-01-03",
        "code": "000001",
        "timing_version_id": "v31_expanded_balanced_tail_guard",
        "strategy_linked_entry_path": True,
        "causal_entry_valid": True,
        "entry_bars_sha256": "a" * 64,
        "execution_assumptions": {
            "entry_model": "next_trading_session_first_bar_open",
            "bar_interval": "1m",
            "bar_source": "complete_1m_session",
            "paper_research_only": True,
        },
        "fixed_stop_path": {"triggered": True},
        "paper_research_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    events_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    report = _long_history_envelope(
        events_path,
        strategy_linked_entry_paths=True,
        entry_model="next_trading_session_first_bar_open",
        parameters={"version_ids": list(stop_audit.STOP_ENTRY_VERSION_IDS)},
    )

    compact = stop_audit._compact_long_history(report, timeframe="1m")

    assert compact["status"] == "auxiliary_only"
    assert compact["eligible_as_long_history_veto"] is False
    assert compact["reason"] == "strategy_linked_external_anchors_unavailable"


def test_stop_long_history_downgrades_non_iso_causal_entry_dates(tmp_path):
    events_path = tmp_path / "events.jsonl"
    event = {
        "date": "zzzz-entry",
        "signal_date": "not-a-date",
        "entry_date": "zzzz-entry",
        "code": "000001",
        "timing_version_id": "v31_expanded_balanced_tail_guard",
        "strategy_linked_entry_path": True,
        "causal_entry_valid": True,
        "entry_bars_sha256": "a" * 64,
        "execution_assumptions": {
            "entry_model": "next_trading_session_first_bar_open",
            "bar_interval": "1m",
            "bar_source": "complete_1m_session",
            "paper_research_only": True,
        },
        "fixed_stop_path": {"triggered": True},
        "paper_research_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    events_path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    report = _long_history_envelope(
        events_path,
        strategy_linked_entry_paths=True,
        entry_model="next_trading_session_first_bar_open",
        parameters={"version_ids": list(stop_audit.STOP_ENTRY_VERSION_IDS)},
    )

    compact = stop_audit._compact_long_history(report, timeframe="1m")

    assert compact["status"] == "auxiliary_only"
    assert compact["reason"] == "strategy_linked_external_anchors_unavailable"


def test_stop_file_audit_uses_only_labeled_trading_dates(monkeypatch, tmp_path):
    tail_dates = _observed_tail_dates()
    samples = [
        {"_sample_date": tail_dates[0], "code": "000001", "forward_return_pct": 1.0, "intraday_bars": _bars(tail_dates[0], True)},
        {"_sample_date": "2026-07-11", "code": "000002", "forward_return_pct": None, "intraday_bars": _bars("2026-07-11", True)},
        {"_sample_date": "2026-07-12", "code": "000003", "forward_return_pct": None, "intraday_bars": _bars("2026-07-12", True)},
        {"_sample_date": tail_dates[-1], "code": "000004", "forward_return_pct": -1.0, "intraday_bars": _bars(tail_dates[-1], True)},
    ]
    monkeypatch.setattr(stop_audit, "_load_samples", lambda *args: samples)
    entry_records_path = tmp_path / "entries.json"
    entry_records_path.write_text(
        json.dumps(_entry_records_report(candidate_root=tmp_path / "candidates")),
        encoding="utf-8",
    )
    long_history_events_path = tmp_path / "long-history-events.jsonl"
    long_history_events_path.write_text("", encoding="utf-8")
    long_history_report_path = tmp_path / "long-history.json"
    long_history_report_path.write_text(
        json.dumps(
            _long_history_envelope(long_history_events_path)
        ),
        encoding="utf-8",
    )

    result = stop_audit.audit_nonstationary_stop_exit(
        candidate_root=tmp_path / "candidates",
        candidate_source_root=tmp_path / "source",
        selection_validation_root=None,
        output_dir=tmp_path / "output",
        as_of="2026-07-13",
        timeframe="1m",
        entry_records_path=entry_records_path,
        trading_calendar_path=_calendar_path(
            tmp_path, tail_dates, records_path=entry_records_path
        ),
        long_history_report_path=long_history_report_path,
        holdout_days=20,
        horizons=(5,),
        min_signals=1,
    )

    assert result["report"]["windows"]["all_history"]["dates"] == tail_dates
    assert "2026-07-11" not in result["report"]["windows"]["all_history"]["dates"]
    assert "2026-07-12" not in result["report"]["windows"]["all_history"]["dates"]
    assert result["report"]["source_as_of"] == "2026-07-13"
    assert result["report"]["source_bar_interval"] == "1m"
    assert result["report"]["source_bar_source"] == "complete_1m_session"
    assert result["report"]["entry_records_sha256"] == hashlib.sha256(entry_records_path.read_bytes()).hexdigest()
    assert result["report"]["long_history_report_sha256"] == hashlib.sha256(
        long_history_report_path.read_bytes()
    ).hexdigest()


def test_stop_file_audit_rejects_non_paper_entry_source(monkeypatch, tmp_path):
    monkeypatch.setattr(
        stop_audit,
        "_load_samples",
        lambda *args: [{"_sample_date": "2026-07-13", "forward_return_pct": 0.0}],
    )
    entry_records_path = tmp_path / "entries.json"
    entry_records_path.write_text(
        json.dumps(_entry_records_report(candidate_root=tmp_path / "candidates", paper_only=False)),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="paper-only"):
        stop_audit.audit_nonstationary_stop_exit(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=None,
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="1m",
            entry_records_path=entry_records_path,
            trading_calendar_path=_calendar_path(
                tmp_path, ["2026-07-13"], records_path=entry_records_path
            ),
        )


def test_stop_file_audit_rejects_native_5m_entry_source(monkeypatch, tmp_path):
    monkeypatch.setattr(
        stop_audit,
        "_load_samples",
        lambda *args: [{"_sample_date": "2026-07-13", "forward_return_pct": 0.0}],
    )
    entry_records_path = tmp_path / "entries.json"
    entry_records_path.write_text(
        json.dumps(
            _entry_records_report(
                candidate_root=tmp_path / "candidates",
                timeframe="5m",
                bar_source="native_5m_session",
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="bar source"):
        stop_audit.audit_nonstationary_stop_exit(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=None,
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="5m",
            entry_records_path=entry_records_path,
            trading_calendar_path=_calendar_path(
                tmp_path, ["2026-07-13"], records_path=entry_records_path
            ),
        )


def test_stop_file_audit_rejects_candidate_identity_from_another_root(monkeypatch, tmp_path):
    monkeypatch.setattr(
        stop_audit,
        "_load_samples",
        lambda *args: [{"_sample_date": "2026-07-13", "forward_return_pct": 0.0}],
    )
    entry_records_path = tmp_path / "entries.json"
    entry_records_path.write_text(
        json.dumps(_entry_records_report(candidate_root=tmp_path / "different-candidates")),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="candidate root"):
        stop_audit.audit_nonstationary_stop_exit(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=None,
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="1m",
            entry_records_path=entry_records_path,
            trading_calendar_path=_calendar_path(
                tmp_path, ["2026-07-13"], records_path=entry_records_path
            ),
        )


def test_stop_file_audit_revalidates_current_candidate_root(monkeypatch, tmp_path):
    monkeypatch.setattr(
        stop_audit,
        "_load_samples",
        lambda *args: [{"_sample_date": "2026-07-13", "forward_return_pct": 0.0}],
    )
    monkeypatch.setattr(
        stop_audit,
        "revalidate_records_candidate_source_identity",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("current root manifest mismatch")),
    )
    entry_records_path = tmp_path / "entries.json"
    entry_records_path.write_text(
        json.dumps(_entry_records_report(candidate_root=tmp_path / "candidates")),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="current root manifest"):
        stop_audit.audit_nonstationary_stop_exit(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=None,
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="1m",
            entry_records_path=entry_records_path,
            trading_calendar_path=_calendar_path(
                tmp_path, ["2026-07-13"], records_path=entry_records_path
            ),
        )


def test_stop_file_audit_revalidates_current_selection_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(
        stop_audit,
        "_load_samples",
        lambda *args: [{"_sample_date": "2026-07-13", "forward_return_pct": 0.0}],
    )
    monkeypatch.setattr(
        stop_audit,
        "revalidate_records_selection_source_identity",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("selection source manifest SHA mismatch")),
        raising=False,
    )
    entry_records_path = tmp_path / "entries.json"
    entry_records_path.write_text(
        json.dumps(_entry_records_report(candidate_root=tmp_path / "candidates")),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="selection source manifest SHA mismatch"):
        stop_audit.audit_nonstationary_stop_exit(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=None,
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="1m",
            entry_records_path=entry_records_path,
            trading_calendar_path=_calendar_path(
                tmp_path, ["2026-07-13"], records_path=entry_records_path
            ),
        )


def test_stop_loader_accepts_exact_three_version_upstream_entry_cohort(tmp_path):
    entry_records_path = tmp_path / "entries.json"
    data = _entry_records_report(candidate_root=tmp_path / "candidates")
    data["parameters"]["version_ids"] = [
        "v26_relative_watch_late_surge_cap",
        "v31_expanded_balanced_tail_guard",
        "v32_expanded_defensive_breakdown_guard",
    ]
    entry_records_path.write_text(json.dumps(data), encoding="utf-8")

    records, identity, records_sha256 = stop_audit._load_entry_records_report(
        entry_records_path,
        as_of="2026-07-13",
        timeframe="1m",
        candidate_root=tmp_path / "candidates",
        candidate_source_root=tmp_path / "source",
    )

    assert records == []
    assert identity["parameters"]["version_ids"] == data["parameters"]["version_ids"]
    assert records_sha256 == hashlib.sha256(entry_records_path.read_bytes()).hexdigest()


def test_stop_entry_records_loader_binds_sha_to_parsed_bytes(tmp_path, monkeypatch):
    entry_records_path = tmp_path / "entries.json"
    first_bytes = json.dumps(
        _entry_records_report(candidate_root=tmp_path / "candidates")
    ).encode("utf-8")
    entry_records_path.write_bytes(first_bytes)
    expected_sha256 = hashlib.sha256(first_bytes).hexdigest()
    original_read_bytes = Path.read_bytes

    def read_then_replace(self):
        payload = original_read_bytes(self)
        if self == entry_records_path:
            self.write_text("{}", encoding="utf-8")
        return payload

    monkeypatch.setattr(Path, "read_bytes", read_then_replace)

    records, identity, actual_sha256 = stop_audit._load_entry_records_report(
        entry_records_path,
        as_of="2026-07-13",
        timeframe="1m",
        candidate_root=tmp_path / "candidates",
        candidate_source_root=tmp_path / "source",
    )

    assert records == []
    assert identity["as_of"] == "2026-07-13"
    assert actual_sha256 == expected_sha256


def test_stop_file_audit_rebuilds_record_cohort(monkeypatch, tmp_path):
    monkeypatch.setattr(
        stop_audit,
        "_load_samples",
        lambda *args: [{"_sample_date": "2026-07-13", "forward_return_pct": 0.0}],
    )
    monkeypatch.setattr(
        stop_audit,
        "validate_paper_record_cohort",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("stop cohort missing candidate selection")),
        raising=False,
    )
    entry_records_path = tmp_path / "entries.json"
    entry_records_path.write_text(
        json.dumps(_entry_records_report(candidate_root=tmp_path / "candidates")),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="stop cohort missing"):
        stop_audit.audit_nonstationary_stop_exit(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=None,
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="1m",
            entry_records_path=entry_records_path,
            trading_calendar_path=_calendar_path(
                tmp_path, ["2026-07-13"], records_path=entry_records_path
            ),
        )


def test_stop_audit_requires_strategy_selected_entry_records():
    with pytest.raises(ValueError, match="selected entry"):
        audit_nonstationary_stop_samples([], selected_entries=None, timeframe="1m")


def test_stop_audit_uses_causal_entry_bars_not_signal_day_candidate_bars():
    samples = [
        {
            "_sample_date": "2026-07-10",
            "code": "000001",
            "forward_return_pct": -1.0,
            "intraday_bars": _bars("2026-07-10", True),
        }
    ]
    selected_entries = [
        {
            "as_of": "2026-07-10",
            "entry_date": "2026-07-13",
            "code": "000001",
            "timing_version_id": "v31_expanded_balanced_tail_guard",
            "causal_entry_valid": True,
            "forward_return_pct": 0.0,
            "path_stats": {"entry_reference_price": 10.0},
            "entry_bars": _bars("2026-07-13", False),
            "execution_assumptions": {"bar_interval": "1m"},
        }
    ]

    report = audit_nonstationary_stop_samples(
        samples,
        selected_entries=selected_entries,
        as_of="2026-07-13",
        calendar_dates=["2026-07-10"],
        holdout_days=0,
        horizons=(5,),
        min_signals=1,
        timeframe="1m",
    )

    assert report["summary"]["strategy_linked_entry_count"] == 1
    assert report["summary"]["triggered_record_count"] == 0


def test_stop_audit_rejects_timeframe_not_bound_to_selected_entry_bars():
    selected = [_selected_entry("2026-07-10", "2026-07-13", "000001", True)]

    with pytest.raises(ValueError, match="timeframe"):
        audit_nonstationary_stop_samples(
            [{"_sample_date": "2026-07-10", "forward_return_pct": -1.0}],
            selected_entries=selected,
            as_of="2026-07-13",
            calendar_dates=["2026-07-10"],
            holdout_days=0,
            timeframe="5m",
        )


def test_stop_relative_weakness_uses_date_timestamp_from_causal_entry_bars():
    def selected(code, closes):
        bars = [
            {
                "date": int(f"2026071309{30 + index:02d}00"),
                "open": closes[index - 1] if index else close,
                "high": max(close, closes[index - 1] if index else close),
                "low": min(close, closes[index - 1] if index else close),
                "close": close,
            }
            for index, close in enumerate(closes)
        ]
        return {
            "as_of": "2026-07-10",
            "entry_date": "2026-07-13",
            "code": code,
            "timing_version_id": "v31_expanded_balanced_tail_guard",
            "causal_entry_valid": True,
            "forward_return_pct": 0.0,
            "path_stats": {"entry_reference_price": 10.0},
            "entry_bars": bars,
            "execution_assumptions": {"bar_interval": "1m"},
        }

    records = build_current_stop_trigger_records(
        [],
        selected_entries=[
            selected("000001", [10.0, 9.8, 9.6, 9.5, 9.4, 9.3, 9.2]),
            selected("000002", [10.0] * 7),
        ],
        as_of="2026-07-13",
        timeframe="1m",
    )

    assert len(records) == 1
    features = records[0]["trigger_factor_features"]
    assert features["market_proxy_return_at_trigger_pct"] == 0.0
    assert features["relative_vs_market_proxy_pct"] == -4.0
    assert features["relative_weakness"] is True


def test_stop_markdown_labels_observed_tail_and_reports_date_coverage():
    tail_dates = _observed_tail_dates()
    report = {
        "as_of": tail_dates[-1],
        "calendar_source": {"dates": tail_dates},
        "candidate_source_identity": {
            "status": "validated",
            "document_dates": tail_dates[:18],
            "complete_candidate_dates": tail_dates[:5],
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
        "summary": {},
        "factors": {},
    }

    markdown = stop_audit._markdown(report)

    assert "observed_evaluation_tail" in markdown
    assert "blind: `false`" in markdown
    assert "eligible_for_oos_claim: `false`" in markdown
    assert "source document coverage: `18/20` (`0.9`)" in markdown
    assert "complete candidate coverage: `5/20` (`0.25`)" in markdown
    assert "`holdout`" not in markdown
