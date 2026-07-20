from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from theme_sector_radar.reporting.strict_json import write_strict_json_atomic


def _dates(count: int = 12) -> list[str]:
    start = date(2026, 1, 5)
    return [(start + timedelta(days=index)).isoformat() for index in range(count)]


def _factor_rows(value: float) -> list[dict]:
    from theme_sector_radar.ml.historical_research import HISTORICAL_FEATURE_NAMES

    return [
        {
            "factor_id": name,
            "raw_value": value,
            "score": value,
            "quality": "good",
            "tags": ["bars_calculated"],
        }
        for name in HISTORICAL_FEATURE_NAMES
    ]


def _write_fixture(root: Path, *, day_count: int = 8) -> tuple[Path, Path, Path]:
    dates = _dates(day_count + 5)
    candidate_root = root / "candidates"
    forward_root = root / "forward"
    calendar_path = root / "calendar.json"
    write_strict_json_atomic(
        calendar_path,
        {
            "schema_version": "test-calendar-v1",
            "dates": dates,
            "source": "unit_test_exchange_calendar",
        },
    )
    for index, day in enumerate(dates[:day_count]):
        candidate_path = candidate_root / day / "top30_candidates.intraday_backfilled.json"
        candidates = []
        items = []
        for offset, code in enumerate(("000001", "000002", "000003")):
            value = float(index + offset + 1)
            candidates.append(
                {
                    "code": code,
                    "name": f"stock-{code}",
                    "boards": ["sector-a"],
                    "factor_snapshot": {
                        "schema_version": "1.0",
                        "as_of": day,
                        "code": code,
                        "factors": _factor_rows(value),
                    },
                    "quant_score": 50.0 + offset,
                    "final_score": 60.0 + offset,
                    "selection_score": 55.0 + offset,
                }
            )
            items.append(
                {
                    "code": code,
                    "as_of": day,
                    "5d": float((offset - 1) * 2 + index / 10),
                    "close_t": 100.0,
                    "close_5d": 100.0 * (1.0 + ((offset - 1) * 2 + index / 10) / 100.0),
                    "data_quality": "ok",
                    "bars_source": "unit_test_client",
                    "bars_count": 11,
                    "bars_start": dates[max(0, index - 5)],
                    "bars_end": dates[index + 5],
                }
            )
        write_strict_json_atomic(
            candidate_path,
            {
                "schema_version": "1.0",
                "as_of": day,
                "candidate_count": len(candidates),
                "candidates": candidates,
            },
        )
        write_strict_json_atomic(
            forward_root / f"{day}.json",
            {
                "schema_version": "1.0",
                "as_of": day,
                "generated_at": f"{dates[index + 5]}T18:00:00+08:00",
                "horizons": ["5d"],
                "items": items,
            },
        )
    return candidate_root, forward_root, calendar_path


def test_historical_research_dataset_is_non_promotable_and_excludes_protected_scores(
    tmp_path: Path,
):
    from theme_sector_radar.ml.historical_research import (
        HISTORICAL_FEATURE_NAMES,
        build_historical_research_dataset,
        validate_historical_research_dataset,
    )

    candidate_root, forward_root, calendar_path = _write_fixture(tmp_path)
    dataset = build_historical_research_dataset(
        candidate_root,
        forward_root,
        calendar_path,
    )
    records = validate_historical_research_dataset(dataset)

    assert dataset["dataset_classification"] == "historical_reconstruction_research"
    assert dataset["strict_pit_eligible"] is False
    assert dataset["eligible_for_oos_claim"] is False
    assert dataset["promotion_allowed"] is False
    assert dataset["live_trading_allowed"] is False
    assert len(dataset["source_manifest"]["candidate_sources"]) == 8
    assert len(records) == 24
    assert tuple(records[0]["features"]) == HISTORICAL_FEATURE_NAMES
    assert not {
        "quant_score",
        "final_score",
        "v2_score",
        "selection_score",
        "selection_score_adjusted",
    } & set(records[0]["features"])
    assert records[0]["training_label_end_date"] > records[0]["as_of_date"]


def test_historical_research_dataset_rejects_forward_date_mismatch(tmp_path: Path):
    from theme_sector_radar.ml.historical_research import (
        build_historical_research_dataset,
    )

    candidate_root, forward_root, calendar_path = _write_fixture(tmp_path)
    path = forward_root / f"{_dates()[0]}.json"
    payload = __import__(
        "theme_sector_radar.reporting.strict_json", fromlist=["load_strict_json"]
    ).load_strict_json(path)
    payload["as_of"] = _dates()[1]
    write_strict_json_atomic(path, payload)

    with pytest.raises(ValueError, match="forward source date mismatch"):
        build_historical_research_dataset(candidate_root, forward_root, calendar_path)


def test_historical_research_dataset_skips_immature_empty_forward_date(tmp_path: Path):
    from theme_sector_radar.ml.historical_research import (
        build_historical_research_dataset,
    )
    from theme_sector_radar.reporting.strict_json import load_strict_json

    candidate_root, forward_root, calendar_path = _write_fixture(tmp_path)
    day = _dates()[0]
    path = forward_root / f"{day}.json"
    payload = load_strict_json(path)
    payload["generated_at"] = f"{day}T18:00:00+08:00"
    for item in payload["items"]:
        item["5d"] = None
    write_strict_json_atomic(path, payload)

    dataset = build_historical_research_dataset(
        candidate_root, forward_root, calendar_path
    )
    assert day not in {row["as_of_date"] for row in dataset["records"]}


def test_historical_research_dataset_rejects_immature_nonempty_label(tmp_path: Path):
    from theme_sector_radar.ml.historical_research import (
        build_historical_research_dataset,
    )
    from theme_sector_radar.reporting.strict_json import load_strict_json

    candidate_root, forward_root, calendar_path = _write_fixture(tmp_path)
    day = _dates()[0]
    path = forward_root / f"{day}.json"
    payload = load_strict_json(path)
    payload["generated_at"] = f"{day}T18:00:00+08:00"
    write_strict_json_atomic(path, payload)

    with pytest.raises(ValueError, match="predates label maturity"):
        build_historical_research_dataset(candidate_root, forward_root, calendar_path)


def test_historical_research_dataset_replays_forward_return_prices(tmp_path: Path):
    from theme_sector_radar.ml.historical_research import (
        build_historical_research_dataset,
    )
    from theme_sector_radar.reporting.strict_json import load_strict_json

    candidate_root, forward_root, calendar_path = _write_fixture(tmp_path)
    path = forward_root / f"{_dates()[0]}.json"
    payload = load_strict_json(path)
    payload["items"][0]["5d"] += 1.0
    write_strict_json_atomic(path, payload)

    with pytest.raises(ValueError, match="cannot be replayed"):
        build_historical_research_dataset(candidate_root, forward_root, calendar_path)


def test_historical_dataset_rejects_rehashed_in_memory_row_tampering(tmp_path: Path):
    from theme_sector_radar.ml.contract import canonical_sha256
    from theme_sector_radar.ml.historical_research import (
        build_historical_research_dataset,
        validate_historical_research_dataset,
    )

    candidate_root, forward_root, calendar_path = _write_fixture(tmp_path)
    dataset = build_historical_research_dataset(
        candidate_root, forward_root, calendar_path
    )
    dataset["records"][0]["training_label"] += 0.25
    core = {
        key: dataset[key]
        for key in dataset
        if key not in {"dataset_sha256", "disclaimer"}
    }
    dataset["dataset_sha256"] = canonical_sha256(core)

    with pytest.raises(ValueError, match="source manifest"):
        validate_historical_research_dataset(dataset)


def test_walk_forward_accepts_registered_historical_feature_schema(tmp_path: Path):
    from theme_sector_radar.ml.historical_research import (
        HISTORICAL_FEATURE_NAMES,
        build_historical_research_dataset,
    )
    from theme_sector_radar.ml.ranker import walk_forward_ranker_predictions

    candidate_root, forward_root, calendar_path = _write_fixture(tmp_path)
    dataset = build_historical_research_dataset(
        candidate_root,
        forward_root,
        calendar_path,
    )
    report = walk_forward_ranker_predictions(
        dataset["records"],
        prediction_universe_records=dataset["feature_universe_records"],
        feature_names=HISTORICAL_FEATURE_NAMES,
        min_train_dates=2,
        test_dates=2,
        purge_dates=5,
        max_label_horizon=5,
        n_estimators=2,
        max_train_dates=2,
    )

    assert report["status"] == "ok"
    assert report["predictions"]
    assert report["promotion_allowed"] is False
    assert report["live_trading_allowed"] is False
    assert all(fold["train_universe_date_count"] <= 2 for fold in report["folds"])


def test_historical_research_bundle_is_rejected_by_formal_model_loader(tmp_path: Path):
    from theme_sector_radar.ml.contract import canonical_sha256
    from theme_sector_radar.ml.historical_research import (
        HISTORICAL_FEATURE_NAMES,
        save_historical_research_bundle,
    )
    from theme_sector_radar.ml.ranker import train_lambdarank
    from theme_sector_radar.ml.registry import load_model_bundle

    rows = []
    dates = _dates(4)
    for day_index, day in enumerate(dates):
        for code_index, code in enumerate(("000001", "000002", "000003")):
            rows.append(
                {
                    "as_of_date": day,
                    "stock_code": code,
                    "sector_name": "sector-a",
                    "features": {
                        name: float(day_index + code_index + feature_index)
                        for feature_index, name in enumerate(HISTORICAL_FEATURE_NAMES)
                    },
                    "training_label": float(code_index),
                    "training_label_end_date": (date.fromisoformat(day) + timedelta(days=5)).isoformat(),
                }
            )
    model = train_lambdarank(
        rows,
        feature_names=HISTORICAL_FEATURE_NAMES,
        n_estimators=2,
    )
    saved = save_historical_research_bundle(
        model,
        tmp_path / "model",
        model_version="historical-research-v1",
        dataset_sha256=canonical_sha256(rows),
    )

    registry = saved["registry"]
    assert registry["dataset_classification"] == "historical_reconstruction_research"
    assert registry["formal_predictor_compatible"] is False
    assert registry["promotion_allowed"] is False
    assert registry["live_trading_allowed"] is False
    with pytest.raises(ValueError, match="schema mismatch"):
        load_model_bundle(
            tmp_path / "model",
            expected_registry_sha256=saved["registry_sha256"],
        )


def test_historical_evaluation_compares_ml_and_rule_without_promotion(tmp_path: Path):
    from theme_sector_radar.ml.historical_research import (
        HISTORICAL_FEATURE_NAMES,
        bind_historical_walk_forward_report,
        build_historical_research_dataset,
        evaluate_historical_walk_forward,
    )
    from theme_sector_radar.ml.ranker import walk_forward_ranker_predictions

    candidate_root, forward_root, calendar_path = _write_fixture(tmp_path)
    dataset = build_historical_research_dataset(
        candidate_root, forward_root, calendar_path
    )
    predictions = walk_forward_ranker_predictions(
        dataset["records"],
        prediction_universe_records=dataset["feature_universe_records"],
        feature_names=HISTORICAL_FEATURE_NAMES,
        min_train_dates=2,
        test_dates=2,
        purge_dates=5,
        max_label_horizon=5,
        n_estimators=2,
    )
    bound_predictions = bind_historical_walk_forward_report(
        dataset, predictions, feature_profile="all_v1"
    )
    evaluation = evaluate_historical_walk_forward(dataset, bound_predictions, top_k=2)

    assert evaluation["status"] == "research_only"
    assert evaluation["dataset_classification"] == "historical_reconstruction_research"
    assert evaluation["strict_pit_eligible"] is False
    assert evaluation["eligible_for_oos_claim"] is False
    assert evaluation["promotion_allowed"] is False
    assert evaluation["live_trading_allowed"] is False
    assert evaluation["metrics"]["evaluated_date_count"] > 0
    assert evaluation["metrics"]["ml_top_k_mean_return"] is not None
    assert evaluation["metrics"]["rule_top_k_mean_return"] is not None
    assert evaluation["metrics"]["ml_win_rate_vs_universe"] is not None
    assert evaluation["metrics"]["ml_win_rate_vs_rule"] is not None
    assert evaluation["metrics"]["mean_spearman_rank_ic"] is not None
    assert set(evaluation["top_k_sensitivity"]) == {"1", "3", "5"}
    assert evaluation["fold_metrics"]


def test_historical_evaluation_rejects_forged_predictions(tmp_path: Path):
    from theme_sector_radar.ml.historical_research import (
        HISTORICAL_FEATURE_NAMES,
        bind_historical_walk_forward_report,
        build_historical_research_dataset,
        evaluate_historical_walk_forward,
    )
    from theme_sector_radar.ml.ranker import walk_forward_ranker_predictions

    candidate_root, forward_root, calendar_path = _write_fixture(tmp_path)
    dataset = build_historical_research_dataset(
        candidate_root, forward_root, calendar_path
    )
    raw = walk_forward_ranker_predictions(
        dataset["records"],
        prediction_universe_records=dataset["feature_universe_records"],
        feature_names=HISTORICAL_FEATURE_NAMES,
        min_train_dates=2,
        test_dates=2,
        purge_dates=5,
        max_label_horizon=5,
        n_estimators=2,
    )
    report = bind_historical_walk_forward_report(
        dataset, raw, feature_profile="all_v1"
    )
    report["predictions"][0]["ml_quant_score_shadow"] = 99.123

    with pytest.raises(ValueError, match="deterministic replay mismatch"):
        evaluate_historical_walk_forward(dataset, report, top_k=2)


def test_missing_rule_baseline_does_not_shrink_ml_universe(tmp_path: Path):
    from theme_sector_radar.ml.historical_research import (
        HISTORICAL_FEATURE_NAMES,
        bind_historical_walk_forward_report,
        build_historical_research_dataset,
        evaluate_historical_walk_forward,
    )
    from theme_sector_radar.ml.ranker import walk_forward_ranker_predictions

    candidate_root, forward_root, calendar_path = _write_fixture(tmp_path)
    from theme_sector_radar.reporting.strict_json import load_strict_json
    for path in candidate_root.glob("*/top30_candidates.intraday_backfilled.json"):
        payload = load_strict_json(path)
        for candidate in payload["candidates"]:
            candidate.pop("selection_score", None)
            candidate.pop("final_score", None)
        write_strict_json_atomic(path, payload)
    dataset = build_historical_research_dataset(
        candidate_root, forward_root, calendar_path
    )
    raw = walk_forward_ranker_predictions(
        dataset["records"],
        prediction_universe_records=dataset["feature_universe_records"],
        feature_names=HISTORICAL_FEATURE_NAMES,
        min_train_dates=2,
        test_dates=2,
        purge_dates=5,
        max_label_horizon=5,
        n_estimators=2,
    )
    report = bind_historical_walk_forward_report(
        dataset, raw, feature_profile="all_v1"
    )
    evaluation = evaluate_historical_walk_forward(dataset, report, top_k=2)

    assert evaluation["metrics"]["evaluated_row_count"] == sum(
        row["row_count"] for row in evaluation["daily_metrics"]
    )
    assert any(
        row["rule_comparison_row_count"] < row["row_count"]
        for row in evaluation["daily_metrics"]
    )


def test_historical_research_cli_writes_isolated_cycle(tmp_path: Path, monkeypatch):
    from scripts.run_ml_stock_historical_research import main
    from theme_sector_radar.reporting.strict_json import load_strict_json

    candidate_root, forward_root, calendar_path = _write_fixture(tmp_path)
    output_root = tmp_path / "output"
    model_dir = tmp_path / "model"
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_ml_stock_historical_research.py",
            "--candidate-root",
            str(candidate_root),
            "--forward-root",
            str(forward_root),
            "--calendar",
            str(calendar_path),
            "--output-root",
            str(output_root),
            "--model-dir",
            str(model_dir),
            "--model-version",
            "historical-cli-v1",
            "--min-train-dates",
            "2",
            "--test-dates",
            "2",
            "--purge-dates",
            "5",
            "--n-estimators",
            "2",
            "--top-k",
            "2",
        ],
    )

    assert main() == 0
    report = load_strict_json(output_root / "cycle_report.json")
    registry = load_strict_json(model_dir / "registry.json")
    assert report["status"] == "research_only"
    assert report["promotion_allowed"] is False
    assert report["live_trading_allowed"] is False
    assert report["formal_predictor_compatible"] is False
    assert registry["schema_version"] == "ml-stock-historical-research-model-v1"
    assert (model_dir / "model.txt").is_file()
