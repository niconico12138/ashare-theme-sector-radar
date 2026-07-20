from __future__ import annotations

from pathlib import Path

import pytest

from theme_sector_radar.ml.contract import canonical_sha256
from theme_sector_radar.ml.prospective_candidate_archive import RAW_FEATURE_NAMES
from theme_sector_radar.ml.prospective_comparison import (
    COST_BPS,
    EVALUATION_INPUT_SCHEMA_VERSION,
    PRE_REGISTERED_CONTRACT,
    TOP_KS,
    _drift_report,
    _load_labels,
    _load_predictions,
    _metric_block,
    _quality_report,
    run_prospective_comparison,
    validate_prospective_comparison_report,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json,
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


def _write_evaluation_source(root: Path, input_type: str, records, **extra):
    path = root / f"{input_type}.json"
    payload = {
        "schema_version": EVALUATION_INPUT_SCHEMA_VERSION,
        "input_type": input_type,
        "records": records,
        **extra,
    }
    write_strict_json_atomic(path, payload)
    _loaded, sha256 = load_strict_json_with_sha256(path)
    return path.resolve(), sha256


def _feature_row(day: str, code: str, base: float, *, missing: str | None = None):
    features = {
        name: base + index / 100.0
        for index, name in enumerate(RAW_FEATURE_NAMES)
    }
    indicators = {name: False for name in RAW_FEATURE_NAMES}
    if missing:
        features[missing] = None
        indicators[missing] = True
    return {
        "as_of_date": day,
        "stock_code": code,
        "features": features,
        "missing_indicators": indicators,
    }


def test_zero_day_archive_only_writes_blocked_report_and_is_idempotent(tmp_path):
    output = tmp_path / "comparison"
    kwargs = {
        "archive_root": tmp_path / "empty_archive",
        "output_root": output,
        "report_as_of_date": "2026-07-20",
    }
    created = run_prospective_comparison(**kwargs)
    repeated = run_prospective_comparison(**kwargs)

    assert created["created"] is True
    assert repeated["created"] is False
    assert created["report"]["status"] == "blocked"
    assert created["report"]["counts"]["snapshot_dates"] == 0
    assert created["report"]["metrics_available"] is False
    assert set(created["report"]["strategies"]) == {
        "rule-only",
        "ML-only",
        "rule-gated+ML/hybrid",
    }
    assert "minimum_60_real_snapshot_dates_not_met" in created["report"]["blockers"]
    assert validate_prospective_comparison_report(output) == {
        "status": "blocked",
        "snapshot_dates": 0,
        "metrics_available": False,
        "physical_sha256": created["sha256"],
    }


def test_parameter_drift_event_manifest_and_tampered_repeat_are_rejected(tmp_path):
    drifted = dict(PRE_REGISTERED_CONTRACT)
    drifted["minimum_snapshot_dates"] = 59
    with pytest.raises(ValueError, match="parameter drift"):
        run_prospective_comparison(
            archive_root=tmp_path / "archive",
            output_root=tmp_path / "drift",
            report_as_of_date="2026-07-20",
            contract=drifted,
        )
    with pytest.raises(ValueError, match="unreviewed event"):
        run_prospective_comparison(
            archive_root=tmp_path / "archive",
            output_root=tmp_path / "event",
            report_as_of_date="2026-07-20",
            event_manifest={"enabled": False, "review_status": "pending"},
        )
    with pytest.raises(ValueError, match="event adjustment is disabled"):
        run_prospective_comparison(
            archive_root=tmp_path / "archive",
            output_root=tmp_path / "event_enabled",
            report_as_of_date="2026-07-20",
            event_manifest={"enabled": True, "review_status": "approved"},
        )

    output = tmp_path / "comparison"
    run_prospective_comparison(
        archive_root=tmp_path / "archive",
        output_root=output,
        report_as_of_date="2026-07-20",
    )
    path = output / "comparison_report.json"
    report = load_strict_json(path)
    report["blockers"].append("tampered")
    write_strict_json_atomic(path, report)
    with pytest.raises(ValueError, match="duplicate comparison execution"):
        run_prospective_comparison(
            archive_root=tmp_path / "archive",
            output_root=output,
            report_as_of_date="2026-07-20",
        )


def test_label_maturity_future_record_duplicate_and_sha_tamper_are_rejected(tmp_path):
    snapshot_by_date = {
        "2026-07-16": {"target_5d": "2026-07-23"},
    }
    records = [
        {
            "as_of_date": "2026-07-16",
            "stock_code": "000001",
            "label_as_of_date": "2026-07-22",
            "future_return_5d": 0.02,
            "future_excess_return_5d": 0.01,
        }
    ]
    path, sha256 = _write_evaluation_source(tmp_path, "labels_5d", records)
    with pytest.raises(ValueError, match="not mature"):
        _load_labels(
            path,
            expected_sha256=sha256,
            snapshot_by_date=snapshot_by_date,
            as_of_dates={"2026-07-16"},
            report_as_of_date="2026-07-23",
        )
    with pytest.raises(ValueError, match="source SHA mismatch"):
        _load_labels(
            path,
            expected_sha256="0" * 64,
            snapshot_by_date=snapshot_by_date,
            as_of_dates={"2026-07-16"},
            report_as_of_date="2026-07-23",
        )

    future_path, future_sha = _write_evaluation_source(
        tmp_path / "future",
        "labels_5d",
        [dict(records[0], label_as_of_date="2026-07-23")],
    )
    with pytest.raises(ValueError, match="future data relative to report date"):
        _load_labels(
            future_path,
            expected_sha256=future_sha,
            snapshot_by_date=snapshot_by_date,
            as_of_dates={"2026-07-16"},
            report_as_of_date="2026-07-22",
        )

    duplicate_path, duplicate_sha = _write_evaluation_source(
        tmp_path / "duplicate",
        "labels_5d",
        records + records,
    )
    with pytest.raises(ValueError, match="duplicate labels_5d"):
        _load_labels(
            duplicate_path,
            expected_sha256=duplicate_sha,
            snapshot_by_date=snapshot_by_date,
            as_of_dates={"2026-07-16"},
            report_as_of_date="2026-07-23",
        )


def test_prediction_manifest_boundary_and_protected_score_are_rejected(tmp_path):
    records = [
        {"as_of_date": "2026-07-16", "stock_code": "000001", "prediction": 0.7}
    ]
    path, sha256 = _write_evaluation_source(
        tmp_path,
        "predictions",
        records,
        model_artifact_sha256="a" * 64,
        model_parameters_sha256="b" * 64,
        feature_contract_sha256="c" * 64,
        paper_shadow_only=True,
        formal_predictor_compatible=False,
        comparison_contract_sha256=canonical_sha256(PRE_REGISTERED_CONTRACT),
    )
    identity, predictions = _load_predictions(
        path,
        expected_sha256=sha256,
        as_of_dates={"2026-07-16"},
        report_as_of_date="2026-07-16",
    )
    assert identity["sha256"] == sha256
    assert predictions == {("2026-07-16", "000001"): 0.7}

    protected_records = [dict(records[0], quant_score=88.0)]
    protected_path, protected_sha = _write_evaluation_source(
        tmp_path / "protected",
        "predictions",
        protected_records,
        model_artifact_sha256="a" * 64,
        model_parameters_sha256="b" * 64,
        feature_contract_sha256="c" * 64,
        paper_shadow_only=True,
        formal_predictor_compatible=False,
        comparison_contract_sha256=canonical_sha256(PRE_REGISTERED_CONTRACT),
    )
    with pytest.raises(ValueError, match="protected field"):
        _load_predictions(
            protected_path,
            expected_sha256=protected_sha,
            as_of_dates={"2026-07-16"},
            report_as_of_date="2026-07-16",
        )


def test_pre_registered_metrics_include_topk_cost_risk_missing_and_drift():
    days = ["2026-07-16", "2026-07-17"]
    codes = ["000001", "000002", "000003", "000004", "000005"]
    ranked = {
        day: {code: float(len(codes) - index) for index, code in enumerate(codes)}
        for day in days
    }
    labels = {
        (day, code): {
            "future_excess_return_5d": 0.01 * (len(codes) - index),
            "future_return_5d": 0.02 * (len(codes) - index),
        }
        for day in days
        for index, code in enumerate(codes)
    }
    metrics = _metric_block(dates=days, ranked=ranked, labels=labels)

    assert set(metrics) == {str(value) for value in TOP_KS}
    assert set(metrics["1"]["cost_bps"]) == {str(value) for value in COST_BPS}
    assert metrics["1"]["rank_ic"] == pytest.approx(1.0)
    for cost in metrics["3"]["cost_bps"].values():
        assert set(cost) == {"mean_return", "win_rate", "max_drawdown", "turnover"}

    feature_rows = {
        day: [
            _feature_row(
                day,
                code,
                float(index),
                missing="sector_support_score" if day == days[0] and index == 0 else None,
            )
            for index, code in enumerate(codes)
        ]
        for day in days
    }
    predictions = {
        (day, code): float(index)
        for day in days
        for index, code in enumerate(codes)
    }
    quality = _quality_report(feature_rows, predictions)
    drift = _drift_report(feature_rows, predictions)
    assert quality["sector_support_score"]["missing_count"] == 1
    assert quality["sector_support_score"]["missing_rate"] == pytest.approx(0.1)
    assert "absolute_mean_shift" in drift["ma20_slope_5"]
    assert "absolute_mean_shift" in drift["ml_prediction"]
