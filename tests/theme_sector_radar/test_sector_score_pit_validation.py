import json
import copy
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

import theme_sector_radar.backtest.sector_score_pit_validation as pit_module
import scripts.validate_sector_scores_pit as pit_script
import theme_sector_radar.reporting.strict_json as strict_json_module

from theme_sector_radar.backtest.sector_score_pit_validation import (
    _candidate_walk_forward,
    _candidate_cap_applied,
    _development_candidate_gate,
    _shadow_candidate_score,
    build_pit_dataset,
    build_walk_forward_folds,
    evaluate_score_rows,
    run_pit_validation,
    write_validation_report,
)


def _write_history(root: Path, name: str, closes: list[float]) -> None:
    industry_root = root / "industry"
    industry_root.mkdir(parents=True, exist_ok=True)
    start = date(2026, 1, 5)
    records = []
    for offset, close in enumerate(closes):
        day = start + timedelta(days=offset)
        records.append(
            {
                "日期": day.isoformat(),
                "开盘价": close - 0.5,
                "最高价": close + 1.0,
                "最低价": close - 1.0,
                "收盘价": close,
                "成交量": 1_000_000 + offset,
                "成交额": 100_000_000 + offset * 1_000_000,
            }
        )
    payload = {
        "sector_name": name,
        "sector_code": f"TEST_{name}",
        "sector_type": "industry",
        "source": "test",
        "price_change_available": True,
        "records": records,
    }
    (industry_root / f"{name}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def test_pit_dataset_binds_actual_source_dates_and_purges_observed_tail_boundary(tmp_path):
    closes = [100.0 + offset for offset in range(12)]
    _write_history(tmp_path, "行业A", closes)
    _write_history(tmp_path, "行业B", [value * 1.01 for value in closes])
    _write_history(tmp_path, "行业C", [value * 0.99 for value in closes])

    dataset = build_pit_dataset(
        tmp_path,
        trend_window=3,
        horizons=(1,),
        holdout_days=3,
    )

    assert dataset["source_manifest"]["document_count"] == 3
    assert len(dataset["holdout"]["dates"]) == 3
    assert dataset["holdout"]["status"] == "observed_evaluation_tail"
    assert dataset["holdout"]["labels_materialized"] is False
    assert dataset["holdout"]["blind"] is False
    assert dataset["holdout"]["eligible_for_oos_claim"] is False

    holdout_dates = set(dataset["holdout"]["dates"])
    assert holdout_dates.isdisjoint(dataset["development_dates"])
    assert dataset["purged_development_dates"]
    assert set(dataset["purged_development_dates"]).isdisjoint(
        dataset["development_dates"]
    )
    holdout_start = min(holdout_dates)
    for sample in dataset["samples"]:
        assert sample["feature_max_date"] == sample["as_of_date"]
        if sample["as_of_date"] in holdout_dates or sample["as_of_date"] in set(
            dataset["purged_development_dates"]
        ):
            assert sample["forward_returns"]["1d"] is None
            assert sample["forward_label_dates"]["1d"] is None
        elif sample["as_of_date"] in set(dataset["development_dates"]):
            assert sample["forward_label_dates"]["1d"] < holdout_start


def test_pit_loader_rejects_duplicate_sector_names_used_for_history_join(tmp_path):
    _write_history(tmp_path, "行业A", [100.0, 101.0, 102.0])
    first = tmp_path / "industry" / "行业A.json"
    payload = json.loads(first.read_text(encoding="utf-8"))
    payload["sector_code"] = "OTHER_CODE"
    (tmp_path / "industry" / "other.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="duplicate sector name"):
        build_pit_dataset(tmp_path, horizons=(1,), holdout_days=0)


def test_pit_loader_rejects_duplicate_source_dates(tmp_path):
    _write_history(tmp_path, "行业A", [100.0, 101.0, 102.0])
    path = tmp_path / "industry" / "行业A.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"][2]["日期"] = payload["records"][1]["日期"]
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate source date"):
        build_pit_dataset(tmp_path, horizons=(1,), holdout_days=0)


def test_pit_loader_rejects_duplicate_json_keys(tmp_path):
    _write_history(tmp_path, "行业A", [100.0, 101.0, 102.0])
    path = tmp_path / "industry" / "行业A.json"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('"records":', '"records": [], "records":', 1), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate JSON key.*records"):
        build_pit_dataset(tmp_path, horizons=(1,), holdout_days=0)


def test_pit_loader_rejects_empty_history_document(tmp_path):
    _write_history(tmp_path, "行业A", [100.0])
    path = tmp_path / "industry" / "行业A.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"] = []
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="must contain at least one record"):
        build_pit_dataset(tmp_path, horizons=(1,), holdout_days=0)


def test_pit_dataset_excludes_sector_rows_without_complete_future_label(tmp_path):
    _write_history(tmp_path, "行业A", [100.0 + offset for offset in range(12)])
    _write_history(tmp_path, "行业B", [90.0 + offset for offset in range(12)])
    _write_history(tmp_path, "短历史", [80.0 + offset for offset in range(8)])

    dataset = build_pit_dataset(
        tmp_path,
        trend_window=3,
        horizons=(1,),
        holdout_days=3,
    )

    development_dates = set(dataset["development_dates"])
    short_rows = [
        sample
        for sample in dataset["samples"]
        if sample["sector_name"] == "短历史"
        and sample["as_of_date"] in development_dates
    ]
    assert short_rows
    assert all(row["forward_returns"]["1d"] is not None for row in short_rows)


def test_pit_base_radar_uses_only_history_available_on_each_scoring_date(tmp_path):
    _write_history(tmp_path, "行业A", [100.0 + offset for offset in range(30)])
    _write_history(tmp_path, "行业B", [100.0 + offset * 0.5 for offset in range(30)])
    _write_history(tmp_path, "行业C", [100.0 - offset * 0.2 for offset in range(30)])

    dataset = build_pit_dataset(
        tmp_path,
        trend_window=10,
        horizons=(1,),
        holdout_days=0,
    )

    rows = sorted(dataset["samples"], key=lambda row: row["as_of_date"])
    assert rows[0]["score_breakdowns"]["radar_base_score"]["trend_history_status"] == "insufficient_history"
    assert rows[-1]["score_breakdowns"]["radar_base_score"]["trend_history_status"] == "ok"
    assert rows[-1]["score_breakdowns"]["radar_base_score"]["trend_history_days"] == 20


def test_pit_labels_require_the_same_calendar_target_date_for_each_sector(tmp_path):
    closes = [100.0 + offset for offset in range(12)]
    clean_root = tmp_path / "clean"
    missing_root = tmp_path / "missing"
    for root in (clean_root, missing_root):
        _write_history(root, "行业A", closes)
        _write_history(root, "行业B", [100.0 + offset * 0.5 for offset in range(12)])
        _write_history(root, "行业C", [100.0 - offset * 0.2 for offset in range(12)])

    path = missing_root / "industry" / "行业C.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    preceding_date = payload["records"][5]["日期"]
    del payload["records"][6]
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    clean = build_pit_dataset(clean_root, trend_window=3, horizons=(1,), holdout_days=0)
    missing = build_pit_dataset(
        missing_root, trend_window=3, horizons=(1,), holdout_days=0
    )

    clean_rows = {
        sample["sector_name"]: sample
        for sample in clean["samples"]
        if sample["as_of_date"] == preceding_date
    }
    missing_rows = {
        sample["sector_name"]: sample
        for sample in missing["samples"]
        if sample["as_of_date"] == preceding_date
    }

    assert set(clean_rows) == {"行业A", "行业B", "行业C"}
    assert set(missing_rows) == {"行业A", "行业B"}
    for sector_name in ("行业A", "行业B"):
        for field in (
            "radar_base_score",
            "trend_continuation_score",
            "short_term_burst_score",
            "rank_metadata",
            "feature_inputs",
        ):
            assert missing_rows[sector_name][field] == clean_rows[sector_name][field]


def test_nonlabelable_dates_still_enter_as_of_scoring_state(tmp_path, monkeypatch):
    closes = [100.0 + offset for offset in range(12)]
    for name in ("行业A", "行业B", "行业C"):
        _write_history(tmp_path, name, closes)
    for name in ("行业B", "行业C"):
        path = tmp_path / "industry" / f"{name}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        preceding_date = payload["records"][5]["日期"]
        del payload["records"][6]
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    ranks_by_date = {}
    previous_by_date = {}
    real_ranking = pit_module.generate_sector_ranking
    real_scoring = pit_module.calculate_sector_scores

    def capture_ranking(snapshots, *args, **kwargs):
        result = real_ranking(snapshots, *args, **kwargs)
        ranks_by_date[snapshots[0].updated_at] = {
            row["sector_id"]: row["current_rank"]
            for row in result.data["industry_top"]
        }
        return result

    def capture_scoring(scores, *args, **kwargs):
        previous_by_date[scores[0].updated_at] = {
            score.sector_id: score.previous_rank for score in scores
        }
        return real_scoring(scores, *args, **kwargs)

    monkeypatch.setattr(pit_module, "generate_sector_ranking", capture_ranking)
    monkeypatch.setattr(pit_module, "calculate_sector_scores", capture_scoring)

    dataset = build_pit_dataset(
        tmp_path, trend_window=3, horizons=(1,), holdout_days=0
    )

    assert preceding_date not in dataset["labelable_dates"]
    assert dataset["scoring_date_sector_counts"][preceding_date] == 3
    next_scoring_date = next(
        day for day in sorted(previous_by_date) if day > preceding_date
    )
    assert previous_by_date[next_scoring_date] == ranks_by_date[preceding_date]


def test_shadow_candidate_caps_independently_of_production_cap_flag():
    definition = {
        "target": "trend_continuation_score",
        "weights": {
            "radar_score_component": 15.0,
            "momentum_component": 25.0,
            "relative_strength_component": 10.0,
            "persistence_component": 20.0,
            "drawdown_component": 15.0,
            "volatility_component": 10.0,
            "data_quality_component": 5.0,
        },
    }
    sample = {
        "trend_continuation_score": 30.0,
        "short_term_burst_score": 20.0,
        "score_breakdowns": {
            "trend_continuation_score": {
                "radar_score_component": 25.0,
                "momentum_component": 20.0,
                "relative_strength_component": 15.0,
                "persistence_component": 15.0,
                "drawdown_component": 10.0,
                "volatility_component": 10.0,
                "data_quality_component": 5.0,
                "risk_penalty": 0.0,
            }
        },
        "cap_metadata": {"trend_cap_applied": False, "burst_cap_applied": False},
        "trend_window_status": "insufficient_history",
        "history_coverage_ratio": 0.2,
        "feature_inputs": {"history_days": 1},
    }

    assert _shadow_candidate_score("trend_evidence_balance_v1", sample, definition) == 34.9
    assert _candidate_cap_applied("trend_evidence_balance_v1", sample, definition) is True


def test_radar_technical_evidence_candidate_rewards_confirmed_breakout_not_exhaustion():
    definition = {
        "target": "radar_base_score",
        "weights": {
            "relative_strength_percentile": 20.0,
            "persistence_ratio": 25.0,
            "healthy_volume_confirmation": 20.0,
            "effective_breakout_20d": 20.0,
            "five_day_momentum_percentile": 15.0,
        },
        "penalties": {
            "volume_exhaustion_risk": 8.0,
            "drawdown_from_20d_high": 7.0,
        },
    }
    confirmed_breakout = {
        "radar_base_score": 50.0,
        "score_breakdowns": {"radar_base_score": {"risk_penalty": 0.0}},
        "feature_inputs": {
            "relative_strength_percentile": 0.9,
            "persistence_ratio": 0.8,
            "healthy_volume_confirmation": 0.9,
            "effective_breakout_20d": 1.0,
            "five_day_momentum_percentile": 0.85,
            "volume_exhaustion_risk": 0.0,
            "drawdown_from_20d_high": 0.0,
        },
    }
    exhausted = {
        **confirmed_breakout,
        "feature_inputs": {
            **confirmed_breakout["feature_inputs"],
            "healthy_volume_confirmation": 0.0,
            "effective_breakout_20d": 0.0,
            "volume_exhaustion_risk": 1.0,
            "drawdown_from_20d_high": -8.0,
        },
    }

    assert (
        _shadow_candidate_score(
            "radar_technical_evidence_v2", confirmed_breakout, definition
        )
        > _shadow_candidate_score(
            "radar_technical_evidence_v2", exhausted, definition
        )
    )


def test_volume_exhaustion_risk_distinguishes_advance_stagnation_decline_and_overheat():
    assert pit_module._volume_exhaustion_risk(3.0, 3.0, 3.5) == 0.0
    assert pit_module._volume_exhaustion_risk(0.0, 3.0, 3.5) == 1.0
    assert pit_module._volume_exhaustion_risk(-3.0, -3.0, 3.5) == 1.0
    assert pit_module._volume_exhaustion_risk(3.0, 16.0, 3.5) == 1.0


def test_pit_dataset_exposes_only_as_of_technical_evidence_inputs(tmp_path):
    closes = [100.0 + offset for offset in range(35)]
    _write_history(tmp_path, "industry_a", closes)
    _write_history(tmp_path, "industry_b", [100.0 + offset * 0.5 for offset in range(35)])
    _write_history(tmp_path, "industry_c", [100.0 - offset * 0.1 for offset in range(35)])

    dataset = build_pit_dataset(
        tmp_path, trend_window=5, horizons=(1,), holdout_days=0
    )
    mature_sample = next(
        sample
        for sample in dataset["samples"]
        if sample["sector_name"] == "industry_a" and sample["as_of_date"] >= "2026-01-30"
    )

    inputs = mature_sample["feature_inputs"]
    assert inputs["feature_max_date"] == mature_sample["as_of_date"]
    assert 0.0 <= inputs["relative_strength_percentile"] <= 1.0
    assert 0.0 <= inputs["five_day_momentum_percentile"] <= 1.0
    assert 0.0 <= inputs["healthy_volume_confirmation"] <= 1.0
    assert inputs["effective_breakout_20d"] in (0.0, 1.0)
    assert inputs["drawdown_from_20d_high"] <= 0.0
    shadow = mature_sample["score_breakdowns"]["radar_base_score"][
        "three_layer_shadow"
    ]
    assert shadow["mode"] == "paper_shadow_research_only"
    assert shadow["direction_score_shadow"] is not None
    assert shadow["time_series"]["status"] == "ok"
    assert shadow["cross_section"]["status"] == "ok"
    assert shadow["rank_momentum"]["status"] == "ok"


def test_pit_sample_manifest_binds_three_layer_shadow(tmp_path):
    closes = [100.0 + offset for offset in range(35)]
    _write_history(tmp_path, "industry_a", closes)
    _write_history(tmp_path, "industry_b", [100.0 + offset * 0.5 for offset in range(35)])
    _write_history(tmp_path, "industry_c", [100.0 - offset * 0.1 for offset in range(35)])
    dataset = build_pit_dataset(
        tmp_path, trend_window=5, horizons=(1,), holdout_days=0
    )
    mutated = copy.deepcopy(dataset["samples"])
    shadow = mutated[-1]["score_breakdowns"]["radar_base_score"][
        "three_layer_shadow"
    ]
    shadow["weights"]["time_series"] = 0.51

    assert pit_module._sample_manifest_sha(mutated) != dataset[
        "provenance_audit"
    ]["sample_manifest_sha256"]


def test_write_validation_report_preserves_old_file_when_replace_fails(
    tmp_path, monkeypatch
):
    output = tmp_path / "pit.json"
    output.write_text('{"status":"previous"}', encoding="utf-8")

    def fail_replace(source, destination):
        raise OSError("synthetic replace failure")

    monkeypatch.setattr(strict_json_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="synthetic replace failure"):
        write_validation_report({"status": "new"}, output)

    assert output.read_text(encoding="utf-8") == '{"status":"previous"}'
    assert list(tmp_path.iterdir()) == [output]


def test_pit_three_layer_shadow_is_unchanged_by_future_source_records(tmp_path):
    before_root = tmp_path / "before"
    after_root = tmp_path / "after"
    histories = {
        "industry_a": [100.0 + offset for offset in range(35)],
        "industry_b": [100.0 + offset * 0.5 for offset in range(35)],
        "industry_c": [100.0 - offset * 0.1 for offset in range(35)],
    }
    for name, closes in histories.items():
        _write_history(before_root, name, closes)
        _write_history(after_root, name, [*closes, closes[-1] * 1.5])

    before = build_pit_dataset(
        before_root, trend_window=5, horizons=(1,), holdout_days=0
    )
    after = build_pit_dataset(
        after_root, trend_window=5, horizons=(1,), holdout_days=0
    )
    target_date = "2026-01-30"

    def shadows(dataset):
        return {
            sample["sector_name"]: sample["score_breakdowns"]["radar_base_score"][
                "three_layer_shadow"
            ]
            for sample in dataset["samples"]
            if sample["as_of_date"] == target_date
        }

    assert shadows(after) == shadows(before)


def test_pit_dataset_exposes_continuous_breakout_volume_efficiency_and_regime(tmp_path):
    closes = [100.0 + offset for offset in range(35)]
    _write_history(tmp_path, "industry_a", closes)
    _write_history(tmp_path, "industry_b", [100.0 + offset * 0.5 for offset in range(35)])
    _write_history(tmp_path, "industry_c", [100.0 - offset * 0.1 for offset in range(35)])

    dataset = build_pit_dataset(
        tmp_path, trend_window=5, horizons=(1,), holdout_days=0
    )
    mature = next(
        sample
        for sample in dataset["samples"]
        if sample["sector_name"] == "industry_a" and sample["as_of_date"] >= "2026-02-02"
    )
    inputs = mature["feature_inputs"]

    assert 0.0 <= inputs["continuous_breakout_quality_20d"] <= 1.0
    assert 0.0 <= inputs["price_volume_efficiency"] <= 1.0
    assert inputs["market_regime"] in {"risk_on", "neutral", "risk_off"}
    assert inputs["market_regime_factor"] in {1.0, 0.95, 0.85}
    assert inputs["feature_max_date"] == mature["as_of_date"]


def test_technical_evidence_requires_a_complete_twenty_session_window(tmp_path):
    closes = [100.0 + offset for offset in range(35)]
    _write_history(tmp_path, "industry_a", closes)
    _write_history(tmp_path, "industry_b", [100.0 + offset * 0.5 for offset in range(35)])
    _write_history(tmp_path, "industry_c", [100.0 - offset * 0.1 for offset in range(35)])

    dataset = build_pit_dataset(
        tmp_path, trend_window=5, horizons=(1,), holdout_days=0
    )
    early = next(
        sample
        for sample in dataset["samples"]
        if sample["sector_name"] == "industry_a" and sample["as_of_date"] == "2026-01-16"
    )
    mature = next(
        sample
        for sample in dataset["samples"]
        if sample["sector_name"] == "industry_a" and sample["as_of_date"] >= "2026-02-02"
    )

    assert early["feature_inputs"]["technical_window_status"] == "insufficient_20_session_history"
    for field in (
        "turnover_ratio_20d",
        "healthy_volume_confirmation",
        "effective_breakout_20d",
        "drawdown_from_20d_high",
        "volume_exhaustion_risk",
    ):
        assert early["feature_inputs"][field] is None
    assert mature["feature_inputs"]["technical_window_status"] == "complete_20_session_history"


def test_technical_evidence_report_excludes_incomplete_feature_rows(tmp_path):
    closes = [100.0 + offset for offset in range(35)]
    _write_history(tmp_path, "industry_a", closes)
    _write_history(tmp_path, "industry_b", [100.0 + offset * 0.5 for offset in range(35)])
    _write_history(tmp_path, "industry_c", [100.0 - offset * 0.1 for offset in range(35)])

    report = run_pit_validation(
        tmp_path,
        trend_window=5,
        horizons=(1, 3),
        holdout_days=5,
        top_k=1,
        fold_count=2,
        artifact_status="current_path_a_v3",
    )
    candidate = report["shadow_candidates"]["candidates"]["radar_technical_evidence_v2"]
    eligibility = candidate["feature_eligibility"]

    assert eligibility["total_development_samples"] == report["coverage"]["development_sample_count"]
    assert eligibility["excluded_incomplete_technical_samples"] > 0
    assert eligibility["eligible_technical_samples"] + eligibility["excluded_incomplete_technical_samples"] == eligibility["total_development_samples"]
    assert candidate["horizons"]["1d"]["sample_count"] == eligibility["eligible_technical_samples"]
    assert candidate["production_baseline_scope"] == {
        "method": "same_eligible_technical_samples",
        "sample_count": eligibility["eligible_technical_samples"],
    }
    assert (
        candidate["development_gate"]["production_baseline_comparison"]
        ["production_score_health"]["sample_count"]
        == eligibility["eligible_technical_samples"]
    )


def test_technical_walk_forward_rebuilds_folds_on_eligible_dates(tmp_path):
    closes = [100.0 + offset for offset in range(80)]
    _write_history(tmp_path, "industry_a", closes)
    _write_history(tmp_path, "industry_b", [100.0 + offset * 0.5 for offset in range(80)])
    _write_history(tmp_path, "industry_c", [100.0 - offset * 0.1 for offset in range(80)])

    report = run_pit_validation(
        tmp_path,
        trend_window=10,
        horizons=(1, 3, 5),
        holdout_days=5,
        top_k=1,
        fold_count=2,
        artifact_status="current_path_a_v3",
    )
    candidate = report["shadow_candidates"]["candidates"]["radar_technical_evidence_v3"]

    assert candidate["walk_forward_scope"]["method"] == "eligible_candidate_dates"
    folds = candidate["walk_forward"]["5d"]
    assert folds
    assert all(
        fold["train_date_count"] == fold["train_metrics"]["date_count"]
        for fold in folds
    )
    assert all(fold["train_metrics"]["date_count"] >= 10 for fold in folds)
    assert candidate["development_gate"]["checks"][
        "all_horizon_train_folds_have_at_least_10_dates"
    ] is True


def test_daily_rank_ic_and_top_k_use_cross_sectional_dates():
    rows = []
    for day in ("2026-01-05", "2026-01-06", "2026-01-07"):
        for value in (1.0, 2.0, 3.0, 4.0):
            rows.append(
                {
                    "as_of_date": day,
                    "score": value,
                    "forward_return": value,
                }
            )

    result = evaluate_score_rows(rows, top_k=1)

    assert result["date_count"] == 3
    assert result["sample_count"] == 12
    assert result["mean_daily_rank_ic"] == pytest.approx(1.0)
    assert result["top_bottom_spread"] == pytest.approx(3.0)
    assert result["top_universe_spread"] == pytest.approx(1.5)
    assert result["top_k_positive_rate"] == pytest.approx(1.0)


def test_walk_forward_folds_apply_purge_and_embargo():
    dates = [f"2026-01-{day:02d}" for day in range(1, 21)]

    folds = build_walk_forward_folds(
        dates,
        fold_count=3,
        purge_days=2,
        embargo_days=1,
        initial_train_ratio=0.4,
    )

    assert len(folds) == 3
    positions = {value: index for index, value in enumerate(dates)}
    for fold in folds:
        assert fold["train_dates"]
        assert fold["test_dates"]
        gap = (
            positions[fold["test_dates"][0]]
            - positions[fold["train_dates"][-1]]
            - 1
        )
        assert gap == 3


def test_run_pit_validation_rejects_purge_shorter_than_maximum_horizon(tmp_path):
    closes = [100.0 + offset for offset in range(35)]
    _write_history(tmp_path, "industry_a", closes)
    _write_history(tmp_path, "industry_b", [value * 0.99 for value in closes])

    with pytest.raises(ValueError, match="purge_days must be at least maximum horizon 5"):
        run_pit_validation(
            tmp_path,
            trend_window=5,
            horizons=(1, 3, 5),
            holdout_days=5,
            fold_count=2,
            purge_days=0,
            embargo_days=2,
        )


def test_run_pit_validation_accepts_purge_equal_to_maximum_horizon(tmp_path):
    closes = [100.0 + offset for offset in range(80)]
    _write_history(tmp_path, "industry_a", closes)
    _write_history(tmp_path, "industry_b", [100.0 + offset * 0.5 for offset in range(80)])
    _write_history(tmp_path, "industry_c", [100.0 - offset * 0.1 for offset in range(80)])

    report = run_pit_validation(
        tmp_path,
        trend_window=10,
        horizons=(1, 3, 5),
        holdout_days=5,
        top_k=1,
        fold_count=2,
        purge_days=5,
        embargo_days=2,
    )

    assert report["parameters"]["purge_days"] == 5


def test_pit_cli_rejects_purge_shorter_than_maximum_horizon(tmp_path, monkeypatch):
    closes = [100.0 + offset for offset in range(35)]
    _write_history(tmp_path, "industry_a", closes)
    _write_history(tmp_path, "industry_b", [value * 0.99 for value in closes])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_sector_scores_pit.py",
            "--history-root",
            str(tmp_path),
            "--output-root",
            str(tmp_path / "reports"),
            "--horizons",
            "1,3,5",
            "--purge-days",
            "4",
        ],
    )

    with pytest.raises(ValueError, match="purge_days must be at least maximum horizon 5"):
        pit_script.main()


def test_pit_cli_accepts_purge_equal_to_maximum_horizon(tmp_path, monkeypatch):
    closes = [100.0 + offset for offset in range(80)]
    _write_history(tmp_path, "industry_a", closes)
    _write_history(tmp_path, "industry_b", [100.0 + offset * 0.5 for offset in range(80)])
    _write_history(tmp_path, "industry_c", [100.0 - offset * 0.1 for offset in range(80)])
    output_root = tmp_path / "reports"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_sector_scores_pit.py",
            "--history-root",
            str(tmp_path),
            "--output-root",
            str(output_root),
            "--trend-window",
            "10",
            "--horizons",
            "1,3,5",
            "--holdout-days",
            "5",
            "--top-k",
            "1",
            "--fold-count",
            "2",
            "--purge-days",
            "5",
            "--embargo-days",
            "2",
        ],
    )

    assert pit_script.main() == 0
    assert list(output_root.rglob("sector_score_pit_validation.json"))


def test_candidate_walk_forward_reports_gap_sensitive_train_metrics():
    dates = [f"2026-01-{day:02d}" for day in range(1, 21)]
    rows = [
        {
            "as_of_date": day,
            "score": float(index),
            "forward_return": float(index if index < 8 else -index),
        }
        for index, day in enumerate(dates, start=1)
    ]
    no_gap = build_walk_forward_folds(
        dates, fold_count=2, purge_days=0, embargo_days=0, initial_train_ratio=0.5
    )
    with_gap = build_walk_forward_folds(
        dates, fold_count=2, purge_days=2, embargo_days=1, initial_train_ratio=0.5
    )

    no_gap_results = _candidate_walk_forward(rows, no_gap, top_k=2)
    gap_results = _candidate_walk_forward(rows, with_gap, top_k=2)

    assert all("train_metrics" in fold for fold in no_gap_results)
    assert all("train_metrics" in fold for fold in gap_results)
    assert (
        no_gap_results[0]["train_metrics"]["sample_count"]
        > gap_results[0]["train_metrics"]["sample_count"]
    )


def test_candidate_gate_requires_all_horizons_and_production_non_degradation():
    passing = {
        "date_count": 20,
        "sample_count": 400,
        "mean_daily_rank_ic": 0.03,
        "top_bottom_spread": 0.2,
    }
    negative_train = {
        **passing,
        "mean_daily_rank_ic": -0.01,
        "top_bottom_spread": -0.1,
    }
    horizon_results = {"1d": passing, "3d": passing, "5d": passing}
    walk_forward = {
        horizon: [
            {
                "fold": 1,
                "train_metrics": (
                    passing if horizon == "3d" else negative_train
                ),
                "metrics": metrics,
            }
        ]
        for horizon, metrics in horizon_results.items()
    }
    production_result = {
        "horizons": {horizon: passing for horizon in horizon_results},
        "walk_forward": {
            horizon: [
                {"fold": 1, "train_metrics": passing, "metrics": passing}
            ]
            for horizon in horizon_results
        },
        "score_health": {
            "constant_date_rate": 0.0,
            "tied_sample_rate": 0.1,
            "cap_rate": 0.0,
        },
    }
    rows = [
        {"as_of_date": f"2026-01-{day:02d}"}
        for day in range(1, 21)
        for _ in range(20)
    ]

    gate = _development_candidate_gate(
        horizon_results,
        walk_forward,
        rows,
        candidate_health={
            "constant_date_rate": 0.0,
            "tied_sample_rate": 0.1,
            "cap_rate": 0.0,
        },
        production_result=production_result,
    )

    assert gate["checks"]["required_1d_3d_5d_horizons_present"] is True
    assert gate["checks"]["all_horizon_train_folds_rank_ic_positive"] is False
    assert gate["checks"]["all_horizon_train_folds_top_bottom_spread_positive"] is False
    assert gate["checks"]["all_walk_forward_folds_not_worse_than_production"] is False
    assert gate["passed"] is False

    missing_horizon_gate = _development_candidate_gate(
        {"3d": passing},
        {"3d": walk_forward["3d"]},
        rows,
        candidate_health={
            "constant_date_rate": 0.0,
            "tied_sample_rate": 0.1,
            "cap_rate": 0.0,
        },
        production_result={
            **production_result,
            "horizons": {"3d": passing},
            "walk_forward": {"3d": production_result["walk_forward"]["3d"]},
        },
    )

    assert (
        missing_horizon_gate["checks"]["required_1d_3d_5d_horizons_present"]
        is False
    )
    assert missing_horizon_gate["passed"] is False


def test_validation_report_is_strict_json_and_holdout_blocks_promotion(tmp_path):
    closes = [100.0 + offset for offset in range(35)]
    _write_history(tmp_path, "行业A", closes)
    _write_history(tmp_path, "行业B", [100.0 + offset * 0.5 for offset in range(35)])
    _write_history(tmp_path, "行业C", [100.0 - offset * 0.2 for offset in range(35)])

    report = run_pit_validation(
        tmp_path,
        trend_window=5,
        horizons=(1, 3),
        holdout_days=5,
        top_k=1,
        fold_count=2,
        artifact_status="current_path_a_v3",
    )
    output = tmp_path / "report.json"
    write_validation_report(report, output)
    parsed = json.loads(output.read_text(encoding="utf-8"))

    assert parsed["mode"] == "paper_shadow_research"
    assert parsed["artifact_status"] == "current_path_a_v3"
    assert parsed["evidence_classification"] == (
        "retrospective_record_date_slice_with_unversioned_current_sector_universe"
    )
    assert parsed["strict_pit_eligible"] is False
    assert parsed["source_manifest"]["universe_vintage_status"] == (
        "not_point_in_time_versioned"
    )
    assert parsed["provenance_audit"]["universe_vintage_lookahead_eliminated"] is False
    assert parsed["promotion_gate"]["promotion_allowed"] is False
    assert "historical_sector_universe_not_versioned" in parsed["promotion_gate"][
        "blocking_reasons"
    ]
    assert parsed["promotion_gate"]["reason"] == "prospective_holdout_not_available"
    assert parsed["holdout"]["labels_materialized"] is False
    assert parsed["holdout"]["status"] == "observed_evaluation_tail"
    assert parsed["holdout"]["eligible_for_oos_claim"] is False
    assert set(parsed["score_results"]) == {
        "radar_base_score",
        "trend_continuation_score",
        "short_term_burst_score",
    }
    assert parsed["shadow_candidates"]["holdout_labels_used"] is False
    assert (
        parsed["shadow_candidates"]["definitions_locked_before_holdout_evaluation"]
        is False
    )
    assert parsed["shadow_candidates"]["eligible_for_oos_claim"] is False
    assert set(parsed["shadow_candidates"]["candidates"]) == {
        "radar_continuous_inputs_v1",
        "radar_technical_evidence_v2",
        "radar_technical_evidence_v3",
        "trend_evidence_balance_v1",
        "burst_momentum_balance_v1",
    }
    assert all(
        candidate["development_gate"]["passed"] is False
        for candidate in parsed["shadow_candidates"]["candidates"].values()
    )
    technical = parsed["shadow_candidates"]["candidates"]["radar_technical_evidence_v2"]
    assert technical["feature_eligibility"]["excluded_incomplete_technical_samples"] > 0
    v3 = parsed["shadow_candidates"]["candidates"]["radar_technical_evidence_v3"]
    assert set(v3["weights"]) == {
        "relative_strength_percentile",
        "persistence_ratio",
        "continuous_breakout_quality_20d",
        "price_volume_efficiency",
        "healthy_volume_confirmation",
        "five_day_momentum_percentile",
    }
    assert v3["market_regime_calibration"] == {
        "risk_on": 1.0,
        "neutral": 0.95,
        "risk_off": 0.85,
    }
    assert v3["market_regime_definition"] == {
        "risk_on": "median_return>=0.5 AND positive_ratio>=0.6",
        "risk_off": "median_return<=-0.5 OR positive_ratio<=0.4",
        "neutral": "otherwise",
    }
    assert v3["price_volume_efficiency_definition"] == {
        "raw": "max(one_day_return,0)/max(turnover_ratio_20d,0.5)",
        "scale": "clip_scale(raw,0,3)",
    }
    assert v3["volume_exhaustion_risk_definition"] == {
        "high_volume": "clip_scale(turnover_ratio_20d,2.0,3.5)",
        "stagnation": "1-clip_scale(abs(one_day_return),0.5,3.0)",
        "decline": "clip_scale(-one_day_return,0,3)",
        "overheat": "clip_scale(five_day_return,8,16)",
        "result": "high_volume*max(stagnation,decline,overheat)",
    }
    assert v3["constituent_breadth_status"] == "not_evaluated_historical_data_unavailable"
    assert (
        v3["feature_eligibility"]["eligible_technical_samples"]
        == technical["feature_eligibility"]["eligible_technical_samples"]
    )
    assert set(v3["factor_ablation"]) == {
        *v3["weights"],
        *v3["penalties"],
        "market_regime_calibration",
        "production_risk_penalty",
    }
    assert all(
        set(variant["horizons"]) == {"1d", "3d"}
        for variant in v3["factor_ablation"].values()
    )
    assert (
        v3["factor_ablation"]["market_regime_calibration"]["method"]
        == "neutralize_market_regime_factor_to_1_and_recompute_candidate"
    )
    assert (
        v3["factor_ablation"]["production_risk_penalty"]["method"]
        == "zero_production_risk_penalty_and_recompute_candidate"
    )
    assert sum(
        regime["sample_count"] for regime in v3["regime_attribution"].values()
    ) == v3["feature_eligibility"]["eligible_technical_samples"]

    markdown = pit_script._markdown(parsed)
    assert "- Holdout blind: false" in markdown
    assert "- Holdout eligible for OOS claim: false" in markdown
    for candidate_name in parsed["shadow_candidates"]["candidates"]:
        assert candidate_name in markdown
    for component in v3["factor_ablation"]:
        assert component in markdown
    for blocker in parsed["promotion_gate"]["blocking_reasons"]:
        assert blocker in markdown
    assert str(v3["feature_eligibility"]["eligible_technical_samples"]) in markdown
    assert str(v3["feature_eligibility"]["excluded_incomplete_technical_samples"]) in markdown
    assert "eligible_candidate_dates" in markdown
