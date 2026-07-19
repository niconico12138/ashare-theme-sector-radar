import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

import scripts.audit_timing_nonstationary_entry as entry_audit
from scripts.audit_timing_strategy_overfit import _load_samples
from scripts.audit_timing_nonstationary_entry import (
    _factor_correlation,
    _perturbation_report,
    audit_nonstationary_entry_samples,
)
from theme_sector_radar.timing.combination_experiment import FactorCondition, StrategyVersion
from theme_sector_radar.data.trading_calendar import (
    build_trading_calendar_report,
    load_trading_calendar,
)
from theme_sector_radar.timing.candidate_source_identity import validate_records_candidate_source_identity


@pytest.fixture(autouse=True)
def _validated_file_boundaries(monkeypatch):
    production_validate_paper_records = entry_audit.validate_paper_records_report
    monkeypatch.setattr(
        entry_audit,
        "validate_paper_records_report",
        lambda report, *, context, **kwargs: production_validate_paper_records(
            report,
            context=context,
            require_durable_entry_bars_source=False,
        ),
    )
    monkeypatch.setattr(
        entry_audit,
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
        entry_audit,
        "validate_causal_paper_records",
        lambda records, **kwargs: {
            "record_count": len(records),
            "valid_record_count": sum(1 for row in records if row.get("causal_entry_valid")),
            "invalid_record_count": sum(1 for row in records if not row.get("causal_entry_valid")),
        },
        raising=False,
    )
    monkeypatch.setattr(
        entry_audit,
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
        entry_audit,
        "revalidate_records_selection_source_identity",
        lambda identity, **kwargs: dict(identity or {"status": "validated"}),
        raising=False,
    )


def _row(day, code, ret, passing=True):
    value = 80 if passing else 0
    return {
        "_sample_date": day,
        "code": code,
        "boards": ["test"],
        "forward_return_pct": ret,
        "open_to_midday_resilience_score": value,
        "midday_hold_score": value,
        "vwap_above_ratio_score": value,
        "late_high_near_close_score": 90 if passing else 0,
        "high_to_close_drawdown_score": 5 if passing else 90,
        "lower_low_sequence_risk": 5 if passing else 90,
        "stock_vs_market_intraday_alpha_score": value,
        "relative_resilience_score": value,
        "optimized_watch_score": value,
        "late_amount_surge_score": 20 if passing else 90,
        "failed_breakout_risk": 5 if passing else 90,
        "execution_tradeability_score": value,
        "late_breakdown_risk": 0 if passing else 90,
        "market_regime_score": 65,
    }


def test_entry_records_loader_requires_durable_manifest(monkeypatch, tmp_path):
    path = tmp_path / "records.json"
    path.write_text('{"records": []}', encoding="utf-8")

    def capture(_report, *, context, require_durable_entry_bars_source):
        assert context == "entry records report"
        assert require_durable_entry_bars_source is True
        raise RuntimeError("durable flag captured")

    monkeypatch.setattr(entry_audit, "validate_paper_records_report", capture)
    with pytest.raises(RuntimeError, match="durable flag captured"):
        entry_audit._load_causal_entry_records_report(
            path,
            as_of="2026-07-13",
            timeframe="1m",
            candidate_root=tmp_path / "candidate",
            candidate_source_root=tmp_path / "source",
        )


def _write_entry_records(path, records):
    candidate_root = path.parent / "candidates"
    normalized_records = [
        {
            "entry_bars_sha256": "a" * 64,
            "paper_trading_only": True,
            "no_execution_signals": True,
            "does_not_modify_official_scores": True,
            "execution_assumptions": {
                "signal_available": "after_signal_session_close",
                "entry_model": "next_trading_session_first_bar_open",
                "bar_interval": "1m",
                "bar_source": "complete_1m_session",
            },
            **record,
        }
        for record in records
    ]
    path.write_text(
        json.dumps(
            {
                "as_of": "2026-07-13",
                "bar_interval": "1m",
                "bar_source": "complete_1m_session",
                "entry_bars_source_identity": {
                    "status": "validated",
                    "source_kind": "in_memory_test_fixture",
                    "sha256": "b" * 64,
                },
                "parameters": {
                    "version_ids": list(entry_audit.VERSION_IDS),
                    "start": None,
                    "end": "2026-07-13",
                    "concentration_threshold": 2,
                    "factor_exit_peak_giveback_pct": 2.0,
                    "candidate_source_identity": {
                        "status": "validated",
                        "candidate_root": str(candidate_root),
                        "source_root": str(path.parent / "source"),
                        "bar_interval": "1m",
                        "bar_source": "complete_1m_session",
                        "manifest_sha256": "a" * 64,
                        "document_dates": _observed_tail_dates(),
                        "complete_candidate_dates": _observed_tail_dates(),
                    },
                },
                "records": normalized_records,
                "paper_trading_only": True,
                "no_execution_signals": True,
                "does_not_modify_official_scores": True,
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_calendar(path, dates, *, end="2026-07-13", records_path=None):
    path.write_text(
        json.dumps(
            build_trading_calendar_report(
                dates,
                source="unit-exchange-calendar",
                requested_start=min(dates),
                requested_end=end,
            )
        ),
        encoding="utf-8",
    )
    if records_path is not None:
        records_report = json.loads(records_path.read_text(encoding="utf-8"))
        records_report["trading_calendar"] = load_trading_calendar(path, as_of=end)
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


def test_nonstationary_entry_audit_includes_windows_perturbation_and_ablation():
    samples = []
    for index in range(150):
        day = f"2025-{index // 28 + 1:02d}-{index % 28 + 1:02d}"
        samples.extend([_row(day, f"6{index:05d}", 2.0), _row(day, f"0{index:05d}", -1.0, passing=False)])

    report = audit_nonstationary_entry_samples(
        samples,
        as_of="2025-06-10",
        calendar_dates=sorted({row["_sample_date"] for row in samples}),
        min_selected=1,
        holdout_days=20,
    )

    assert set(report["versions"]) == {
        "v26_relative_watch_late_surge_cap",
        "v31_expanded_balanced_tail_guard",
        "v32_expanded_defensive_breakdown_guard",
    }
    assert report["windows"]["holdout"]["date_count"] == 20
    assert report["versions"]["v31_expanded_balanced_tail_guard"]["perturbation"]["variant_count"] == 2
    assert report["versions"]["v32_expanded_defensive_breakdown_guard"]["ablation"]["variant_count"] == 12
    v31 = report["versions"]["v31_expanded_balanced_tail_guard"]
    loose_conditions = v31["perturbation"]["variants"][0]["conditions"]
    loose_drawdown = next(item for item in loose_conditions if item["factor_id"] == "high_to_close_drawdown_score")
    assert loose_drawdown["threshold"] == 22.0
    assert v31["walk_forward"]["fold_count"] == 5
    assert "high_correlation_pairs" in v31["factor_correlation"]
    assert v31["factor_correlation"]["pair_count"] == v31["factor_correlation"]["expected_pair_count"]
    assert max(report["windows"]["all_history"]["dates"]) <= "2025-06-10"
    assert report["paper_trading_only"] is True


def test_nonstationary_entry_audit_reports_complete_candidate_date_coverage():
    dates = [f"2026-06-{day:02d}" for day in range(1, 21)]
    samples = [_row(day, f"6{index:05d}", 1.0) for index, day in enumerate(dates)]

    report = audit_nonstationary_entry_samples(
        samples,
        as_of=dates[-1],
        calendar_dates=dates,
        holdout_days=20,
        min_selected=1,
        source_document_dates=dates,
        complete_candidate_dates=dates[-5:],
    )

    holdout = report["windows"]["holdout"]
    assert holdout["source_document_date_count"] == 20
    assert holdout["complete_candidate_date_count"] == 5
    assert holdout["source_document_date_coverage_rate"] == 1.0
    assert holdout["complete_candidate_date_coverage_rate"] == 0.25
    assert holdout["candidate_date_coverage_status"] == "insufficient"


def test_nonstationary_entry_audit_rejects_tiny_holdout_selection():
    samples = []
    for index in range(30):
        day = f"2026-01-{index + 1:02d}"
        samples.append(_row(day, f"0{index:05d}", -1.0, passing=False))
    samples.append(_row("2026-01-30", "600001", 2.0, passing=True))

    report = audit_nonstationary_entry_samples(samples, min_selected=3, holdout_days=5)

    risk = report["versions"]["v31_expanded_balanced_tail_guard"]["overfit_risk"]
    assert risk["risk_level"] == "high"
    assert "holdout_insufficient" in risk["risk_points"]
    assert "recent_120_insufficient" in risk["risk_points"]


def test_entry_file_audit_uses_only_labeled_trading_dates(monkeypatch, tmp_path):
    tail_dates = _observed_tail_dates()
    samples = [
        _row(tail_dates[0], "000001", 1.0),
        _row("2026-07-11", "000002", None),
        _row("2026-07-12", "000003", None),
        _row(tail_dates[-1], "000004", -1.0),
    ]
    monkeypatch.setattr(entry_audit, "_load_samples", lambda *args: samples)
    entry_records_path = _write_entry_records(tmp_path / "causal-entry-records.json", [])
    calendar_path = _write_calendar(
        tmp_path / "calendar.json", tail_dates, records_path=entry_records_path
    )

    result = entry_audit.audit_nonstationary_entry(
        candidate_root=tmp_path / "candidates",
        candidate_source_root=tmp_path / "source",
        selection_validation_root=tmp_path / "selection",
        entry_records_path=entry_records_path,
        trading_calendar_path=calendar_path,
        output_dir=tmp_path / "output",
        as_of="2026-07-13",
        timeframe="1m",
        min_selected=1,
    )

    assert result["report"]["windows"]["all_history"]["dates"] == tail_dates
    assert "2026-07-11" not in result["report"]["windows"]["all_history"]["dates"]
    assert "2026-07-12" not in result["report"]["windows"]["all_history"]["dates"]


def test_entry_file_audit_rejects_records_bound_to_another_calendar(monkeypatch, tmp_path):
    dates = ["2026-07-10", "2026-07-13"]
    monkeypatch.setattr(
        entry_audit,
        "_load_samples",
        lambda *args: [_row("2026-07-10", "000001", 1.0)],
    )
    entry_records_path = _write_entry_records(tmp_path / "records.json", [])
    _write_calendar(
        tmp_path / "calendar-a.json",
        dates,
        records_path=entry_records_path,
    )
    different_calendar_path = _write_calendar(tmp_path / "calendar-b.json", dates)

    with pytest.raises(ValueError, match="calendar path mismatch"):
        entry_audit.audit_nonstationary_entry(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=tmp_path / "selection",
            entry_records_path=entry_records_path,
            trading_calendar_path=different_calendar_path,
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="1m",
            min_selected=1,
        )


def test_entry_file_audit_uses_version_specific_causal_returns(monkeypatch, tmp_path):
    tail_dates = _observed_tail_dates()
    samples = [_row(tail_dates[0], "000001", 99.0)]
    monkeypatch.setattr(entry_audit, "_load_samples", lambda *args: samples)
    entry_records_path = _write_entry_records(
        tmp_path / "causal-entry-records.json",
        [
            {
                "signal_date": tail_dates[0],
                "entry_date": tail_dates[1],
                "code": "000001",
                "timing_version_id": version_id,
                "causal_entry_valid": True,
                "forward_return_pct": -2.0,
            }
            for version_id in entry_audit.VERSION_IDS
        ],
    )
    calendar_path = _write_calendar(
        tmp_path / "calendar.json", tail_dates, records_path=entry_records_path
    )

    result = entry_audit.audit_nonstationary_entry(
        candidate_root=tmp_path / "candidates",
        candidate_source_root=tmp_path / "source",
        selection_validation_root=tmp_path / "selection",
        entry_records_path=entry_records_path,
        trading_calendar_path=calendar_path,
        output_dir=tmp_path / "output",
        as_of="2026-07-13",
        timeframe="1m",
        min_selected=1,
    )

    report = result["report"]
    assert report["label_source"]["mode"] == "causal_next_session_open_to_close"
    assert report["versions"]["v31_expanded_balanced_tail_guard"]["by_window"]["all_history"][
        "selected_avg_return_pct"
    ] == -2.1
    assert report["parameters"]["round_trip_cost_pct"] == 0.1
    assert report["causal_entry_coverage"]["valid_record_count"] == 3


def test_entry_file_audit_excludes_sample_mode_rows_from_window_analysis(monkeypatch, tmp_path):
    tail_dates = _observed_tail_dates()
    normal = _row(tail_dates[0], "000001", 99.0)
    sample_mode = dict(normal, _sample_mode=True)
    monkeypatch.setattr(entry_audit, "_load_samples", lambda *args: [normal, sample_mode])
    entry_records_path = _write_entry_records(
        tmp_path / "causal-entry-records.json",
        [
            {
                "signal_date": tail_dates[0],
                "entry_date": tail_dates[1],
                "code": "000001",
                "timing_version_id": version_id,
                "causal_entry_valid": True,
                "forward_return_pct": 1.0,
            }
            for version_id in entry_audit.VERSION_IDS
        ],
    )
    calendar_path = _write_calendar(
        tmp_path / "calendar.json", tail_dates, records_path=entry_records_path
    )

    result = entry_audit.audit_nonstationary_entry(
        candidate_root=tmp_path / "candidates",
        candidate_source_root=tmp_path / "source",
        selection_validation_root=tmp_path / "selection",
        entry_records_path=entry_records_path,
        trading_calendar_path=calendar_path,
        output_dir=tmp_path / "output",
        as_of="2026-07-13",
        timeframe="1m",
        min_selected=1,
    )

    report = result["report"]
    assert report["windows"]["all_history"]["record_count"] == 1
    assert report["versions"]["v31_expanded_balanced_tail_guard"]["by_window"]["all_history"][
        "selected_count"
    ] == 1


def test_entry_file_audit_rejects_future_entry_after_as_of(monkeypatch, tmp_path):
    monkeypatch.setattr(entry_audit, "_load_samples", lambda *args: [_row("2026-07-10", "000001", 1.0)])
    entry_records_path = _write_entry_records(
        tmp_path / "future-entry-records.json",
        [
            {
                "signal_date": "2026-07-10",
                "entry_date": "2026-07-20",
                "code": "000001",
                "timing_version_id": version_id,
                "causal_entry_valid": True,
                "forward_return_pct": 5.0,
            }
            for version_id in entry_audit.VERSION_IDS
        ],
    )
    calendar_path = _write_calendar(
        tmp_path / "calendar.json",
        ["2026-07-10", "2026-07-13"],
        records_path=entry_records_path,
    )

    with pytest.raises(ValueError, match="after audit as_of"):
        entry_audit.audit_nonstationary_entry(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=tmp_path / "selection",
            entry_records_path=entry_records_path,
            trading_calendar_path=calendar_path,
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="1m",
            min_selected=1,
        )


def test_entry_file_audit_rejects_native_5m_bar_source(monkeypatch, tmp_path):
    monkeypatch.setattr(entry_audit, "_load_samples", lambda *args: [_row("2026-07-10", "000001", 1.0)])
    entry_records_path = _write_entry_records(tmp_path / "records.json", [])
    source = json.loads(entry_records_path.read_text(encoding="utf-8"))
    source["bar_interval"] = "5m"
    source["bar_source"] = "native_5m_unverified"
    entry_records_path.write_text(json.dumps(source), encoding="utf-8")
    calendar_path = _write_calendar(
        tmp_path / "calendar.json",
        ["2026-07-10", "2026-07-13"],
        records_path=entry_records_path,
    )

    with pytest.raises(ValueError, match="bar source"):
        entry_audit.audit_nonstationary_entry(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=tmp_path / "selection",
            entry_records_path=entry_records_path,
            trading_calendar_path=calendar_path,
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="5m",
            min_selected=1,
        )


def test_entry_file_audit_rejects_missing_candidate_source_identity(monkeypatch, tmp_path):
    monkeypatch.setattr(entry_audit, "_load_samples", lambda *args: [_row("2026-07-10", "000001", 1.0)])
    entry_records_path = _write_entry_records(tmp_path / "records.json", [])
    source = json.loads(entry_records_path.read_text(encoding="utf-8"))
    del source["parameters"]["candidate_source_identity"]
    entry_records_path.write_text(json.dumps(source), encoding="utf-8")
    calendar_path = _write_calendar(
        tmp_path / "calendar.json",
        ["2026-07-10", "2026-07-13"],
        records_path=entry_records_path,
    )

    with pytest.raises(ValueError, match="candidate source identity"):
        entry_audit.audit_nonstationary_entry(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=tmp_path / "selection",
            entry_records_path=entry_records_path,
            trading_calendar_path=calendar_path,
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="1m",
            min_selected=1,
        )


def test_entry_file_audit_revalidates_current_candidate_root(monkeypatch, tmp_path):
    monkeypatch.setattr(entry_audit, "_load_samples", lambda *args: [_row("2026-07-10", "000001", 1.0)])
    monkeypatch.setattr(
        entry_audit,
        "revalidate_records_candidate_source_identity",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("current root manifest mismatch")),
    )
    entry_records_path = _write_entry_records(tmp_path / "records.json", [])
    calendar_path = _write_calendar(
        tmp_path / "calendar.json",
        ["2026-07-10", "2026-07-13"],
        records_path=entry_records_path,
    )

    with pytest.raises(ValueError, match="current root manifest"):
        entry_audit.audit_nonstationary_entry(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=tmp_path / "selection",
            entry_records_path=entry_records_path,
            trading_calendar_path=calendar_path,
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="1m",
            min_selected=1,
        )


def test_entry_file_audit_revalidates_current_selection_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(entry_audit, "_load_samples", lambda *args: [_row("2026-07-10", "000001", 1.0)])
    monkeypatch.setattr(
        entry_audit,
        "revalidate_records_selection_source_identity",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("selection source manifest SHA mismatch")),
        raising=False,
    )
    entry_records_path = _write_entry_records(tmp_path / "records.json", [])

    with pytest.raises(ValueError, match="selection source manifest SHA mismatch"):
        entry_audit.audit_nonstationary_entry(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=tmp_path / "selection",
            entry_records_path=entry_records_path,
            trading_calendar_path=_write_calendar(
                tmp_path / "calendar.json",
                ["2026-07-10", "2026-07-13"],
                records_path=entry_records_path,
            ),
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="1m",
            min_selected=1,
        )


def test_entry_file_audit_requires_exact_strategy_version_set(tmp_path):
    entry_records_path = _write_entry_records(tmp_path / "records.json", [])
    source = json.loads(entry_records_path.read_text(encoding="utf-8"))
    source["parameters"]["version_ids"].append("v29_overfit")
    entry_records_path.write_text(json.dumps(source), encoding="utf-8")

    with pytest.raises(ValueError, match="exact strategy versions"):
        entry_audit._load_causal_entry_records_report(
            entry_records_path,
            as_of="2026-07-13",
            timeframe="1m",
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
        )


def test_entry_records_loader_binds_sha_to_parsed_bytes(tmp_path, monkeypatch):
    entry_records_path = _write_entry_records(tmp_path / "records.json", [])
    first_bytes = entry_records_path.read_bytes()
    expected_sha256 = hashlib.sha256(first_bytes).hexdigest()
    original_read_bytes = Path.read_bytes

    def read_then_replace(self):
        payload = original_read_bytes(self)
        if self == entry_records_path:
            self.write_text("{}", encoding="utf-8")
        return payload

    monkeypatch.setattr(Path, "read_bytes", read_then_replace)

    report, actual_sha256 = entry_audit._load_causal_entry_records_report(
        entry_records_path,
        as_of="2026-07-13",
        timeframe="1m",
        candidate_root=tmp_path / "candidates",
        candidate_source_root=tmp_path / "source",
    )

    assert report["records"] == []
    assert actual_sha256 == expected_sha256


def test_entry_file_audit_rebuilds_record_cohort(monkeypatch, tmp_path):
    monkeypatch.setattr(entry_audit, "_load_samples", lambda *args: [_row("2026-07-10", "000001", 1.0)])
    monkeypatch.setattr(
        entry_audit,
        "validate_paper_record_cohort",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("entry cohort missing candidate selection")),
        raising=False,
    )
    entry_records_path = _write_entry_records(tmp_path / "records.json", [])

    with pytest.raises(ValueError, match="entry cohort missing"):
        entry_audit.audit_nonstationary_entry(
            candidate_root=tmp_path / "candidates",
            candidate_source_root=tmp_path / "source",
            selection_validation_root=tmp_path / "selection",
            entry_records_path=entry_records_path,
            trading_calendar_path=_write_calendar(
                tmp_path / "calendar.json",
                ["2026-07-10", "2026-07-13"],
                records_path=entry_records_path,
            ),
            output_dir=tmp_path / "output",
            as_of="2026-07-13",
            timeframe="1m",
            min_selected=1,
        )


def test_entry_perturbation_requires_both_variants_to_have_valid_samples():
    version = StrategyVersion(
        "test",
        "test",
        (FactorCondition("signal", ">=", 10.0),),
    )
    rows = [
        {"signal": 10.0, "forward_return_pct": 1.0},
        {"signal": 10.0, "forward_return_pct": 1.0},
        {"signal": 12.0, "forward_return_pct": 1.0},
    ]

    report = _perturbation_report(rows, version, min_selected=4)

    assert report["variant_count"] == 2
    assert report["valid_variant_count"] == 1
    assert report["all_variants_valid"] is False


def test_entry_factor_correlation_rejects_nonfinite_values():
    version = StrategyVersion(
        "test",
        "test",
        (
            FactorCondition("left", ">=", 0.0),
            FactorCondition("right", ">=", 0.0),
        ),
    )
    rows = [{"left": float("nan"), "right": value} for value in range(5)]

    report = _factor_correlation(rows, version)

    assert report["expected_pair_count"] == 1
    assert report["pair_count"] == 0
    assert report["pair_coverage_rate"] == 0.0


def test_load_samples_propagates_top_level_sample_mode(tmp_path):
    path = tmp_path / "2026-06-28" / "top30_candidates.intraday_backfilled.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"as_of": "2026-06-28", "sample_mode": True, "candidates": [{"code": "600001"}]}),
        encoding="utf-8",
    )

    rows = _load_samples(tmp_path, None, None, None)

    assert rows[0]["_sample_mode"] is True


def test_entry_markdown_labels_observed_tail_and_reports_date_coverage():
    tail_dates = _observed_tail_dates()
    report = {
        "as_of": tail_dates[-1],
        "calendar_source": {"dates": tail_dates},
        "label_source": {
            "revalidated_candidate_source_identity": {
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
        "versions": {},
    }

    markdown = entry_audit._markdown(report)

    assert "observed_evaluation_tail" in markdown
    assert "blind: `false`" in markdown
    assert "eligible_for_oos_claim: `false`" in markdown
    assert "source document coverage: `18/20` (`0.9`)" in markdown
    assert "complete candidate coverage: `5/20` (`0.25`)" in markdown
    assert "Holdout avg" not in markdown
