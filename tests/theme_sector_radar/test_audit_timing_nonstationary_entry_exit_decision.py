import hashlib
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

import scripts.audit_timing_nonstationary_entry_exit_decision as decision_audit
from theme_sector_radar.data.trading_calendar import build_trading_calendar_report
from scripts.audit_timing_nonstationary_entry_exit_decision import (
    _entry_decisions,
    _entry_perturbation_gate,
    _entry_regime_gate,
    _entry_redundancy_gate,
    _entry_walk_forward_gate,
    _profit_fill_gate,
    _profit_long_history_gate,
    _profit_regime_gate,
    _profit_threshold_robustness_gate,
    _profit_walk_forward_gate,
    _report_provenance,
    _stop_fill_gate,
    _stop_decisions,
    build_dynamic_recommendations,
    evaluate_candidate_hard_gates,
    validate_profit_report_cohort,
    validate_report_identity,
)


PASSING_GATES = {
    "recent_60": {"status": "pass"},
    "recent_120": {"status": "pass"},
    "holdout": {"status": "pass"},
    "regime": {"status": "pass"},
    "perturbation": {"status": "pass"},
    "concentration": {"status": "pass"},
    "long_history_veto": {"status": "pass"},
    "next_bar_fill": {"status": "pass"},
    "friction": {"status": "pass"},
}


@pytest.fixture(autouse=True)
def _allow_explicit_in_memory_record_fixtures(monkeypatch):
    production_validate_paper_records = decision_audit.validate_paper_records_report
    monkeypatch.setattr(
        decision_audit,
        "validate_paper_records_report",
        lambda report, *, context, **kwargs: production_validate_paper_records(
            report,
            context=context,
            require_durable_entry_bars_source=False,
        ),
    )


def _paper_records_report(records=None):
    return {
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
        "entry_bars_source_identity": {
            "status": "validated",
            "source_kind": "in_memory_test_fixture",
            "sha256": "b" * 64,
        },
        "records": list(records or []),
    }


def test_final_report_provenance_requires_durable_manifest(monkeypatch, tmp_path):
    report_path = tmp_path / "audit.json"
    report_path.write_text("{}", encoding="utf-8")
    records_path = tmp_path / "records.json"
    records_path.write_text(json.dumps(_paper_records_report()), encoding="utf-8")
    report = {
        "label_source": {
            "entry_records_path": str(records_path),
            "entry_records_sha256": hashlib.sha256(records_path.read_bytes()).hexdigest(),
        }
    }

    def capture(_report, *, context, require_durable_entry_bars_source):
        assert context.startswith("upstream records report")
        assert require_durable_entry_bars_source is True
        raise RuntimeError("durable flag captured")

    monkeypatch.setattr(decision_audit, "validate_paper_records_report", capture)
    with pytest.raises(RuntimeError, match="durable flag captured"):
        _report_provenance(report_path, report)


def test_final_decision_script_supports_direct_cli_execution():
    project_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, str(project_root / "scripts" / "audit_timing_nonstationary_entry_exit_decision.py"), "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--selection-validation-root" in result.stdout
    assert "--expected-entry-1m-sha256" in result.stdout
    assert "--expected-profit-5m-3-sha256" in result.stdout
    assert "--expected-stop-5m-sha256" in result.stdout
    assert "--expected-calendar-path" in result.stdout
    assert "--expected-calendar-sha256" in result.stdout
    assert "--expected-records-manifest" in result.stdout
    assert "--expected-records-manifest-sha256" in result.stdout


@pytest.mark.parametrize(
    ("entry_reports", "profit_reports", "stop_reports", "message"),
    [
        ({"1m": Path("entry")}, {"1m": {2.0: Path("p2"), 3.0: Path("p3")}, "5m": {2.0: Path("p2"), 3.0: Path("p3")}}, {"1m": Path("stop"), "5m": Path("stop")}, "entry report topology"),
        ({"1m": Path("entry"), "5m": Path("entry")}, {"1m": {2.0: Path("p2")}, "5m": {2.0: Path("p2"), 3.0: Path("p3")}}, {"1m": Path("stop"), "5m": Path("stop")}, "profit report topology"),
        ({"1m": Path("entry"), "5m": Path("entry")}, {"1m": {2.0: Path("p2"), 3.0: Path("p3")}, "5m": {2.0: Path("p2"), 3.0: Path("p3")}}, {"1m": Path("stop"), "15m": Path("stop")}, "stop report topology"),
    ],
)
def test_final_decision_requires_exact_report_topology(entry_reports, profit_reports, stop_reports, message):
    with pytest.raises(ValueError, match=message):
        decision_audit.validate_input_topology(
            entry_reports=entry_reports,
            profit_reports=profit_reports,
            stop_reports=stop_reports,
        )


def test_final_decision_accepts_only_two_plus_four_plus_two_topology():
    decision_audit.validate_input_topology(
        entry_reports={"1m": Path("entry"), "5m": Path("entry")},
        profit_reports={
            "1m": {2.0: Path("p2"), 3.0: Path("p3")},
            "5m": {2.0: Path("p2"), 3.0: Path("p3")},
        },
        stop_reports={"1m": Path("stop"), "5m": Path("stop")},
    )


def test_final_decision_rejects_audit_changed_after_caller_bound_sha(tmp_path):
    path = tmp_path / "entry-audit.json"
    path.write_text('{"metric":1}', encoding="utf-8")
    expected_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    path.write_text('{"metric":999}', encoding="utf-8")

    with pytest.raises(ValueError, match="caller-bound audit SHA mismatch"):
        decision_audit.validate_expected_report_sha256(
            path,
            expected_sha256,
            context="entry 1m",
        )


def test_final_decision_parses_the_same_bytes_bound_to_caller_sha(tmp_path, monkeypatch):
    path = tmp_path / "entry-audit.json"
    first_bytes = b'{"metric":1}'
    path.write_bytes(first_bytes)
    expected_sha256 = hashlib.sha256(first_bytes).hexdigest()
    original_read_bytes = Path.read_bytes

    def read_then_replace(self):
        payload = original_read_bytes(self)
        self.write_bytes(b'{"metric":999}')
        return payload

    monkeypatch.setattr(Path, "read_bytes", read_then_replace)

    report, actual_sha256 = decision_audit._load_expected_report(
        path,
        expected_sha256,
        context="entry 1m",
    )

    assert report == {"metric": 1}
    assert actual_sha256 == expected_sha256


def test_final_decision_expected_sha_topology_is_exact():
    with pytest.raises(ValueError, match="expected entry SHA topology"):
        decision_audit.validate_expected_report_sha_topology(
            entry_sha256={"1m": "a" * 64},
            profit_sha256={
                "1m": {2.0: "b" * 64, 3.0: "c" * 64},
                "5m": {2.0: "d" * 64, 3.0: "e" * 64},
            },
            stop_sha256={"1m": "f" * 64, "5m": "0" * 64},
        )


def test_observed_evaluation_tail_cannot_pass_as_blind_holdout():
    gate = decision_audit._governed_holdout_gate(
        {
            "status": "observed_evaluation_tail",
            "blind": False,
            "eligible_for_oos_claim": False,
        },
        {"status": "pass", "reason": "positive observed return"},
    )

    assert gate["status"] == "insufficient"
    assert gate["evidence"]["observed_metric_gate"]["status"] == "pass"


def test_candidate_date_coverage_gate_requires_all_three_complete_windows():
    passing = {
        "date_count": 60,
        "source_document_date_count": 60,
        "complete_candidate_date_count": 60,
        "source_document_date_coverage_rate": 1.0,
        "complete_candidate_date_coverage_rate": 1.0,
        "candidate_date_coverage_status": "ok",
    }
    windows = {
        "recent_60": dict(passing),
        "recent_120": dict(
            passing,
            date_count=120,
            source_document_date_count=120,
            complete_candidate_date_count=120,
        ),
        "holdout": {
            "date_count": 20,
            "source_document_date_count": 18,
            "complete_candidate_date_count": 5,
            "source_document_date_coverage_rate": 0.9,
            "complete_candidate_date_coverage_rate": 0.25,
            "candidate_date_coverage_status": "insufficient",
        },
    }

    gate = decision_audit._candidate_date_coverage_gate(windows)

    assert gate["status"] == "insufficient"
    assert gate["evidence"]["incomplete_windows"] == ["holdout"]


def test_entry_window_gate_requires_complete_candidate_date_coverage():
    candidate = {
        "by_window": {
            "recent_60": {
                "window_status": "ok",
                "is_valid": True,
                "selected_avg_return_pct": 2.0,
                "window_date_count": 60,
                "source_document_date_count": 60,
                "complete_candidate_date_count": 15,
                "source_document_date_coverage_rate": 1.0,
                "complete_candidate_date_coverage_rate": 0.25,
                "candidate_date_coverage_status": "insufficient",
            }
        }
    }
    baseline = {
        "by_window": {
            "recent_60": {
                "window_status": "ok",
                "is_valid": True,
                "selected_avg_return_pct": 1.0,
            }
        }
    }

    gate = decision_audit._entry_window_gate(candidate, baseline, "recent_60")

    assert gate["status"] == "insufficient"
    assert gate["evidence"]["complete_candidate_date_count"] == 15
    assert gate["evidence"]["window_date_count"] == 60


def test_positive_tail_gate_reports_date_coverage_before_selected_sample_size():
    gate = decision_audit._positive_holdout_gate(
        {
            "window_status": "ok",
            "is_valid": False,
            "selected_count": 3,
            "window_date_count": 20,
            "source_document_date_count": 17,
            "complete_candidate_date_count": 5,
            "source_document_date_coverage_rate": 0.85,
            "complete_candidate_date_coverage_rate": 0.25,
            "candidate_date_coverage_status": "insufficient",
        }
    )

    assert gate["status"] == "insufficient"
    assert gate["evidence"]["complete_candidate_date_count"] == 5
    assert "selected_count" not in gate["evidence"]


@pytest.mark.parametrize(
    "failed_gate",
    ["recent_60", "recent_120", "holdout", "perturbation", "concentration", "long_history_veto"],
)
def test_hard_gate_failure_rejects_candidate(failed_gate):
    gates = {key: dict(value) for key, value in PASSING_GATES.items()}
    gates[failed_gate] = {"status": "fail", "reason": "test failure"}

    result = evaluate_candidate_hard_gates(
        candidate_id="candidate",
        candidate_type="entry",
        timeframe="1m",
        gates=gates,
        passing_status="champion",
    )

    assert result["decision_status"] == "observe"
    assert result["promotion_eligible"] is False
    assert failed_gate in result["failed_gates"]


def test_insufficient_gate_never_promotes_candidate():
    gates = {key: dict(value) for key, value in PASSING_GATES.items()}
    gates["recent_120"] = {"status": "insufficient", "reason": "only 82 training days"}

    result = evaluate_candidate_hard_gates(
        candidate_id="candidate",
        candidate_type="entry",
        timeframe="1m",
        gates=gates,
        passing_status="champion",
    )

    assert result["decision_status"] == "insufficient_evidence"
    assert result["promotion_eligible"] is False


def test_missing_or_unknown_required_gate_fails_closed():
    missing = {key: dict(value) for key, value in PASSING_GATES.items() if key != "regime"}
    missing_result = evaluate_candidate_hard_gates(
        candidate_id="candidate",
        candidate_type="entry",
        timeframe="1m",
        gates=missing,
        passing_status="champion",
    )
    unknown = {key: dict(value) for key, value in PASSING_GATES.items()}
    unknown["regime"] = {"status": "maybe"}
    unknown_result = evaluate_candidate_hard_gates(
        candidate_id="candidate",
        candidate_type="entry",
        timeframe="1m",
        gates=unknown,
        passing_status="champion",
    )

    assert missing_result["decision_status"] == "insufficient_evidence"
    assert "regime" in missing_result["insufficient_gates"]
    assert unknown_result["decision_status"] == "insufficient_evidence"


def test_report_identity_rejects_timeframe_and_threshold_mismatch():
    report = {
        "schema_version": "timing_nonstationary_profit_exit_audit.v1",
        "as_of": "2026-07-13",
        "timeframe": "1m",
        "parameters": {"applied_giveback_pct": 2.0},
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }

    validate_report_identity(
        report,
        schema="timing_nonstationary_profit_exit_audit.v1",
        as_of="2026-07-13",
        timeframe="1m",
        giveback_pct=2.0,
    )
    with pytest.raises(ValueError, match="timeframe"):
        validate_report_identity(report, schema=report["schema_version"], as_of="2026-07-13", timeframe="5m")
    with pytest.raises(ValueError, match="giveback"):
        validate_report_identity(report, schema=report["schema_version"], as_of="2026-07-13", timeframe="1m", giveback_pct=3.0)

    unsafe = dict(report)
    unsafe["paper_trading_only"] = False
    with pytest.raises(ValueError, match="paper-only"):
        validate_report_identity(unsafe, schema=report["schema_version"], as_of="2026-07-13", timeframe="1m")

    nested_instruction = dict(report)
    nested_instruction["evidence"] = {
        "orders": [{"side": "buy", "quantity": 100}]
    }
    with pytest.raises(ValueError, match="executable instruction"):
        validate_report_identity(
            nested_instruction,
            schema=report["schema_version"],
            as_of="2026-07-13",
            timeframe="1m",
        )


def test_report_provenance_binds_content_hash_and_cohort_identity(tmp_path):
    path = tmp_path / "report.json"
    path.write_text('{"value": 1}', encoding="utf-8")
    records_path = tmp_path / "records.json"
    records_path.write_text(json.dumps(_paper_records_report()), encoding="utf-8")
    records_sha256 = hashlib.sha256(records_path.read_bytes()).hexdigest()
    report = {
        "schema_version": "test.v1",
        "as_of": "2026-07-13",
        "timeframe": "1m",
        "snapshot_label": "unit",
        "calendar_source": {"sha256": "calendar-sha"},
        "candidate_source": {"candidate_root": "candidate-root"},
        "label_source": {
            "entry_records_path": str(records_path),
            "entry_records_sha256": records_sha256,
        },
    }

    provenance = _report_provenance(path, report)

    assert provenance["path"] == str(path)
    assert len(provenance["sha256"]) == 64
    assert provenance["schema_version"] == "test.v1"
    assert provenance["calendar_source"]["sha256"] == "calendar-sha"
    assert provenance["records_path"] == str(records_path)
    assert provenance["records_sha256"] == records_sha256


def test_report_provenance_rejects_records_outside_caller_bound_manifest(tmp_path):
    path = tmp_path / "report.json"
    path.write_text('{"value": 1}', encoding="utf-8")
    records_path = tmp_path / "records.json"
    records_path.write_text(json.dumps(_paper_records_report()), encoding="utf-8")
    records_sha256 = hashlib.sha256(records_path.read_bytes()).hexdigest()
    report = {
        "records_path": str(records_path),
        "records_sha256": records_sha256,
    }

    with pytest.raises(ValueError, match="caller-bound records path"):
        _report_provenance(
            path,
            report,
            expected_records_path=tmp_path / "other-records.json",
            expected_records_sha256=records_sha256,
        )


def test_caller_bound_records_manifest_requires_strict_paper_guards(tmp_path):
    path = tmp_path / "records-manifest.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "timing_final_records_manifest.v1",
                "records": {
                    source_id: {"path": f"{source_id}.json", "sha256": "a" * 64}
                    for source_id in decision_audit.EXPECTED_RECORD_SOURCE_IDS
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="paper_trading_only"):
        decision_audit._load_expected_records_manifest(
            path,
            expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )


def test_report_provenance_collects_entry_path_manifest_without_serializing_it(tmp_path):
    path = tmp_path / "report.json"
    path.write_text('{"value": 1}', encoding="utf-8")
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _paper_records_report(
                [
                    {
                        "signal_date": "2026-07-01",
                        "entry_date": "2026-07-02",
                        "code": "600001",
                        "causal_entry_valid": True,
                        "entry_bars_sha256": "a" * 64,
                        "paper_trading_only": True,
                        "no_execution_signals": True,
                        "does_not_modify_official_scores": True,
                    }
                ]
            )
        ),
        encoding="utf-8",
    )
    manifest = {}
    report = {
        "schema_version": "test.v1",
        "timeframe": "1m",
        "label_source": {
            "entry_records_path": str(records_path),
            "entry_records_sha256": hashlib.sha256(records_path.read_bytes()).hexdigest(),
        },
    }

    provenance = _report_provenance(path, report, entry_path_manifest_out=manifest)

    assert manifest == {
        ("2026-07-01", "2026-07-02", "600001"): "a" * 64
    }
    assert "entry_path_manifest" not in provenance


def _entry_path_audit_source(
    tmp_path,
    label,
    timeframe,
    path_sha256,
    *,
    records_path=None,
):
    records_path = records_path or tmp_path / f"{label}.records.json"
    path_field = (
        "source_1m_bars_sha256" if timeframe == "5m" else "entry_bars_sha256"
    )
    if not records_path.exists():
        records_path.write_text(
            json.dumps(
                _paper_records_report(
                    [
                        {
                            "signal_date": "2026-07-01",
                            "entry_date": "2026-07-02",
                            "code": "600001",
                            "causal_entry_valid": True,
                            path_field: path_sha256,
                            "paper_trading_only": True,
                            "no_execution_signals": True,
                            "does_not_modify_official_scores": True,
                        }
                    ]
                )
            ),
            encoding="utf-8",
        )
    report_path = tmp_path / f"{label}.audit.json"
    report_path.write_text(
        json.dumps(
            {
                "timeframe": timeframe,
                "records_path": str(records_path),
                "records_sha256": hashlib.sha256(records_path.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    return report_path, hashlib.sha256(report_path.read_bytes()).hexdigest()


def _entry_path_orchestrator_inputs(
    tmp_path,
    *,
    conflicting_source=None,
    with_stop=False,
    detached_stop_records=False,
):
    sources = {
        label: _entry_path_audit_source(
            tmp_path,
            label,
            timeframe,
            "b" * 64 if label == conflicting_source else "a" * 64,
        )
        for label, timeframe in (
            ("entry_1m", "1m"),
            ("entry_5m", "5m"),
            ("profit_1m_2", "1m"),
            ("profit_1m_3", "1m"),
            ("profit_5m_2", "5m"),
            ("profit_5m_3", "5m"),
        )
    }
    entry_records_paths = {
        timeframe: Path(
            json.loads(sources[f"entry_{timeframe}"][0].read_text(encoding="utf-8"))[
                "records_path"
            ]
        )
        for timeframe in ("1m", "5m")
    }
    stop_sources = {
        timeframe: _entry_path_audit_source(
            tmp_path,
            f"stop_{timeframe}",
            timeframe,
            "a" * 64,
            records_path=(
                None if detached_stop_records else entry_records_paths[timeframe]
            ),
        )
        for timeframe in ("1m", "5m")
    }

    def records_identity(source):
        report = json.loads(source[0].read_text(encoding="utf-8"))
        return {
            "path": report["records_path"],
            "sha256": report["records_sha256"],
        }

    expected_records_provenance = {
        "entry:1m": records_identity(sources["entry_1m"]),
        "entry:5m": records_identity(sources["entry_5m"]),
        "profit:1m:2pct": records_identity(sources["profit_1m_2"]),
        "profit:1m:3pct": records_identity(sources["profit_1m_3"]),
        "profit:5m:2pct": records_identity(sources["profit_5m_2"]),
        "profit:5m:3pct": records_identity(sources["profit_5m_3"]),
        "stop:1m": records_identity(sources["entry_1m"]),
        "stop:5m": records_identity(sources["entry_5m"]),
    }
    return {
        "entry_reports": {
            "1m": sources["entry_1m"][0],
            "5m": sources["entry_5m"][0],
        },
        "profit_reports": {
            "1m": {
                2.0: sources["profit_1m_2"][0],
                3.0: sources["profit_1m_3"][0],
            },
            "5m": {
                2.0: sources["profit_5m_2"][0],
                3.0: sources["profit_5m_3"][0],
            },
        },
        "stop_reports": {
            timeframe: stop_sources[timeframe][0]
            if with_stop
            else tmp_path / f"missing_stop_{timeframe}"
            for timeframe in ("1m", "5m")
        },
        "expected_entry_report_sha256": {
            "1m": sources["entry_1m"][1],
            "5m": sources["entry_5m"][1],
        },
        "expected_profit_report_sha256": {
            "1m": {
                2.0: sources["profit_1m_2"][1],
                3.0: sources["profit_1m_3"][1],
            },
            "5m": {
                2.0: sources["profit_5m_2"][1],
                3.0: sources["profit_5m_3"][1],
            },
        },
        "expected_stop_report_sha256": {
            timeframe: stop_sources[timeframe][1] if with_stop else ("1" if timeframe == "1m" else "2") * 64
            for timeframe in ("1m", "5m")
        },
        "candidate_roots": {
            "1m": tmp_path / "candidate_1m",
            "5m": tmp_path / "candidate_5m",
        },
        "candidate_source_root": tmp_path / "source",
        "selection_validation_root": tmp_path / "selection",
        "expected_calendar_path": tmp_path / "calendar.json",
        "expected_calendar_sha256": "a" * 64,
        "expected_records_provenance": expected_records_provenance,
        "output_dir": tmp_path / "out",
        "as_of": "2026-07-13",
    }


def _stub_orchestrator_report_validation(monkeypatch):
    monkeypatch.setattr(decision_audit, "validate_report_identity", lambda *args, **kwargs: None)
    monkeypatch.setattr(decision_audit, "validate_report_strategy_set", lambda *args, **kwargs: None)
    monkeypatch.setattr(decision_audit, "validate_profit_report_cohort", lambda *args, **kwargs: None)
    monkeypatch.setattr(decision_audit, "_entry_decisions", lambda *args, **kwargs: [])
    monkeypatch.setattr(decision_audit, "_profit_decisions", lambda *args, **kwargs: [])


@pytest.mark.parametrize(
    "conflicting_source",
    [
        "entry_1m",
        "entry_5m",
        "profit_1m_2",
        "profit_1m_3",
        "profit_5m_2",
        "profit_5m_3",
    ],
)
def test_final_orchestrator_rejects_each_six_record_path_mismatch(
    monkeypatch,
    tmp_path,
    conflicting_source,
):
    _stub_orchestrator_report_validation(monkeypatch)
    real_merge = decision_audit.merge_entry_path_manifests
    merge_counts = []

    def merge_exactly_six(manifests, *, context):
        merge_counts.append(len(manifests))
        return real_merge(manifests, context=context)

    monkeypatch.setattr(decision_audit, "merge_entry_path_manifests", merge_exactly_six)

    with pytest.raises(ValueError, match="final upstream records entry path mismatch"):
        decision_audit.audit_nonstationary_entry_exit_decision(
            **_entry_path_orchestrator_inputs(
                tmp_path,
                conflicting_source=conflicting_source,
            )
        )
    assert merge_counts == [6]


def test_final_orchestrator_keeps_six_path_manifests_transient(monkeypatch, tmp_path):
    _stub_orchestrator_report_validation(monkeypatch)
    monkeypatch.setattr(decision_audit, "_stop_decisions", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        decision_audit,
        "_evaluation_tail_summary",
        lambda reports: {"status": "observed_evaluation_tail", "sources": {}},
    )

    def validate_sources(*args, **kwargs):
        kwargs["source_snapshot_identity"].update({"manifest_sha256": "a" * 64})
        return {"status": "validated"}

    monkeypatch.setattr(decision_audit, "validate_cross_report_source_identity", validate_sources)
    monkeypatch.setattr(
        decision_audit,
        "validate_cross_timeframe_source_identity",
        lambda *args, **kwargs: None,
    )
    real_merge = decision_audit.merge_entry_path_manifests
    merge_counts = []

    def merge_exactly_six(manifests, *, context):
        merge_counts.append(len(manifests))
        return real_merge(manifests, context=context)

    monkeypatch.setattr(decision_audit, "merge_entry_path_manifests", merge_exactly_six)

    result = decision_audit.audit_nonstationary_entry_exit_decision(
        **_entry_path_orchestrator_inputs(tmp_path, with_stop=True)
    )

    assert merge_counts == [6]
    assert set(result["report"]["source_reports"]["entry"]) == {"1m", "5m"}
    assert sum(
        len(items) for items in result["report"]["source_reports"]["profit"].values()
    ) == 4
    assert set(result["report"]["source_reports"]["stop"]) == {"1m", "5m"}
    assert "entry_path_manifest" not in json.dumps(result["report"], sort_keys=True)


def test_final_orchestrator_rejects_stop_audit_with_detached_entry_records(
    monkeypatch,
    tmp_path,
):
    _stub_orchestrator_report_validation(monkeypatch)
    monkeypatch.setattr(decision_audit, "_stop_decisions", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        decision_audit,
        "_evaluation_tail_summary",
        lambda reports: {"status": "observed_evaluation_tail", "sources": {}},
    )

    def validate_sources(*args, **kwargs):
        kwargs["source_snapshot_identity"].update({"manifest_sha256": "a" * 64})
        return {"status": "validated"}

    monkeypatch.setattr(
        decision_audit,
        "validate_cross_report_source_identity",
        validate_sources,
    )
    monkeypatch.setattr(
        decision_audit,
        "validate_cross_timeframe_source_identity",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(ValueError, match="caller-bound records path"):
        decision_audit.audit_nonstationary_entry_exit_decision(
            **_entry_path_orchestrator_inputs(
                tmp_path,
                with_stop=True,
                detached_stop_records=True,
            )
        )


def test_final_orchestrator_rejects_conflicting_stop_records_aliases(
    monkeypatch,
    tmp_path,
):
    _stub_orchestrator_report_validation(monkeypatch)
    monkeypatch.setattr(decision_audit, "_stop_decisions", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        decision_audit,
        "_evaluation_tail_summary",
        lambda reports: {"status": "observed_evaluation_tail", "sources": {}},
    )

    def validate_sources(*args, **kwargs):
        kwargs["source_snapshot_identity"].update({"manifest_sha256": "a" * 64})
        return {"status": "validated"}

    monkeypatch.setattr(
        decision_audit,
        "validate_cross_report_source_identity",
        validate_sources,
    )
    monkeypatch.setattr(
        decision_audit,
        "validate_cross_timeframe_source_identity",
        lambda *args, **kwargs: None,
    )
    inputs = _entry_path_orchestrator_inputs(tmp_path, with_stop=True)
    stop_path = inputs["stop_reports"]["1m"]
    stop_report = json.loads(stop_path.read_text(encoding="utf-8"))
    detached_records = tmp_path / "detached-stop-alias.records.json"
    detached_records.write_text(json.dumps(_paper_records_report()), encoding="utf-8")
    stop_report["entry_records_path"] = str(detached_records)
    stop_report["entry_records_sha256"] = hashlib.sha256(
        detached_records.read_bytes()
    ).hexdigest()
    stop_path.write_text(json.dumps(stop_report), encoding="utf-8")
    inputs["expected_stop_report_sha256"]["1m"] = hashlib.sha256(
        stop_path.read_bytes()
    ).hexdigest()

    with pytest.raises(ValueError, match="conflicting upstream records provenance aliases"):
        decision_audit.audit_nonstationary_entry_exit_decision(**inputs)


def test_report_provenance_rejects_executable_fields_in_upstream_records(tmp_path):
    path = tmp_path / "report.json"
    path.write_text('{"value": 1}', encoding="utf-8")
    records_path = tmp_path / "records.json"
    records_path.write_text(
        json.dumps(
            _paper_records_report(
                [
                    {
                        "factor_exit_triggers": {"entry_price": 10.0},
                        "entry_bars": [
                            {"orders": [{"side": "buy", "quantity": 1}]}
                        ],
                        "paper_trading_only": True,
                        "no_execution_signals": True,
                        "does_not_modify_official_scores": True,
                    }
                ]
            )
        ),
        encoding="utf-8",
    )
    report = {
        "label_source": {
            "entry_records_path": str(records_path),
            "entry_records_sha256": hashlib.sha256(records_path.read_bytes()).hexdigest(),
        }
    }

    with pytest.raises(ValueError, match="executable instruction fields"):
        _report_provenance(path, report)


@pytest.mark.parametrize(
    ("scope", "field"),
    [
        ("report", "paper_trading_only"),
        ("report", "no_execution_signals"),
        ("report", "does_not_modify_official_scores"),
        ("record", "paper_trading_only"),
        ("record", "no_execution_signals"),
        ("record", "does_not_modify_official_scores"),
    ],
)
def test_report_provenance_rejects_unsafe_upstream_records_guards(
    tmp_path,
    scope,
    field,
):
    path = tmp_path / "report.json"
    path.write_text('{"value": 1}', encoding="utf-8")
    record = {
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    records_report = _paper_records_report([record])
    target = records_report if scope == "report" else record
    target[field] = False
    records_path = tmp_path / "records.json"
    records_path.write_text(json.dumps(records_report), encoding="utf-8")
    report = {
        "label_source": {
            "entry_records_path": str(records_path),
            "entry_records_sha256": hashlib.sha256(records_path.read_bytes()).hexdigest(),
        }
    }

    with pytest.raises(ValueError, match=field):
        _report_provenance(path, report)


def test_report_provenance_rejects_missing_upstream_records_identity(tmp_path):
    path = tmp_path / "synthetic-audit.json"
    path.write_text('{"value": 1}', encoding="utf-8")

    with pytest.raises(ValueError, match="upstream records provenance is required"):
        _report_provenance(path, {"schema_version": "test.v1"})


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda reports: reports["profit:2pct"]["candidate_source"]["candidate_source_identity"].update(
                manifest_sha256="f" * 64
            ),
            "manifest",
        ),
        (
            lambda reports: reports["stop"]["candidate_source_identity"].update(source_root="other-source"),
            "source root",
        ),
        (
            lambda reports: reports["entry"].update(candidate_root="other-candidates"),
            "candidate root",
        ),
        (
            lambda reports: reports["profit:3pct"]["calendar_source"].update(sha256="e" * 64),
            "calendar",
        ),
        (
            lambda reports: reports["profit:3pct"]["calendar_source"].update(
                dates=["2026-07-01"]
            ),
            "calendar dates",
        ),
        (
            lambda reports: reports["profit:3pct"]["calendar_source"].update(
                source="other-calendar"
            ),
            "calendar source",
        ),
        (
            lambda reports: reports["profit:3pct"]["calendar_source"].update(
                requested_start="2026-02-01"
            ),
            "calendar requested start",
        ),
        (
            lambda reports: reports["profit:3pct"]["calendar_source"].update(
                requested_end="2026-07-12"
            ),
            "calendar requested end",
        ),
        (
            lambda reports: reports["entry"]["label_source"]["revalidated_candidate_source_identity"].update(
                document_dates=["2026-07-01"]
            ),
            "document dates",
        ),
        (
            lambda reports: reports["stop"]["candidate_source_identity"].update(
                complete_candidate_dates=[]
            ),
            "complete candidate dates",
        ),
        (
            lambda reports: reports["profit:2pct"]["candidate_source"].update(
                selection_source_identity={
                    "status": "validated",
                    "selection_validation_root": "other-selection",
                    "document_count": 1,
                    "document_dates": ["2026-07-01"],
                    "manifest_sha256": "f" * 64,
                }
            ),
            "selection source",
        ),
    ],
)
def test_final_decision_revalidates_current_manifest_and_cross_report_sources(
    monkeypatch,
    tmp_path,
    mutate,
    match,
):
    candidate_root = tmp_path / "candidates"
    source_root = tmp_path / "source"
    selection_root = tmp_path / "selection"
    candidate_root.mkdir()
    source_root.mkdir()
    selection_root.mkdir()
    calendar_path = tmp_path / "calendar.json"
    calendar_report = build_trading_calendar_report(
        ["2026-07-01", "2026-07-02"],
        source="unit-exchange-calendar",
        requested_start="2026-07-01",
        requested_end="2026-07-13",
    )
    calendar_path.write_text(json.dumps(calendar_report), encoding="utf-8")
    calendar_sha = hashlib.sha256(calendar_path.read_bytes()).hexdigest()
    current_identity = {
        "status": "validated",
        "candidate_root": str(candidate_root),
        "source_root": str(source_root),
        "bar_interval": "1m",
        "bar_source": "complete_1m_session",
        "document_count": 2,
        "complete_candidate_count": 3,
        "invalid_candidate_count": 1,
        "document_dates": ["2026-07-01", "2026-07-02"],
        "complete_candidate_dates": ["2026-07-01"],
        "manifest_sha256": "a" * 64,
    }
    monkeypatch.setattr(
        decision_audit,
        "validate_candidate_root_identity",
        lambda root, *, source_root, timeframe, start, end: dict(current_identity),
        raising=False,
    )
    current_selection_identity = {
        "status": "validated",
        "selection_validation_root": str(selection_root),
        "start": "2026-07-01",
        "end": "2026-07-13",
        "document_count": 1,
        "document_dates": ["2026-07-01"],
        "manifest_sha256": "c" * 64,
    }
    monkeypatch.setattr(
        decision_audit,
        "validate_selection_source_identity",
        lambda root, *, start, end: dict(current_selection_identity),
        raising=False,
    )

    def identity():
        return dict(current_identity)

    calendar = {
        "path": str(calendar_path),
        "sha256": calendar_sha,
        "dates": calendar_report["dates"],
        "source": calendar_report["source"],
        "requested_start": calendar_report["requested_start"],
        "requested_end": calendar_report["requested_end"],
    }
    reports = {
        "entry": {
            "schema_version": "timing_nonstationary_entry_audit.v1",
            "candidate_root": str(candidate_root),
            "calendar_source": dict(calendar),
            "label_source": {
                "revalidated_candidate_source_identity": identity(),
                "revalidated_selection_source_identity": dict(current_selection_identity),
            },
        },
        "profit:2pct": {
            "schema_version": "timing_nonstationary_profit_exit_audit.v1",
            "calendar_source": dict(calendar),
            "candidate_source": {
                "candidate_root": str(candidate_root),
                "candidate_source_identity": identity(),
                "selection_source_identity": dict(current_selection_identity),
            },
        },
        "profit:3pct": {
            "schema_version": "timing_nonstationary_profit_exit_audit.v1",
            "calendar_source": dict(calendar),
            "candidate_source": {
                "candidate_root": str(candidate_root),
                "candidate_source_identity": identity(),
                "selection_source_identity": dict(current_selection_identity),
            },
        },
        "stop": {
            "schema_version": "timing_nonstationary_stop_exit_audit.v1",
            "candidate_root": str(candidate_root),
            "calendar_source": dict(calendar),
            "candidate_source_identity": identity(),
            "selection_source_identity": dict(current_selection_identity),
        },
    }
    mutate(reports)

    with pytest.raises(ValueError, match=match):
        decision_audit.validate_cross_report_source_identity(
            reports,
            candidate_root=candidate_root,
            candidate_source_root=source_root,
            selection_validation_root=selection_root,
            timeframe="1m",
            as_of="2026-07-13",
            expected_calendar_path=calendar_path,
            expected_calendar_sha256=calendar_sha,
        )


@pytest.mark.parametrize("invalid_declared_count", [False, True])
def test_final_decision_accepts_fresh_manifest_and_matching_cross_report_sources(
    monkeypatch, tmp_path, invalid_declared_count
):
    candidate_root = tmp_path / "candidates"
    source_root = tmp_path / "source"
    selection_root = tmp_path / "selection"
    candidate_root.mkdir()
    source_root.mkdir()
    selection_root.mkdir()
    calendar_path = tmp_path / "calendar.json"
    calendar_report = build_trading_calendar_report(
        ["2026-07-01", "2026-07-02"],
        source="unit-exchange-calendar",
        requested_start="2026-07-01",
        requested_end="2026-07-13",
    )
    if invalid_declared_count:
        calendar_report["date_count"] = 99
    calendar_path.write_text(json.dumps(calendar_report), encoding="utf-8")
    calendar_sha = hashlib.sha256(calendar_path.read_bytes()).hexdigest()
    current_identity = {
        "status": "validated",
        "candidate_root": str(candidate_root),
        "source_root": str(source_root),
        "bar_interval": "1m",
        "bar_source": "complete_1m_session",
        "document_count": 2,
        "complete_candidate_count": 3,
        "invalid_candidate_count": 1,
        "document_dates": ["2026-07-01", "2026-07-02"],
        "complete_candidate_dates": ["2026-07-01"],
        "manifest_sha256": "a" * 64,
    }
    calls = []

    def validate(root, *, source_root, timeframe, start, end):
        calls.append((root, source_root, timeframe, start, end))
        return dict(current_identity)

    monkeypatch.setattr(decision_audit, "validate_candidate_root_identity", validate, raising=False)
    selection_calls = []
    current_selection_identity = {
        "status": "validated",
        "selection_validation_root": str(selection_root),
        "start": None,
        "end": "2026-07-13",
        "document_count": 1,
        "document_dates": ["2026-07-01"],
        "manifest_sha256": "c" * 64,
    }
    monkeypatch.setattr(
        decision_audit,
        "validate_selection_source_identity",
        lambda root, *, start, end: (
            selection_calls.append((root, start, end)) or dict(current_selection_identity)
        ),
        raising=False,
    )
    calendar = {
        "path": str(calendar_path),
        "sha256": calendar_sha,
        "dates": calendar_report["dates"],
        "source": calendar_report["source"],
        "requested_start": calendar_report["requested_start"],
        "requested_end": calendar_report["requested_end"],
    }
    reports = {
        "entry": {
            "schema_version": "timing_nonstationary_entry_audit.v1",
            "candidate_root": str(candidate_root),
            "calendar_source": dict(calendar),
            "label_source": {
                "revalidated_candidate_source_identity": dict(current_identity),
                "revalidated_selection_source_identity": dict(current_selection_identity),
            },
        },
        "profit:2pct": {
            "schema_version": "timing_nonstationary_profit_exit_audit.v1",
            "calendar_source": dict(calendar),
            "candidate_source": {
                "candidate_root": str(candidate_root),
                "candidate_source_identity": dict(current_identity),
                "selection_source_identity": dict(current_selection_identity),
            },
        },
        "profit:3pct": {
            "schema_version": "timing_nonstationary_profit_exit_audit.v1",
            "calendar_source": dict(calendar),
            "candidate_source": {
                "candidate_root": str(candidate_root),
                "candidate_source_identity": dict(current_identity),
                "selection_source_identity": dict(current_selection_identity),
            },
        },
        "stop": {
            "schema_version": "timing_nonstationary_stop_exit_audit.v1",
            "candidate_root": str(candidate_root),
            "calendar_source": dict(calendar),
            "candidate_source_identity": dict(current_identity),
            "selection_source_identity": dict(current_selection_identity),
        },
    }

    if invalid_declared_count:
        with pytest.raises(ValueError, match="date_count"):
            decision_audit.validate_cross_report_source_identity(
                reports,
                candidate_root=candidate_root,
                candidate_source_root=source_root,
                selection_validation_root=selection_root,
                timeframe="1m",
                as_of="2026-07-13",
                expected_calendar_path=calendar_path,
                expected_calendar_sha256=calendar_sha,
            )
        return

    with pytest.raises(ValueError, match="caller-bound calendar path"):
        decision_audit.validate_cross_report_source_identity(
            reports,
            candidate_root=candidate_root,
            candidate_source_root=source_root,
            selection_validation_root=selection_root,
            timeframe="1m",
            as_of="2026-07-13",
            expected_calendar_path=tmp_path / "other-calendar.json",
            expected_calendar_sha256=calendar_sha,
        )
    calls.clear()
    selection_calls.clear()

    result = decision_audit.validate_cross_report_source_identity(
        reports,
        candidate_root=candidate_root,
        candidate_source_root=source_root,
        selection_validation_root=selection_root,
        timeframe="1m",
        as_of="2026-07-13",
        expected_calendar_path=calendar_path,
        expected_calendar_sha256=calendar_sha,
    )

    assert calls == [(candidate_root, source_root, "1m", None, "2026-07-13")]
    assert selection_calls == [(selection_root, None, "2026-07-13")]
    assert result["current_candidate_source_identity"] == current_identity
    assert result["current_selection_source_identity"] == current_selection_identity
    assert result["calendar_source"] == {
        "path": str(calendar_path),
        "sha256": calendar_sha,
    }
    assert result["report_count"] == 4


@pytest.mark.parametrize(
    ("mismatch", "match"),
    [
        ("selection", "selection.*across timeframes"),
        ("calendar", "calendar.*across timeframes"),
        ("source", "source snapshot.*across timeframes"),
    ],
)
def test_final_decision_rejects_cross_timeframe_source_state_mismatch(
    mismatch, match
):
    validations = {
        timeframe: {
            "current_selection_source_identity": {
                "selection_validation_root": "selection-root",
                "start": "2026-01-01",
                "end": "2026-07-13",
                "manifest_sha256": "a" * 64,
                "document_count": 10,
                "document_dates": ["2026-07-01"],
            },
            "calendar_source": {"path": "calendar.json", "sha256": "b" * 64},
        }
        for timeframe in ("1m", "5m")
    }
    source_snapshots = {
        timeframe: {
            "source_root": "source-root",
            "manifest_sha256": "d" * 64,
            "document_count": 10,
            "document_dates": ["2026-07-01"],
        }
        for timeframe in ("1m", "5m")
    }
    if mismatch == "selection":
        validations["5m"]["current_selection_source_identity"][
            "manifest_sha256"
        ] = "c" * 64
    elif mismatch == "calendar":
        validations["5m"]["calendar_source"]["sha256"] = "c" * 64
    else:
        source_snapshots["5m"]["manifest_sha256"] = "c" * 64

    with pytest.raises(ValueError, match=match):
        decision_audit.validate_cross_timeframe_source_identity(
            validations,
            source_snapshots=source_snapshots,
        )


@pytest.mark.parametrize(
    ("schema", "report", "message"),
    [
        (
            "timing_nonstationary_entry_audit.v1",
            {"versions": {"v26_relative_watch_late_surge_cap": {}, "v31_expanded_balanced_tail_guard": {}, "v32_expanded_defensive_breakdown_guard": {}, "v29_extra": {}}},
            "entry strategy set",
        ),
        (
            "timing_nonstationary_profit_exit_audit.v1",
            {"candidates": {"paper_take_profit_protect_candidate": {}}},
            "profit strategy set",
        ),
        (
            "timing_nonstationary_stop_exit_audit.v1",
            {"factors": {"relative_weakness": {}, "money_flow_deterioration": {}}},
            "stop factor set",
        ),
    ],
)
def test_final_report_strategy_sets_are_exact(schema, report, message):
    with pytest.raises(ValueError, match=message):
        decision_audit.validate_report_strategy_set(report, schema=schema)


def test_recommendations_are_derived_from_decisions():
    decisions = [
        {"candidate_id": "profit:1m:2pct", "candidate_type": "profit_exit", "research_track_status": "challenger", "decision_status": "insufficient_evidence", "insufficient_gates": ["recent_120"], "failed_gates": []},
        {"candidate_id": "stop:1m:relative", "candidate_type": "stop_exit", "research_track_status": "observe", "decision_status": "observe", "insufficient_gates": [], "failed_gates": ["holdout"]},
    ]

    result = build_dynamic_recommendations(decisions)

    assert result["paper_stack"]["profit_exit"]["challengers"] == []
    assert result["paper_stack"]["profit_exit"]["insufficient"] == ["profit:1m:2pct"]
    assert result["blockers"]["recent_120"] == ["profit:1m:2pct"]


def test_entry_perturbation_gate_requires_two_valid_variants():
    gate = _entry_perturbation_gate(
        {
            "variant_count": 2,
            "valid_variant_count": 1,
            "all_variants_valid": False,
            "positive_variant_rate": 1.0,
        }
    )

    assert gate["status"] == "insufficient"


def test_entry_regime_gate_requires_latest_current_regime_only():
    regimes = {
        "strong": {"selected_count": 5, "selected_avg_return_pct": 1.0},
        "range": {"selected_count": 8, "selected_avg_return_pct": -1.0},
    }

    assert _entry_regime_gate(
        regimes,
        {"status": "ok", "date": "2026-07-13", "regime": "strong"},
    )["status"] == "pass"
    assert _entry_regime_gate(
        regimes,
        {"status": "insufficient", "date": "2026-07-13", "regime": None},
    )["status"] == "insufficient"


def test_entry_walk_forward_gate_requires_five_valid_positive_folds():
    folds = [
        {"is_valid": True, "selected_avg_return_pct": 1.0}
        for _ in range(4)
    ] + [{"is_valid": False, "selected_avg_return_pct": 1.0}]

    gate = _entry_walk_forward_gate({"fold_count": 5, "folds": folds})

    assert gate["status"] == "insufficient"


def test_entry_redundancy_gate_rejects_high_correlation_pairs():
    gate = _entry_redundancy_gate(
        {
            "pair_count": 3,
            "expected_pair_count": 3,
            "high_correlation_threshold": 0.85,
            "high_correlation_pairs": [{"left": "a", "right": "b", "correlation": 0.91}],
        }
    )

    assert gate["status"] == "fail"


def test_entry_redundancy_gate_requires_complete_pair_coverage():
    gate = _entry_redundancy_gate(
        {
            "pair_count": 1,
            "expected_pair_count": 55,
            "high_correlation_threshold": 0.85,
            "high_correlation_pairs": [],
        }
    )

    assert gate["status"] == "insufficient"


def test_entry_decision_requires_walk_forward_and_redundancy_gates():
    candidate = {
        "by_window": {},
        "perturbation": {},
        "regime": {},
        "concentration": {},
        "walk_forward": {},
        "factor_correlation": {},
        "overfit_risk": {},
    }
    report = {
        "versions": {
            "v26_relative_watch_late_surge_cap": {"by_window": {}},
            "v31_expanded_balanced_tail_guard": candidate,
            "v32_expanded_defensive_breakdown_guard": candidate,
        }
    }

    decisions = _entry_decisions(report, "1m")

    assert "walk_forward" in decisions[0]["gates"]
    assert "redundancy" in decisions[0]["gates"]
    assert decisions[0]["research_track_status"] == decisions[0]["decision_status"]


def test_entry_decision_consumes_causal_fill_and_friction_evidence():
    window = {
        "window_status": "ok",
        "window_date_count": 120,
        "selected_count": 5,
        "selected_avg_return_pct": 1.0,
        "is_valid": True,
        "causal_entry_expected_count": 5,
        "causal_entry_valid_count": 5,
        "causal_entry_fill_rate": 1.0,
    }
    candidate = {
        "by_window": {name: dict(window) for name in ("recent_60", "recent_120", "holdout")},
        "perturbation": {},
        "regime": {},
        "concentration": {},
        "walk_forward": {},
        "factor_correlation": {},
        "overfit_risk": {},
    }
    report = {
        "timeframe": "1m",
        "label_source": {
            "mode": "causal_next_session_open_to_close",
            "version_specific": True,
            "source_as_of": "2026-07-13",
            "source_bar_interval": "1m",
        },
        "parameters": {"round_trip_cost_pct": 0.1, "returns_net_of_round_trip_cost": True},
        "versions": {
            "v26_relative_watch_late_surge_cap": {"by_window": {name: dict(window) for name in ("recent_60", "recent_120", "holdout")}},
            "v31_expanded_balanced_tail_guard": candidate,
            "v32_expanded_defensive_breakdown_guard": candidate,
        },
    }

    decisions = _entry_decisions(report, "1m")

    assert decisions[0]["gates"]["next_bar_fill"]["status"] == "pass"
    assert decisions[0]["gates"]["friction"]["status"] == "pass"


def test_stop_strategy_linkage_accepts_causal_simulated_entry_fill_for_paper_research():
    report = {
        "summary": {
            "strategy_linked_entry_paths": True,
            "entry_reference_is_actual_fill": False,
            "entry_reference_is_causal_simulated_fill": True,
        },
        "factors": {},
        "long_history_veto_evidence": {},
    }

    decisions = _stop_decisions(report, "1m")

    assert decisions[0]["gates"]["strategy_linkage"]["status"] == "pass"


def test_stop_board_data_unavailable_is_explicitly_insufficient():
    report = {
        "summary": {
            "strategy_linked_entry_paths": True,
            "entry_reference_is_causal_simulated_fill": True,
        },
        "factors": {
            "board_synchronous_weakness": {
                "by_window": {
                    name: {
                        "data_status": "data_unavailable",
                        "data_reason": "causal_board_minute_series_not_supplied",
                    }
                    for name in ("recent_60", "recent_120", "holdout")
                }
            }
        },
        "long_history_veto_evidence": {},
    }

    decision = next(
        item
        for item in _stop_decisions(report, "1m")
        if item["factor_id"] == "board_synchronous_weakness"
    )

    assert decision["gates"]["recent_60"]["status"] == "insufficient"
    assert "board minute" in decision["gates"]["recent_60"]["reason"].lower()


def _passing_profit_window():
    return {
        "window_status": "ok",
        "trigger_count": 5,
        "next_bar_fill_rate": 1.0,
    }


def _passing_paired_window(delta=1.0):
    return {
        "paired_record_count": 5,
        "avg_paired_delta_pct": delta,
        "paired_tail_avoided_count": 0,
        "paired_tail_worsened_count": 0,
    }


def test_profit_fill_gate_requires_evidence_in_all_three_windows():
    windows = {
        "recent_60": _passing_profit_window(),
        "recent_120": _passing_profit_window(),
        "holdout": _passing_profit_window(),
    }
    windows["recent_120"] = {"window_status": "ok", "trigger_count": 0, "next_bar_fill_rate": None}

    gate = _profit_fill_gate(windows)

    assert gate["status"] == "insufficient"


def test_profit_fill_gate_rejects_nonfinite_rate_even_when_other_windows_pass():
    windows = {
        "recent_60": _passing_profit_window(),
        "recent_120": _passing_profit_window(),
        "holdout": _passing_profit_window(),
        "all_history": _passing_profit_window(),
    }
    windows["recent_120"]["next_bar_fill_rate"] = float("nan")

    assert _profit_fill_gate(windows)["status"] == "insufficient"


def test_stop_fill_gate_requires_evidence_in_all_three_windows():
    window = {
        "window_status": "ok",
        "by_horizon": {
            horizon: {"signal_count": 5, "next_bar_fill_rate": 1.0}
            for horizon in ("5", "15", "30")
        },
    }
    windows = {name: window for name in ("recent_60", "recent_120", "holdout")}

    assert _stop_fill_gate(windows)["status"] == "pass"
    assert _stop_fill_gate({"recent_120": window, "all_history": window})["status"] == "insufficient"


def test_stop_fill_gate_rejects_nonfinite_rate_even_when_other_windows_pass():
    def stop_window(rate):
        return {
            "window_status": "ok",
            "by_horizon": {
                horizon: {"signal_count": 5, "next_bar_fill_rate": rate}
                for horizon in ("5", "15", "30")
            },
        }

    windows = {
        "recent_60": stop_window(1.0),
        "recent_120": stop_window(float("nan")),
        "holdout": stop_window(1.0),
        "all_history": stop_window(1.0),
    }

    assert _stop_fill_gate(windows)["status"] == "insufficient"


def test_profit_threshold_robustness_checks_recent_120_window():
    candidate = {
        "by_window": {
            name: {"window_status": "ok"}
            for name in ("recent_60", "recent_120", "holdout")
        },
        "paired_vs_fixed_by_window": {
            "recent_60": _passing_paired_window(),
            "recent_120": _passing_paired_window(delta=-1.0),
            "holdout": _passing_paired_window(),
        },
    }

    gate = _profit_threshold_robustness_gate([{"candidates": {"paper_take_profit_protect_candidate": candidate}}])

    assert gate["status"] == "fail"
    assert gate["evidence"]["alternate_window"] == "recent_120"


def test_profit_long_history_gate_requires_complete_finite_metrics():
    gate = _profit_long_history_gate(
        {
            "status": "ok",
            "vetoed": False,
            "candidate": {},
            "baseline": {},
        }
    )

    assert gate["status"] == "insufficient"


def test_profit_regime_gate_uses_paired_delta_against_fixed_policy():
    gate = _profit_regime_gate(
        {
            "strong": {
                "deduplicated_record_count": 6,
                "paired_record_count": 6,
                "avg_paired_delta_pct": -0.5,
                "paired_tail_avoided_count": 0,
                "paired_tail_worsened_count": 0,
                "duplicate_policy_conflict_count": 0,
            }
        },
        {"status": "ok", "date": "2026-07-13", "regime": "strong"},
    )

    assert gate["status"] == "fail"


def test_profit_regime_gate_rejects_unknown_current_environment():
    gate = _profit_regime_gate(
        {
            "unknown": {
                "deduplicated_record_count": 10,
                "paired_record_count": 10,
                "avg_paired_delta_pct": 1.0,
                "paired_tail_avoided_count": 1,
                "paired_tail_worsened_count": 0,
            }
        },
        {"status": "insufficient", "date": "2026-07-13", "regime": None},
    )

    assert gate["status"] == "insufficient"


def test_profit_walk_forward_gate_requires_three_positive_paired_folds():
    folds = [
        {
            "status": "ok",
            "paired_record_count": 5,
            "avg_paired_delta_pct": 0.5,
            "paired_tail_avoided_count": 0,
            "paired_tail_worsened_count": 0,
            "duplicate_policy_conflict_count": 0,
        }
        for _ in range(3)
    ]
    report = {"fold_count": 3, "valid_fold_count": 3, "folds": folds}

    assert _profit_walk_forward_gate(report)["status"] == "pass"
    folds[1]["avg_paired_delta_pct"] = -0.1
    assert _profit_walk_forward_gate(report)["status"] == "fail"


@pytest.mark.parametrize("field", ["snapshot_label", "calendar_source", "candidate_source", "window_dates"])
def test_profit_report_cohort_rejects_mixed_sources(field):
    base = {
        "snapshot_label": "same",
        "calendar_source": "candidate-root",
        "candidate_source": {"candidate_root": "candidate-root", "version_ids": ["v31", "v32"]},
        "windows": {
            name: {"dates": ["2026-07-09", "2026-07-10"]}
            for name in ("all_history", "recent_60", "recent_120", "holdout")
        },
    }
    other = {
        **base,
        "candidate_source": dict(base["candidate_source"]),
        "windows": {name: dict(window) for name, window in base["windows"].items()},
    }
    if field == "snapshot_label":
        other["snapshot_label"] = "different"
    elif field == "calendar_source":
        other["calendar_source"] = "other-root"
    elif field == "candidate_source":
        other["candidate_source"]["candidate_root"] = "other-root"
    else:
        other["windows"]["recent_120"]["dates"] = ["2026-07-10"]

    with pytest.raises(ValueError, match="cohort"):
        validate_profit_report_cohort({2.0: base, 3.0: other})


def test_profit_report_cohort_accepts_top_level_calendar_source_and_matching_window_dates():
    report = {
        "snapshot_label": "same",
        "calendar_source": "candidate-root",
        "candidate_source": {"candidate_root": "candidate-root", "version_ids": ["v31", "v32"]},
        "windows": {
            name: {"dates": ["2026-07-09", "2026-07-10"]}
            for name in ("all_history", "recent_60", "recent_120", "holdout")
        },
    }

    validate_profit_report_cohort({2.0: report, 3.0: report})

    with pytest.raises(ValueError, match="2% and 3%"):
        validate_profit_report_cohort({2.0: report, 4.0: report})


def test_decision_evaluation_tail_summary_and_markdown_report_source_coverage():
    current = date(2026, 6, 30)
    dates = []
    while len(dates) < 20:
        if current.weekday() < 5:
            dates.append(current.isoformat())
        current -= timedelta(days=1)
    dates = sorted(dates)
    source_report = {
        "as_of": dates[-1],
        "calendar_source": {"dates": dates},
        "label_source": {
            "revalidated_candidate_source_identity": {
                "status": "validated",
                "document_dates": dates[:18],
                "complete_candidate_dates": dates[:5],
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
                "dates": dates,
                "source_document_date_count": 18,
                "complete_candidate_date_count": 5,
                "source_document_date_coverage_rate": 0.9,
                "complete_candidate_date_coverage_rate": 0.25,
                "candidate_date_coverage_status": "insufficient",
            }
        },
    }

    evaluation_tail = decision_audit._evaluation_tail_summary({"entry:1m": source_report})
    report = {
        "evaluation_tail": evaluation_tail,
        "summary": {},
        "decisions": [
            {
                "candidate_id": "entry:1m:test",
                "candidate_type": "entry",
                "timeframe": "1m",
                "research_track_status": "observe",
                "decision_status": "observe",
                "failed_gates": ["holdout"],
                "insufficient_gates": ["recent_120", "holdout"],
            }
        ],
        "recommended_paper_stack": {},
    }
    markdown = decision_audit._markdown(report)

    assert evaluation_tail["status"] == "observed_evaluation_tail"
    assert evaluation_tail["blind"] is False
    assert evaluation_tail["eligible_for_oos_claim"] is False
    assert evaluation_tail["sources"]["entry:1m"]["source_document_date_count"] == 18
    assert "observed_evaluation_tail" in markdown
    assert "blind: `false`" in markdown
    assert "eligible_for_oos_claim: `false`" in markdown
    assert "entry:1m" in markdown
    assert "18/20" in markdown
    assert "5/20" in markdown
    assert "None/None" not in markdown
    assert "holdout" not in markdown.lower()
