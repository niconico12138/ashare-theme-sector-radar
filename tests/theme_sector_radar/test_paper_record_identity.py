import importlib
import hashlib
import json
from datetime import datetime, timedelta

import pytest

from theme_sector_radar.data.local_minute_archive import aggregate_complete_1m_session_to_5m


def _bars(day="2026-07-02", code="600001", name="test"):
    base = datetime.strptime(day, "%Y-%m-%d")
    times = []
    current = base.replace(hour=9, minute=30)
    while current <= base.replace(hour=11, minute=30):
        times.append(current)
        current += timedelta(minutes=1)
    current = base.replace(hour=13, minute=1)
    while current <= base.replace(hour=15, minute=0):
        times.append(current)
        current += timedelta(minutes=1)
    return [
        {
            "date": int(value.strftime("%Y%m%d%H%M%S")),
            "code": code,
            "name": name,
            "open": 10.0,
            "high": 10.6 if index == len(times) - 1 else 10.1,
            "low": 9.9,
            "close": 10.5 if index == len(times) - 1 else 10.0,
            "volume": 100.0,
            "amount": 1000.0,
        }
        for index, value in enumerate(times)
    ]


def _record(timeframe="1m"):
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    source_1m_bars = _bars()
    bars = source_1m_bars
    if timeframe == "5m":
        bars = aggregate_complete_1m_session_to_5m(bars)
    derived = _derived_fields(bars, timeframe)
    record = {
        "signal_date": "2026-07-01",
        "entry_date": "2026-07-02",
        "code": "600001",
        "name": "test",
        "timing_version_id": "v31_expanded_balanced_tail_guard",
        "causal_entry_valid": True,
        "causal_entry_invalid_reasons": [],
        "entry_bars": bars,
        "entry_bars_sha256": module.entry_bars_sha256(bars),
        "forward_return_pct": 5.0,
        **derived,
        "execution_assumptions": {
            "signal_available": "after_signal_session_close",
            "entry_model": "next_trading_session_first_bar_open",
            "bar_interval": timeframe,
            "bar_source": {
                "1m": "complete_1m_session",
                "5m": "aggregated_from_complete_1m_session",
            }[timeframe],
            "factor_exit_peak_giveback_pct": 2.0,
        },
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    if timeframe == "5m":
        record["source_1m_bars"] = source_1m_bars
        record["source_1m_bars_sha256"] = module.entry_bars_sha256(source_1m_bars)
    return record


def _records_report(records):
    return {
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
        "entry_bars_source_identity": {
            "status": "validated",
            "source_kind": "in_memory_test_fixture",
            "sha256": "a" * 64,
        },
        "records": records,
    }


def _selected_candidate():
    return {
        "_sample_date": "2026-07-01",
        "code": "600001",
        "name": "test",
        "boards": ["gas"],
        "open_to_midday_resilience_score": 70,
        "midday_hold_score": 70,
        "vwap_above_ratio_score": 70,
        "late_high_near_close_score": 90,
        "high_to_close_drawdown_score": 12,
        "lower_low_sequence_risk": 20,
        "stock_vs_market_intraday_alpha_score": 75,
        "relative_resilience_score": 75,
        "optimized_watch_score": 80,
        "late_amount_surge_score": 40,
        "failed_breakout_risk": 20,
        "execution_tradeability_score": 60,
        "late_breakdown_risk": 0,
    }


def _derived_fields(bars, timeframe):
    paper_trading = importlib.import_module("theme_sector_radar.timing.paper_trading")
    factor_exit = importlib.import_module("theme_sector_radar.timing.factor_exit")
    path_stats = paper_trading._path_stats(bars)
    entry_price = path_stats["entry_reference_price"]
    factor_exit_triggers = factor_exit.evaluate_factor_exit_triggers(
        bars,
        entry_price=entry_price or 0.0,
        protect_peak_giveback_pct=2.0,
    )
    return {
        "path_stats": path_stats,
        "exit_research": paper_trading._exit_research(path_stats),
        "factor_exit_triggers": factor_exit_triggers,
        "paper_exit_candidates": paper_trading._paper_exit_candidates(
            factor_exit_triggers,
            bars,
            entry_price,
            bar_interval=timeframe,
        ),
        "exit_data_quality": paper_trading._exit_data_quality(
            bars,
            interval_minutes={"1m": 1, "5m": 5}[timeframe],
        ),
    }


@pytest.mark.parametrize("timeframe", ["1m", "5m"])
def test_causal_paper_record_identity_accepts_complete_next_session_path(timeframe):
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")

    summary = module.validate_causal_paper_records(
        [_record(timeframe)],
        timeframe=timeframe,
        as_of="2026-07-02",
        calendar_dates=["2026-07-01", "2026-07-02"],
        factor_exit_peak_giveback_pct=2.0,
        context="unit records",
    )

    assert summary == {"record_count": 1, "valid_record_count": 1, "invalid_record_count": 0}


@pytest.mark.parametrize("entry_price", [0.0, -0.0, True, False, "10.0", None])
def test_paper_records_report_rejects_nonpositive_or_nonnumeric_observational_entry_price(
    entry_price,
):
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    record = _record("1m")
    record["factor_exit_triggers"]["entry_price"] = entry_price

    with pytest.raises(ValueError, match="observational entry_price"):
        module.validate_paper_records_report(
            _records_report([record]),
            context="unit records",
        )


def test_paper_records_report_accepts_frozen_unlabeled_zero_placeholder():
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    record = _record("1m")
    record["causal_entry_valid"] = False
    record["entry_bars"] = []
    record["factor_exit_triggers"]["entry_price"] = 0.0

    module.validate_paper_records_report(
        _records_report([record]),
        context="unit records",
    )


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
def test_paper_records_report_requires_all_paper_only_guards(scope, field):
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    report = _records_report([_record("1m")])
    target = report if scope == "report" else report["records"][0]
    target[field] = False

    with pytest.raises(ValueError, match=field):
        module.validate_paper_records_report(report, context="unit records")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("trade_side", "buy"),
        ("order_price", 10.0),
        ("shares", 100),
        ("tradeSide", "buy"),
        ("orderPrice", 10.0),
        ("shareQuantity", 100),
        ("tradeAction", "buy"),
        ("executionSide", "sell"),
        ("positionPct", 0.5),
        ("tradeaction", "buy"),
        ("TRADEACTION", "buy"),
        ("executionside", "sell"),
        ("EXECUTIONSIDE", "sell"),
        ("positionpct", 0.5),
        ("POSITIONPCT", 0.5),
    ],
)
def test_paper_records_report_rejects_executable_field_synonyms(field, value):
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    report = _records_report([_record("1m")])
    report["records"][0]["nested_execution"] = {field: value}

    with pytest.raises(ValueError, match="executable instruction"):
        module.validate_paper_records_report(report, context="unit records")


def test_paper_records_report_revalidates_entry_bars_manifest(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    path = tmp_path / "entry-bars.json"
    payload = {
        "schema_version": "timing_entry_bars_source_manifest.v1",
        "as_of": "2026-07-02",
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
        "sessions": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    report = _records_report([])
    report["entry_bars_source_identity"] = {
        "status": "validated",
        "source_kind": "strict_json_manifest",
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "schema_version": payload["schema_version"],
        "as_of": payload["as_of"],
        "session_count": 0,
    }

    module.validate_paper_records_report(report, context="unit records")
    path.write_text(json.dumps({**payload, "as_of": "2026-07-03"}), encoding="utf-8")

    with pytest.raises(ValueError, match="entry-bars manifest SHA mismatch"):
        module.validate_paper_records_report(report, context="unit records")


def test_paper_records_report_requires_durable_entry_bars_for_production_chain():
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")

    with pytest.raises(ValueError, match="durable strict JSON manifest"):
        module.validate_paper_records_report(
            _records_report([]),
            context="unit records",
            require_durable_entry_bars_source=True,
        )


def test_paper_records_report_binds_valid_record_to_manifest_session(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    record = _record("1m")
    payload = {
        "schema_version": "timing_entry_bars_source_manifest.v1",
        "as_of": "2026-07-02",
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
        "sessions": [
            {
                "code": record["code"],
                "entry_date": record["entry_date"],
                "bars": record["entry_bars"],
            }
        ],
    }
    path = tmp_path / "entry-bars.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    report = _records_report([record])
    report["entry_bars_source_identity"] = {
        "status": "validated",
        "source_kind": "strict_json_manifest",
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "schema_version": payload["schema_version"],
        "as_of": payload["as_of"],
        "session_count": 1,
    }

    module.validate_paper_records_report(
        report,
        context="unit records",
        require_durable_entry_bars_source=True,
    )

    report["records"][0]["entry_bars"][0]["close"] = 9.99
    report["records"][0]["entry_bars_sha256"] = module.entry_bars_sha256(
        report["records"][0]["entry_bars"]
    )
    with pytest.raises(ValueError, match="entry-bars manifest path mismatch"):
        module.validate_paper_records_report(
            report,
            context="unit records",
            require_durable_entry_bars_source=True,
        )


def test_paper_records_report_rejects_duplicate_manifest_sessions(tmp_path):
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    record = _record("1m")
    session = {
        "code": record["code"],
        "entry_date": record["entry_date"],
        "bars": record["entry_bars"],
    }
    payload = {
        "schema_version": "timing_entry_bars_source_manifest.v1",
        "as_of": "2026-07-02",
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
        "sessions": [session, dict(session)],
    }
    path = tmp_path / "entry-bars.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    report = _records_report([])
    report["entry_bars_source_identity"] = {
        "status": "validated",
        "source_kind": "strict_json_manifest",
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "schema_version": payload["schema_version"],
        "as_of": payload["as_of"],
        "session_count": 2,
    }

    with pytest.raises(ValueError, match="duplicate entry-bars manifest session"):
        module.validate_paper_records_report(
            report,
            context="unit records",
            require_durable_entry_bars_source=True,
        )


def test_causal_paper_records_reject_non_object_entry_bar_elements():
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    record = _record("1m")
    record["entry_bars"].append("not-a-bar")

    with pytest.raises(ValueError, match="entry bars must contain only objects"):
        module.validate_causal_paper_records(
            [record],
            timeframe="1m",
            as_of="2026-07-02",
            calendar_dates=["2026-07-01", "2026-07-02"],
            factor_exit_peak_giveback_pct=2.0,
            context="unit records",
        )


def test_causal_paper_record_identity_rejects_cross_version_path_mismatch():
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    first = _record("1m")
    second = _record("1m")
    second["timing_version_id"] = "v32_expanded_balanced_tail_guard"
    second["entry_bars"][0]["amount"] = 1001.0
    second["entry_bars_sha256"] = module.entry_bars_sha256(second["entry_bars"])

    with pytest.raises(ValueError, match="entry path"):
        module.validate_causal_paper_records(
            [first, second],
            timeframe="1m",
            as_of="2026-07-02",
            calendar_dates=["2026-07-01", "2026-07-02"],
            factor_exit_peak_giveback_pct=2.0,
            context="unit records",
        )


def test_entry_path_manifests_reject_cross_timeframe_source_mismatch():
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    one_minute = _record("1m")
    five_minute = _record("5m")
    five_minute["source_1m_bars"][0]["amount"] = 1001.0
    five_minute["source_1m_bars_sha256"] = module.entry_bars_sha256(
        five_minute["source_1m_bars"]
    )
    five_minute["entry_bars"] = aggregate_complete_1m_session_to_5m(
        five_minute["source_1m_bars"]
    )
    five_minute["entry_bars_sha256"] = module.entry_bars_sha256(
        five_minute["entry_bars"]
    )
    five_minute.update(_derived_fields(five_minute["entry_bars"], "5m"))

    one_manifest = module.entry_path_manifest(
        [one_minute], timeframe="1m", context="1m records"
    )
    five_manifest = module.entry_path_manifest(
        [five_minute], timeframe="5m", context="5m records"
    )

    with pytest.raises(ValueError, match="entry path"):
        module.merge_entry_path_manifests(
            [one_manifest, five_manifest], context="final records"
        )


def test_paper_record_cohort_rejects_missing_candidate_selection_record():
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    paper_trading = importlib.import_module("theme_sector_radar.timing.paper_trading")
    candidate = _selected_candidate()
    expected = paper_trading.build_timing_paper_trading_records(
        [candidate],
        as_of="2026-07-01",
        snapshot_label="unit",
        version_ids=["v31_expanded_balanced_tail_guard"],
        concentration_threshold=2,
        factor_exit_peak_giveback_pct=2.0,
        bar_interval="1m",
        bar_source="complete_1m_session",
    )
    assert len(expected["records"]) == 1

    with pytest.raises(ValueError, match="cohort.*missing"):
        module.validate_paper_record_cohort(
            [],
            samples=[candidate],
            version_ids=["v31_expanded_balanced_tail_guard"],
            snapshot_label="unit",
            calendar_dates=["2026-07-01", "2026-07-02"],
            start=None,
            end="2026-07-02",
            concentration_threshold=2,
            factor_exit_peak_giveback_pct=2.0,
            timeframe="1m",
            context="unit records",
        )


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda row: row.update(snapshot_label="forged"), "cohort source fields"),
        (lambda row: row.update(as_of="2026-06-30"), "cohort source fields"),
        (
            lambda row: row["factor_snapshot"].update(late_amount_surge_score=99),
            "cohort source fields",
        ),
        (lambda row: row.update(boards=["forged"]), "cohort source fields"),
        (lambda row: row.update(selection_forward_return_pct=99.0), "selection label"),
    ],
)
def test_paper_record_cohort_rejects_tampered_candidate_source_fields(mutate, match):
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    paper_trading = importlib.import_module("theme_sector_radar.timing.paper_trading")
    candidate = {**_selected_candidate(), "forward_return_pct": -1.25}
    report = paper_trading.build_timing_paper_trading_records(
        [candidate],
        minute_bars_by_code={"600001": _bars()},
        entry_date_by_code={"600001": "2026-07-02"},
        as_of="2026-07-01",
        snapshot_label="unit",
        version_ids=["v31_expanded_balanced_tail_guard"],
        concentration_threshold=2,
        factor_exit_peak_giveback_pct=2.0,
        bar_interval="1m",
        bar_source="complete_1m_session",
    )
    assert len(report["records"]) == 1
    mutate(report["records"][0])

    with pytest.raises(ValueError, match=match):
        module.validate_paper_record_cohort(
            report["records"],
            samples=[candidate],
            version_ids=["v31_expanded_balanced_tail_guard"],
            snapshot_label="unit",
            calendar_dates=["2026-07-01", "2026-07-02"],
            start=None,
            end="2026-07-02",
            concentration_threshold=2,
            factor_exit_peak_giveback_pct=2.0,
            timeframe="1m",
            context="unit records",
        )


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda row: row.update(entry_date="2026-07-03"), "next trading date"),
        (lambda row: row.update(entry_bars_sha256="a" * 64), "bars SHA"),
        (lambda row: row["entry_bars"][10].update(code="000001"), "security code"),
        (lambda row: row["entry_bars"].pop(10), "complete session"),
    ],
)
def test_causal_paper_record_identity_rejects_forged_or_incomplete_paths(mutate, match):
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    row = _record()
    mutate(row)

    with pytest.raises(ValueError, match=match):
        module.validate_causal_paper_records(
            [row],
            timeframe="1m",
            as_of="2026-07-03",
            calendar_dates=["2026-07-01", "2026-07-02", "2026-07-03"],
            factor_exit_peak_giveback_pct=2.0,
            context="unit records",
        )


def test_causal_paper_record_identity_rejects_executable_fields_nested_in_bars():
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    row = _record()
    row["entry_bars"][0]["orders"] = [{"side": "buy", "quantity": 1}]
    row["entry_bars_sha256"] = module.entry_bars_sha256(row["entry_bars"])

    with pytest.raises(ValueError, match="executable instruction fields"):
        module.validate_causal_paper_records(
            [row],
            timeframe="1m",
            as_of="2026-07-02",
            calendar_dates=["2026-07-01", "2026-07-02"],
            factor_exit_peak_giveback_pct=2.0,
            context="unit records",
        )


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda row: row["path_stats"].update(max_favorable_excursion_pct=99.0),
            "derived path fields",
        ),
        (
            lambda row: row["paper_exit_candidates"]["paper_fixed_exit_baseline"].update(
                simulated_exit_return_pct=99.0
            ),
            "derived path fields",
        ),
    ],
)
def test_causal_paper_record_identity_rejects_tampered_derived_path_fields(mutate, match):
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    row = _record()
    mutate(row)

    with pytest.raises(ValueError, match=match):
        module.validate_causal_paper_records(
            [row],
            timeframe="1m",
            as_of="2026-07-02",
            calendar_dates=["2026-07-01", "2026-07-02"],
            factor_exit_peak_giveback_pct=2.0,
            context="unit records",
        )


def test_causal_paper_record_identity_rejects_empty_security_name():
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    row = _record()
    row["name"] = ""

    with pytest.raises(ValueError, match="security or strategy identity"):
        module.validate_causal_paper_records(
            [row],
            timeframe="1m",
            as_of="2026-07-02",
            calendar_dates=["2026-07-01", "2026-07-02"],
            factor_exit_peak_giveback_pct=2.0,
            context="unit records",
        )


@pytest.mark.parametrize("mutation", ["missing", "aggregate_mismatch"])
def test_causal_5m_record_identity_requires_bound_source_1m_session(mutation):
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    row = _record("5m")
    if mutation == "missing":
        row.pop("source_1m_bars")
        row.pop("source_1m_bars_sha256")
    else:
        row["source_1m_bars"][10]["close"] = 10.05
        row["source_1m_bars_sha256"] = module.entry_bars_sha256(row["source_1m_bars"])

    with pytest.raises(ValueError, match="source 1m"):
        module.validate_causal_paper_records(
            [row],
            timeframe="5m",
            as_of="2026-07-02",
            calendar_dates=["2026-07-01", "2026-07-02"],
            factor_exit_peak_giveback_pct=2.0,
            context="unit records",
        )


def test_causal_paper_record_identity_binds_factor_exit_parameter_to_batch_report():
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")

    with pytest.raises(ValueError, match="factor-exit parameter identity"):
        module.validate_causal_paper_records(
            [_record()],
            timeframe="1m",
            as_of="2026-07-02",
            calendar_dates=["2026-07-01", "2026-07-02"],
            factor_exit_peak_giveback_pct=3.0,
            context="unit records",
        )


def test_causal_paper_record_identity_accepts_unlabeled_record_only_without_path_data():
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    row = _record()
    row.update(
        causal_entry_valid=False,
        causal_entry_invalid_reasons=["entry_bars_missing"],
        entry_bars=[],
        entry_bars_sha256=None,
        forward_return_pct=None,
        **_derived_fields([], "1m"),
    )

    summary = module.validate_causal_paper_records(
        [row],
        timeframe="1m",
        as_of="2026-07-02",
        calendar_dates=["2026-07-01", "2026-07-02"],
        factor_exit_peak_giveback_pct=2.0,
        context="unit records",
    )

    assert summary["invalid_record_count"] == 1


def test_causal_paper_record_identity_rejects_unlabeled_record_with_selection_label():
    module = importlib.import_module("theme_sector_radar.timing.paper_record_identity")
    row = _record()
    row.update(
        causal_entry_valid=False,
        causal_entry_invalid_reasons=["entry_bars_missing"],
        entry_bars=[],
        entry_bars_sha256=None,
        forward_return_pct=None,
        selection_forward_return_pct=5.0,
        **_derived_fields([], "1m"),
    )

    with pytest.raises(ValueError, match="selection label"):
        module.validate_causal_paper_records(
            [row],
            timeframe="1m",
            as_of="2026-07-02",
            calendar_dates=["2026-07-01", "2026-07-02"],
            factor_exit_peak_giveback_pct=2.0,
            context="unit records",
        )
