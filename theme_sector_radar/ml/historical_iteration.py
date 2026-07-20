"""Ten paper-only follow-up iterations for historical ML shadow research."""

from __future__ import annotations

from collections import defaultdict
import copy
import math
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json,
    write_strict_json_atomic,
)

from .contract import canonical_sha256
from .historical_factor_ablation import (
    BASE_FEATURE_NAMES,
    HISTORICAL_DATASET_CLASSIFICATION,
    build_ablation_context_rows,
    build_ablation_views,
    evaluate_ablation_predictions,
)
from .historical_research import validate_historical_research_dataset
from .ranker import walk_forward_ranker_predictions
from .schema import DISCLAIMER, MODE


ITERATION_SUITE_SCHEMA_VERSION = "ml-stock-historical-iteration-suite-v1"
ITERATION_COUNT = 10
FORBIDDEN_FEATURE_NAMES = frozenset(
    {
        "quant_score",
        "final_score",
        "v2_score",
        "selection_score",
        "selection_score_adjusted",
        "relevance_score",
        "legacy_relevance_score",
    }
)


def iteration_specs() -> tuple[dict[str, Any], ...]:
    """Return the immutable hypotheses for the ten follow-up rounds."""

    return (
        {
            "iteration": 1,
            "id": "complete_fold_sensitivity",
            "kind": "model",
            "hypothesis": "Removing the incomplete tail fold should not materially change the technical baseline conclusion.",
            "method": "Use only the first 95 candidate dates, keeping expanding 60/5/5 folds complete.",
            "n_estimators": 80,
            "top_ks": [1, 3, 5],
            "decision_policy": "retain_only_as_complete_fold_robustness_check",
        },
        {
            "iteration": 2,
            "id": "top_k_sensitivity",
            "kind": "model",
            "hypothesis": "The baseline conclusion should not depend on the selected top-k reporting point.",
            "method": "Run the technical baseline with top-k values 1, 2, 3, 5, and 10.",
            "n_estimators": 80,
            "top_ks": [1, 2, 3, 5, 10],
            "decision_policy": "retain_as_reporting_sensitivity_only",
        },
        {
            "iteration": 3,
            "id": "random_seed_sensitivity",
            "kind": "multi_model",
            "hypothesis": "Technical-baseline conclusions should be stable across nearby deterministic seeds.",
            "method": "Run the same fixed split with seeds 20260719 and 20260720, never using a promotion decision.",
            "seeds": [20260719, 20260720],
            "n_estimators": 80,
            "top_ks": [1, 3, 5],
            "decision_policy": "retain_only_if_seed_spread_is_small",
        },
        {
            "iteration": 4,
            "id": "estimator_sensitivity",
            "kind": "multi_model",
            "hypothesis": "The observed baseline signal should not be an artifact of one tree-count choice.",
            "method": "Compare 40 and 120 estimators under the same 60/5/5 split and seed.",
            "estimators": [40, 120],
            "n_estimators": 80,
            "top_ks": [1, 3, 5],
            "decision_policy": "retain_as_hyperparameter_sensitivity_only",
        },
        {
            "iteration": 5,
            "id": "drop_sector_support",
            "kind": "feature_subset",
            "hypothesis": "The technical baseline should not depend entirely on the sector-support feature.",
            "method": "Drop sector_support_score from the stability_core_v1 research-only feature subset.",
            "feature_drop": ["sector_support_score"],
            "n_estimators": 80,
            "top_ks": [1, 3, 5],
            "decision_policy": "retain_if_direction_of_effect_is_consistent",
        },
        {
            "iteration": 6,
            "id": "drop_reversal_risk",
            "kind": "feature_subset",
            "hypothesis": "The technical baseline should remain informative without intraday reversal-risk calibration.",
            "method": "Drop intraday_reversal_risk_score from the stability_core_v1 research-only feature subset.",
            "feature_drop": ["intraday_reversal_risk_score"],
            "n_estimators": 80,
            "top_ks": [1, 3, 5],
            "decision_policy": "retain_if_direction_of_effect_is_consistent",
        },
        {
            "iteration": 7,
            "id": "datewise_shuffle_control",
            "kind": "shuffle_control",
            "hypothesis": "A date-wise feature shuffle should remove ranking power if the baseline signal is real.",
            "method": "Rotate feature vectors within each as-of date while preserving labels, row counts, and feature distributions.",
            "n_estimators": 80,
            "top_ks": [1, 3, 5],
            "decision_policy": "retain_as_null_control_only",
        },
        {
            "iteration": 8,
            "id": "daily_bootstrap_uncertainty",
            "kind": "bootstrap",
            "hypothesis": "The baseline lift is too uncertain to support a promotion claim even if its point estimate is positive.",
            "method": "Bootstrap existing baseline daily metrics 1000 times with a fixed seed; do not refit a model.",
            "bootstrap_replicates": 1000,
            "bootstrap_seed": 20260720,
            "decision_policy": "retain_as_uncertainty_evidence_only",
        },
        {
            "iteration": 9,
            "id": "source_manifest_tamper_rejection",
            "kind": "rejection_control",
            "hypothesis": "Changing a declared physical source identity must block historical dataset validation.",
            "method": "Tamper only an in-memory source-manifest SHA and require validate_historical_research_dataset to reject it.",
            "decision_policy": "retain_gate_if_rejected",
        },
        {
            "iteration": 10,
            "id": "label_row_tamper_rejection",
            "kind": "rejection_control",
            "hypothesis": "Changing an in-memory historical label without rebuilding its dataset identity must block validation.",
            "method": "Tamper one in-memory training label while leaving the dataset SHA and source manifest unchanged.",
            "decision_policy": "retain_gate_if_rejected",
        },
    )


def _assert_safe_feature_names(feature_names: Sequence[str]) -> None:
    if FORBIDDEN_FEATURE_NAMES.intersection(feature_names):
        raise ValueError("historical iteration contains a forbidden feature")


def _date_filter(
    rows: Sequence[Mapping[str, Any]], dates: set[str] | None
) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in rows
        if dates is None or str(row.get("as_of_date") or "") in dates
    ]


def _technical_views(
    dataset: Mapping[str, Any],
    contexts: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    dates: set[str] | None = None,
    feature_names: tuple[str, ...] = BASE_FEATURE_NAMES,
    shuffle: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records, universe = build_ablation_views(dataset, contexts, "A_technical_baseline")
    records = _date_filter(records, dates)
    universe = _date_filter(universe, dates)
    _assert_safe_feature_names(feature_names)
    if shuffle:
        universe_by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in universe:
            universe_by_day[str(row["as_of_date"])].append(row)
        shuffled_features: dict[tuple[str, str], Mapping[str, float]] = {}
        for day, day_rows in universe_by_day.items():
            ordered = sorted(day_rows, key=lambda row: str(row["stock_code"]))
            for index, row in enumerate(ordered):
                source = ordered[(index + 1) % len(ordered)]
                shuffled_features[(day, str(row["stock_code"]).zfill(6))] = source["features"]
        for row in universe:
            identity = (str(row["as_of_date"]), str(row["stock_code"]).zfill(6))
            row["features"] = {
                name: float(shuffled_features[identity][name]) for name in feature_names
            }
        record_by_identity = {
            (str(row["as_of_date"]), str(row["stock_code"]).zfill(6)): row
            for row in universe
        }
        for row in records:
            identity = (str(row["as_of_date"]), str(row["stock_code"]).zfill(6))
            source = record_by_identity.get(identity)
            if source is None:
                raise ValueError("shuffle control identity mismatch")
            row["features"] = dict(source["features"])
    else:
        for row in records + universe:
            row["features"] = {name: float(row["features"][name]) for name in feature_names}
    return records, universe


def _prediction_run(
    dataset: Mapping[str, Any],
    contexts: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    feature_names: tuple[str, ...],
    top_ks: Sequence[int],
    n_estimators: int,
    random_state: int = 20260718,
    dates: set[str] | None = None,
    shuffle: bool = False,
) -> dict[str, Any]:
    records, universe = _technical_views(
        dataset,
        contexts,
        dates=dates,
        feature_names=feature_names,
        shuffle=shuffle,
    )
    prediction = walk_forward_ranker_predictions(
        records,
        prediction_universe_records=universe,
        feature_names=feature_names,
        min_train_dates=60,
        test_dates=5,
        purge_dates=5,
        max_label_horizon=5,
        n_estimators=n_estimators,
        random_state=random_state,
    )
    if prediction.get("status") != "ok":
        raise ValueError(f"iteration walk-forward unavailable: {prediction.get('reason')}")
    prediction = {
        **prediction,
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "dataset_sha256": dataset["dataset_sha256"],
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "prediction_rows_sha256": canonical_sha256(prediction["predictions"]),
        "disclaimer": DISCLAIMER,
    }
    metrics = evaluate_ablation_predictions(
        dataset, prediction, contexts, top_ks=top_ks
    )
    return {
        "feature_names": list(feature_names),
        "prediction": prediction,
        **metrics,
    }


def _baseline_comparison(
    metrics: Mapping[str, Any], baseline_metrics: Mapping[str, Any]
) -> dict[str, Any]:
    comparison: dict[str, Any] = {}
    for key, value in metrics.items():
        base = baseline_metrics.get(key)
        if not isinstance(value, Mapping) or not isinstance(base, Mapping):
            continue
        comparison[key] = {
            metric: (
                value.get(metric) - base.get(metric)
                if isinstance(value.get(metric), (int, float))
                and isinstance(base.get(metric), (int, float))
                else None
            )
            for metric in ("lift_vs_universe", "mean_rank_ic", "win_rate_vs_universe")
        }
    return comparison


def _bootstrap_report(
    baseline_report: Mapping[str, Any], *, replicates: int, seed: int
) -> dict[str, Any]:
    daily = list(
        baseline_report["groups"]["A_technical_baseline"]["daily_metrics"]["1"]
    )
    if not daily:
        raise ValueError("baseline daily metrics are empty")
    state = int(seed) & 0xFFFFFFFF
    samples: list[float] = []
    for _ in range(replicates):
        values: list[float] = []
        for _index in range(len(daily)):
            state = (1664525 * state + 1013904223) & 0xFFFFFFFF
            values.append(float(daily[state % len(daily)]["lift_vs_universe"]))
        samples.append(mean(values))
    ordered = sorted(samples)
    p05 = ordered[max(0, int(replicates * 0.05) - 1)]
    p50 = ordered[max(0, int(replicates * 0.50) - 1)]
    p95 = ordered[max(0, int(replicates * 0.95) - 1)]
    return {
        "sample_date_count": len(daily),
        "replicates": replicates,
        "seed": seed,
        "top1_lift_point_estimate": baseline_report["groups"]["A_technical_baseline"]["metrics"]["1"]["lift_vs_universe"],
        "top1_lift_bootstrap_p05": p05,
        "top1_lift_bootstrap_median": p50,
        "top1_lift_bootstrap_p95": p95,
        "positive_lift_fraction": sum(value > 0 for value in samples) / len(samples),
    }


def _safe_flags() -> dict[str, bool]:
    return {
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
    }


def _run_one(
    spec: Mapping[str, Any],
    dataset: Mapping[str, Any],
    contexts: Mapping[tuple[str, str], Mapping[str, Any]],
    baseline_report: Mapping[str, Any],
) -> dict[str, Any]:
    kind = str(spec["kind"])
    if kind == "bootstrap":
        result: dict[str, Any] = _bootstrap_report(
            baseline_report,
            replicates=int(spec["bootstrap_replicates"]),
            seed=int(spec["bootstrap_seed"]),
        )
        decision = "uncertainty_only_no_promotion"
    elif kind == "rejection_control":
        tampered = copy.deepcopy(dataset)
        if spec["id"] == "source_manifest_tamper_rejection":
            tampered["source_manifest"]["calendar"]["sha256"] = "0" * 64
        else:
            tampered["records"][0]["training_label"] = float(
                tampered["records"][0]["training_label"]
            ) + 0.000001
        try:
            validate_historical_research_dataset(tampered)
        except (ValueError, OSError) as exc:
            result = {"rejected": True, "error": str(exc)}
            decision = "gate_retained_rejected_as_expected"
        else:
            raise AssertionError("tampered historical input was accepted")
    else:
        top_ks = tuple(int(value) for value in spec["top_ks"])
        feature_names = tuple(
            name for name in BASE_FEATURE_NAMES if name not in set(spec.get("feature_drop", []))
        )
        if kind == "multi_model":
            variants: dict[str, Any] = {}
            values = spec.get("seeds") or spec.get("estimators") or []
            for value in values:
                variants[str(value)] = _prediction_run(
                    dataset,
                    contexts,
                    feature_names=feature_names,
                    top_ks=top_ks,
                    n_estimators=(
                        int(value) if spec["id"] == "estimator_sensitivity" else int(spec["n_estimators"])
                    ),
                    random_state=(
                        int(value) if spec["id"] == "random_seed_sensitivity" else 20260718
                    ),
                )
            result = {"variants": variants}
            decision = "retain_as_sensitivity_evidence_only"
        else:
            dates = None
            if spec["id"] == "complete_fold_sensitivity":
                all_dates = sorted({str(row["as_of_date"]) for row in dataset["feature_universe_records"]})
                dates = set(all_dates[:95])
            run = _prediction_run(
                dataset,
                contexts,
                feature_names=feature_names,
                top_ks=top_ks,
                n_estimators=int(spec["n_estimators"]),
                dates=dates,
                shuffle=spec["id"] == "datewise_shuffle_control",
            )
            result = run
            decision = "retain_as_research_control"
    return {
        "iteration": spec["iteration"],
        "id": spec["id"],
        "hypothesis": spec["hypothesis"],
        "method": spec["method"],
        "decision_policy": spec["decision_policy"],
        "status": "completed",
        "decision": decision,
        "result": result,
    }


def run_historical_iteration_suite(
    dataset: Mapping[str, Any],
    baseline_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Run ten non-promotable follow-ups without changing source files."""

    validate_historical_research_dataset(dataset)
    if baseline_report.get("dataset_sha256") != dataset.get("dataset_sha256"):
        raise ValueError("iteration baseline and dataset SHA mismatch")
    contexts, coverage = build_ablation_context_rows(dataset)
    baseline_group = baseline_report["groups"]["A_technical_baseline"]
    baseline_metrics = baseline_group["metrics"]
    iterations: list[dict[str, Any]] = []
    for spec in iteration_specs():
        try:
            item = _run_one(spec, dataset, contexts, baseline_report)
        except Exception as exc:  # Preserve failed experiments as first-class artifacts.
            item = {
                "iteration": spec["iteration"],
                "id": spec["id"],
                "hypothesis": spec["hypothesis"],
                "method": spec["method"],
                "decision_policy": spec["decision_policy"],
                "status": "failed",
                "decision": "eliminated_due_to_failure",
                "error": f"{type(exc).__name__}: {exc}",
            }
        if item.get("status") == "completed" and isinstance(item.get("result"), Mapping):
            result = item["result"]
            if "metrics" in result:
                item["baseline_comparison"] = _baseline_comparison(
                    result["metrics"], baseline_metrics
                )
            elif "variants" in result:
                item["baseline_comparison"] = {
                    name: _baseline_comparison(value["metrics"], baseline_metrics)
                    for name, value in result["variants"].items()
                }
        iterations.append(item)
    report = {
        "schema_version": ITERATION_SUITE_SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "dataset_sha256": dataset["dataset_sha256"],
        "baseline": {
            "schema_version": baseline_report.get("schema_version"),
            "dataset_sha256": baseline_report.get("dataset_sha256"),
            "top1_top3_top5_metrics": {
                key: baseline_metrics[key]
                for key in ("1", "3", "5")
                if key in baseline_metrics
            },
        },
        "source_coverage": coverage,
        "experiment_contract": {
            "split_type": "expanding_date_grouped_walk_forward",
            "min_train_dates": 60,
            "test_dates": 5,
            "purge_dates": 5,
            "max_label_horizon": 5,
            "same_contract_for_model_iterations": True,
        },
        "iteration_count": len(iterations),
        "iterations": iterations,
        **_safe_flags(),
        "paper_only_policy": "No formal model bundle, predictor registration, broker, order, or live-trading output is emitted.",
        "limitations": [
            "Direction and Linkage V2 coverage remains zero in the real historical candidate archive.",
            "Historical source bars are reconstructed and are not prospective strict-PIT evidence.",
            "Model iterations use the existing technical baseline as a comparator and do not justify promotion.",
        ],
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(report, context="historical iteration suite")
    return report


def write_historical_iteration_suite(
    dataset_path: Path | str,
    baseline_path: Path | str,
    output_root: Path | str,
) -> dict[str, Any]:
    destination = Path(output_root)
    if destination.exists():
        raise FileExistsError(f"historical iteration output already exists: {destination}")
    dataset = load_strict_json(dataset_path)
    baseline = load_strict_json(baseline_path)
    report = run_historical_iteration_suite(dataset, baseline)
    destination.mkdir(parents=True)
    for item in report["iterations"]:
        artifact = {
            "schema_version": f"{ITERATION_SUITE_SCHEMA_VERSION}-{int(item['iteration']):02d}",
            "mode": MODE,
            "status": "research_only",
            "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
            "dataset_sha256": report["dataset_sha256"],
            "baseline": report["baseline"],
            "experiment_contract": report["experiment_contract"],
            "iteration": item,
            **_safe_flags(),
            "disclaimer": DISCLAIMER,
        }
        validate_no_executable_instructions(artifact, context="historical iteration artifact")
        iteration_dir = destination / f"iteration_{int(item['iteration']):02d}_{item['id']}"
        iteration_dir.mkdir()
        write_strict_json_atomic(iteration_dir / "iteration_report.json", artifact)
    write_strict_json_atomic(destination / "suite_report.json", report)
    return report
