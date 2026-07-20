"""Rounds 11-20 for paper-only historical stock-ML robustness research."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
import hashlib
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json,
    load_strict_json_with_sha256,
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
from .historical_factor_source_rebuild import SOURCE_REPORT_SCHEMA_VERSION
from .historical_iteration import FORBIDDEN_FEATURE_NAMES
from .historical_research import (
    HISTORICAL_LABEL_DEFINITION,
    HISTORICAL_LABEL_LINEAGE_STATUS,
    HISTORICAL_FEATURE_NAMES,
    historical_feature_schema_sha256,
    validate_historical_research_dataset,
)
from .ranker import (
    RankerModel,
    train_lambdarank,
    walk_forward_ranker_predictions,
)
from .schema import DISCLAIMER, MODE


EXTENSION_SCHEMA_VERSION = "ml-stock-historical-iteration-extension-v2"
ROUND_PREDICTION_SCHEMA_VERSION = "ml-stock-historical-iteration-prediction-v2"
ROUND_EVALUATION_SCHEMA_VERSION = "ml-stock-historical-iteration-evaluation-v2"
ROUND_REGISTRY_SCHEMA_VERSION = "ml-stock-historical-iteration-model-registry-v2"
ROUND_MANIFEST_SCHEMA_VERSION = "ml-stock-historical-iteration-manifest-v2"
FEATURE_INVENTORY_SCHEMA_VERSION = "ml-stock-historical-candidate-feature-inventory-v2"
ROUND_FILES = frozenset(
    {"prediction.json", "evaluation.json", "model.txt", "registry.json", "manifest.json"}
)


def extension_specs() -> tuple[dict[str, Any], ...]:
    """Return immutable, technical-only hypotheses for rounds 11-20."""

    return (
        {
            "iteration": 11,
            "id": "long_purge_10",
            "axis": "purge",
            "hypothesis": "A ten-date purge should expose sensitivity to stricter temporal separation.",
            "method": "Keep the technical baseline and extend purge from five to ten candidate dates.",
            "purge_dates": 10,
        },
        {
            "iteration": 12,
            "id": "minimum_train_70",
            "axis": "window",
            "hypothesis": "Requiring seventy mature training dates should reduce early-fold sample sensitivity.",
            "method": "Keep the technical baseline and require seventy mature training dates.",
            "min_train_dates": 70,
        },
        {
            "iteration": 13,
            "id": "rolling_train_60",
            "axis": "window",
            "hypothesis": "A sixty-date rolling cap should reveal whether old regimes dominate the expanding baseline.",
            "method": "Use the same purged walk-forward split with a sixty-date training cap.",
            "max_train_dates": 60,
        },
        {
            "iteration": 14,
            "id": "seed_20260721",
            "axis": "seed",
            "hypothesis": "A nearby deterministic seed should not reverse the baseline ranking conclusion.",
            "method": "Use random_state 20260721 under the original 60/5/5 contract.",
            "random_state": 20260721,
        },
        {
            "iteration": 15,
            "id": "compact_technical_subset",
            "axis": "feature_ablation",
            "hypothesis": "A compact technical subset should retain only signal that survives lower dimensionality.",
            "method": "Use contraction, range, drawdown, trend persistence, and close strength only.",
            "feature_names": (
                "contraction_score",
                "range10_range20",
                "drawdown_depth_20",
                "trend_persistence_score",
                "close_strength_score",
            ),
        },
        {
            "iteration": 16,
            "id": "drop_sector_and_reversal",
            "axis": "feature_ablation",
            "hypothesis": "The baseline should not rely jointly on sector support and reversal-risk calibration.",
            "method": "Drop sector_support_score and intraday_reversal_risk_score together.",
            "feature_drop": ("sector_support_score", "intraday_reversal_risk_score"),
        },
        {
            "iteration": 17,
            "id": "drop_range_drawdown_breakout",
            "axis": "feature_ablation",
            "hypothesis": "Removing range, drawdown, and breakout-distance features should expose price-shape dependence.",
            "method": "Drop range10_range20, drawdown_depth_20, and breakout_distance_20 together.",
            "feature_drop": (
                "range10_range20",
                "drawdown_depth_20",
                "breakout_distance_20",
            ),
        },
        {
            "iteration": 18,
            "id": "drop_volume_close_quality",
            "axis": "feature_ablation",
            "hypothesis": "Removing volume and close-quality features should expose execution-quality dependence.",
            "method": "Drop volume_stability_score, volume_burst_quality_score, and close_strength_score.",
            "feature_drop": (
                "volume_stability_score",
                "volume_burst_quality_score",
                "close_strength_score",
            ),
        },
        {
            "iteration": 19,
            "id": "datewise_label_rotation_control",
            "axis": "random_control",
            "hypothesis": "Rotating labels within each date should remove genuine stock-level ranking signal.",
            "method": "Deterministically rotate training labels within each date while evaluating against untouched labels.",
            "rotate_training_labels": True,
        },
        {
            "iteration": 20,
            "id": "low_complexity_model",
            "axis": "complexity",
            "hypothesis": "A smaller ranker should show whether the baseline depends on model capacity.",
            "method": "Use twenty estimators and seven leaves under the original 60/5/5 contract.",
            "n_estimators": 20,
            "num_leaves": 7,
        },
    )


def _safe_flags() -> dict[str, bool]:
    return {
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _forbidden_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in FORBIDDEN_FEATURE_NAMES:
                found.add(str(key))
            found.update(_forbidden_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_forbidden_keys(item))
    return found


def _feature_names(spec: Mapping[str, Any]) -> tuple[str, ...]:
    explicit = spec.get("feature_names")
    names = tuple(explicit) if explicit else tuple(
        name for name in BASE_FEATURE_NAMES if name not in set(spec.get("feature_drop") or ())
    )
    if not names or FORBIDDEN_FEATURE_NAMES.intersection(names):
        raise ValueError("historical extension feature contract is unsafe")
    if any(name not in BASE_FEATURE_NAMES for name in names):
        raise ValueError("historical extension feature is outside the technical baseline")
    return names


def _model_feature_names(raw_feature_names: Sequence[str]) -> tuple[str, ...]:
    return tuple(raw_feature_names) + tuple(
        f"{name}_missing" for name in raw_feature_names
    )


def _allowed_model_feature(name: str) -> bool:
    return name in BASE_FEATURE_NAMES or (
        name.endswith("_missing") and name[: -len("_missing")] in BASE_FEATURE_NAMES
    )


def build_candidate_feature_inventory(
    dataset: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, float | None]]]:
    """Replay daily candidate factor snapshots and inventory actual finite coverage."""

    validate_historical_research_dataset(dataset)
    selected_raw = {
        name for spec in extension_specs() for name in _feature_names(spec)
    }
    approved = set(HISTORICAL_FEATURE_NAMES)
    stats: dict[str, dict[str, Any]] = {}
    values: dict[tuple[str, str], dict[str, float | None]] = {}
    candidate_sources: list[dict[str, Any]] = []
    snapshot_as_of_exact_rows = 0
    snapshot_as_of_inherited_rows = 0
    for entry in dataset["source_manifest"]["candidate_sources"]:
        path = Path(str(entry.get("path") or ""))
        payload, source_sha = load_strict_json_with_sha256(path)
        day = str(entry.get("as_of_date") or "")
        if source_sha != entry.get("sha256") or payload.get("as_of") != day:
            raise ValueError("historical iteration candidate inventory source mismatch")
        candidates = payload.get("candidates")
        if not isinstance(candidates, list) or payload.get("candidate_count") != len(candidates):
            raise ValueError("historical iteration candidate inventory count mismatch")
        candidate_sources.append(
            {"as_of_date": day, "path": str(path.resolve()), "sha256": source_sha}
        )
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                raise ValueError("historical iteration candidate inventory row is invalid")
            code = str(candidate.get("code") or "").zfill(6)
            if len(code) != 6 or not code.isdigit():
                raise ValueError("historical iteration candidate inventory code is invalid")
            identity = (day, code)
            if identity in values:
                raise ValueError("historical iteration candidate inventory identity duplicated")
            snapshot = candidate.get("factor_snapshot")
            if (
                not isinstance(snapshot, Mapping)
                or str(snapshot.get("code") or "").zfill(6) != code
            ):
                raise ValueError("historical iteration factor snapshot identity mismatch")
            snapshot_as_of = str(snapshot.get("as_of") or "")
            if snapshot_as_of not in ("", day):
                raise ValueError("historical iteration factor snapshot date conflicts with source")
            if snapshot_as_of == day:
                snapshot_as_of_exact_rows += 1
            else:
                snapshot_as_of_inherited_rows += 1
            factors = snapshot.get("factors")
            if not isinstance(factors, list):
                raise ValueError("historical iteration factor snapshot rows are missing")
            by_name: dict[str, Mapping[str, Any]] = {}
            for factor in factors:
                if not isinstance(factor, Mapping):
                    raise ValueError("historical iteration factor snapshot row is invalid")
                name = str(factor.get("factor_id") or "")
                if not name or name in by_name:
                    raise ValueError("historical iteration factor identity is invalid or duplicated")
                by_name[name] = factor
                item = stats.setdefault(
                    name,
                    {
                        "present_rows": 0,
                        "finite_rows": 0,
                        "categories": set(),
                        "source_projects": set(),
                    },
                )
                item["present_rows"] += 1
                raw = factor.get("raw_value")
                if (
                    isinstance(raw, (int, float))
                    and not isinstance(raw, bool)
                    and math.isfinite(float(raw))
                ):
                    item["finite_rows"] += 1
                if factor.get("category"):
                    item["categories"].add(str(factor["category"]))
                if factor.get("source_project"):
                    item["source_projects"].add(str(factor["source_project"]))
            row_values: dict[str, float | None] = {}
            for name in HISTORICAL_FEATURE_NAMES:
                factor = by_name.get(name)
                raw = factor.get("raw_value") if factor is not None else None
                row_values[name] = (
                    float(raw)
                    if isinstance(raw, (int, float))
                    and not isinstance(raw, bool)
                    and math.isfinite(float(raw))
                    else None
                )
            values[identity] = row_values
    expected = {
        (str(row["as_of_date"]), str(row["stock_code"]).zfill(6))
        for row in dataset["feature_universe_records"]
    }
    if set(values) != expected:
        raise ValueError("historical iteration inventory identities do not match v9")
    total = len(values)
    inventory_rows = []
    for name in sorted(stats):
        item = stats[name]
        if name in FORBIDDEN_FEATURE_NAMES:
            exclusion = "protected_score_field"
        elif "label" in name or name.startswith(("future_", "forward_")):
            exclusion = "future_or_label_derived_field"
        elif name not in approved:
            exclusion = "outside_preregistered_historical_feature_contract"
        else:
            exclusion = None
        inventory_rows.append(
            {
                "feature_name": name,
                "categories": sorted(item["categories"]),
                "source_projects": sorted(item["source_projects"]),
                "present_rows": int(item["present_rows"]),
                "finite_rows": int(item["finite_rows"]),
                "finite_coverage_ratio": item["finite_rows"] / total if total else 0.0,
                "approved_for_historical_ml": exclusion is None,
                "selected_by_round11_20": name in selected_raw,
                "exclusion_reason": exclusion,
            }
        )
    if FORBIDDEN_FEATURE_NAMES.intersection(selected_raw):
        raise ValueError("historical iteration inventory selected protected fields")
    core = {
        "schema_version": FEATURE_INVENTORY_SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "dataset_sha256": dataset["dataset_sha256"],
        "candidate_source_count": len(candidate_sources),
        "candidate_sources": candidate_sources,
        "candidate_date_count": len({day for day, _code in values}),
        "candidate_row_count": total,
        "snapshot_contract": "stock code must match the nested factor_snapshot; blank nested as_of inherits only the content-bound candidate file as_of_date",
        "snapshot_as_of_exact_rows": snapshot_as_of_exact_rows,
        "snapshot_as_of_inherited_rows": snapshot_as_of_inherited_rows,
        "approved_raw_feature_names": sorted(approved),
        "selected_raw_feature_names": sorted(selected_raw),
        "missing_value_policy": "every selected raw feature is paired with an explicit _missing indicator; numeric zero is never silent",
        "ranking_policy": "cross-sectional ranking grouped by as_of_date",
        "label_policy": "future labels are used only for model training and evaluation, never as prediction inputs",
        "rule_parallel_policy": "ML shadow scores remain parallel to rule baselines and never overwrite formal ranking fields",
        "features": inventory_rows,
        **_safe_flags(),
    }
    artifact = {
        **core,
        "inventory_sha256": canonical_sha256(core),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(artifact, context="historical candidate feature inventory")
    return artifact, values


def _rotate_labels(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_date[str(row["as_of_date"])].append(dict(row))
    rotated: list[dict[str, Any]] = []
    for day in sorted(by_date):
        rows = sorted(by_date[day], key=lambda row: str(row["stock_code"]))
        if len(rows) < 2:
            rotated.extend(rows)
            continue
        labels = [float(row["training_label"]) for row in rows]
        for index, row in enumerate(rows):
            row["training_label"] = labels[(index + 1) % len(labels)]
            rotated.append(row)
    return rotated


def _baseline_comparison(
    metrics: Mapping[str, Any], baseline_metrics: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        key: {
            metric: (
                value.get(metric) - baseline_metrics[key].get(metric)
                if isinstance(value.get(metric), (int, float))
                and isinstance(baseline_metrics.get(key, {}).get(metric), (int, float))
                else None
            )
            for metric in ("lift_vs_universe", "mean_rank_ic", "win_rate_vs_universe")
        }
        for key, value in metrics.items()
        if isinstance(value, Mapping) and key in baseline_metrics
    }


def _cost_sensitivity(metrics: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    return {
        str(cost_bps): {
            "assumption": "flat rebalance cost deducted from each selected daily portfolio return",
            "top_k_adjusted_lift_vs_universe": {
                top_k: (
                    float(values["lift_vs_universe"]) - cost_bps / 10_000.0
                    if isinstance(values.get("lift_vs_universe"), (int, float))
                    else None
                )
                for top_k, values in metrics.items()
            },
        }
        for cost_bps in (0, 10, 25)
    }


def _final_fold_training_rows(
    records: Sequence[Mapping[str, Any]], prediction: Mapping[str, Any]
) -> list[dict[str, Any]]:
    folds = prediction.get("folds")
    if not isinstance(folds, list) or not folds:
        raise ValueError("historical extension final fold is unavailable")
    final_fold = folds[-1]
    start = str(final_fold.get("train_universe_start") or "")
    end = str(final_fold.get("train_universe_end") or "")
    test_start = date.fromisoformat(str(final_fold.get("test_start") or ""))
    selected = [
        dict(row)
        for row in records
        if start <= str(row.get("as_of_date") or "") <= end
        and date.fromisoformat(str(row.get("training_label_end_date") or "")) < test_start
    ]
    if len(selected) != int(final_fold.get("train_row_count") or 0):
        raise ValueError("historical extension final model rows do not match fold audit")
    if len({row["as_of_date"] for row in selected}) != int(
        final_fold.get("train_date_count") or 0
    ):
        raise ValueError("historical extension final model dates do not match fold audit")
    return selected


def _run_round(
    spec: Mapping[str, Any],
    dataset: Mapping[str, Any],
    contexts: Mapping[tuple[str, str], Mapping[str, Any]],
    baseline_metrics: Mapping[str, Any],
    source_values: Mapping[tuple[str, str], Mapping[str, float | None]],
) -> tuple[dict[str, Any], RankerModel]:
    raw_feature_names = _feature_names(spec)
    feature_names = _model_feature_names(raw_feature_names)
    records, universe = build_ablation_views(dataset, contexts, "A_technical_baseline")
    for row in records + universe:
        identity = (str(row["as_of_date"]), str(row["stock_code"]).zfill(6))
        observed = source_values.get(identity)
        if observed is None:
            raise ValueError("historical iteration source feature identity is missing")
        features: dict[str, float] = {}
        for name in raw_feature_names:
            raw = observed.get(name)
            if raw is not None and not math.isclose(
                float(row["features"][name]), float(raw), abs_tol=1e-12
            ):
                raise ValueError("historical iteration v9 feature differs from source snapshot")
            features[name] = float(raw) if raw is not None else 0.0
        for name in raw_feature_names:
            features[f"{name}_missing"] = float(observed.get(name) is None)
        row["features"] = features
    if spec.get("rotate_training_labels"):
        records = _rotate_labels(records)
    contract = {
        "min_train_dates": int(spec.get("min_train_dates", 60)),
        "test_dates": 5,
        "purge_dates": int(spec.get("purge_dates", 5)),
        "max_train_dates": spec.get("max_train_dates"),
        "max_label_horizon": 5,
        "n_estimators": int(spec.get("n_estimators", 80)),
        "num_leaves": int(spec.get("num_leaves", 15)),
        "random_state": int(spec.get("random_state", 20260718)),
    }
    prediction = walk_forward_ranker_predictions(
        records,
        prediction_universe_records=universe,
        feature_names=feature_names,
        **contract,
    )
    if prediction.get("status") != "ok":
        raise ValueError(f"round walk-forward unavailable: {prediction.get('reason')}")
    prediction = {
        key: value for key, value in prediction.items() if key != "generated_at"
    }
    prediction = {
        **prediction,
        "schema_version": ROUND_PREDICTION_SCHEMA_VERSION,
        "iteration": int(spec["iteration"]),
        "iteration_id": str(spec["id"]),
        "experiment_axis": str(spec["axis"]),
        "raw_feature_names": list(raw_feature_names),
        "missing_indicator_names": [
            f"{name}_missing" for name in raw_feature_names
        ],
        "training_label_control": (
            "datewise_deterministic_rotation"
            if spec.get("rotate_training_labels")
            else "unaltered"
        ),
        "evaluation_label_source": "unaltered_v9_dataset",
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "dataset_sha256": dataset["dataset_sha256"],
        "prediction_rows_sha256": canonical_sha256(prediction["predictions"]),
        **_safe_flags(),
        "disclaimer": DISCLAIMER,
    }
    evaluation = evaluate_ablation_predictions(
        dataset, prediction, contexts, top_ks=(1, 3, 5)
    )
    final_rows = _final_fold_training_rows(records, prediction)
    model = train_lambdarank(
        final_rows,
        feature_names=feature_names,
        n_estimators=contract["n_estimators"],
        num_leaves=contract["num_leaves"],
        random_state=contract["random_state"],
    )
    result = {
        "feature_names": list(feature_names),
        "raw_feature_names": list(raw_feature_names),
        "missing_indicator_names": [
            f"{name}_missing" for name in raw_feature_names
        ],
        "experiment_contract": {
            "split_type": prediction["split_type"],
            **contract,
            "training_label_control": prediction["training_label_control"],
        },
        "prediction": prediction,
        **evaluation,
        "cost_sensitivity": _cost_sensitivity(evaluation["metrics"]),
        "baseline_comparison": _baseline_comparison(
            evaluation["metrics"], baseline_metrics
        ),
    }
    return result, model


def _validate_source_gate(source_report: Mapping[str, Any]) -> None:
    expected = {
        "schema_version": SOURCE_REPORT_SCHEMA_VERSION,
        "status": "blocked_insufficient_strict_pit_coverage",
        "incremental_direction_linkage_experiment_allowed": False,
        **_safe_flags(),
    }
    if any(source_report.get(key) != value for key, value in expected.items()):
        raise ValueError("round11-20 requires the v2 blocking historical factor source gate")
    counts = source_report.get("counts") or {}
    if counts.get("direction_strict_pit_eligible_rows") != 0:
        raise ValueError("unexpected eligible direction rows require a new preregistered suite")
    if counts.get("linkage_strict_pit_eligible_rows") != 0:
        raise ValueError("unexpected eligible Linkage rows require a new preregistered suite")
    core = {
        key: value
        for key, value in source_report.items()
        if key not in {"rebuild_report_sha256", "disclaimer"}
    }
    if source_report.get("rebuild_report_sha256") != canonical_sha256(core):
        raise ValueError("round11-20 source rebuild gate logical SHA mismatch")


def _run_extension_core(
    dataset: Mapping[str, Any],
    baseline_report: Mapping[str, Any],
    previous_suite: Mapping[str, Any],
    previous_suite_file_sha256: str,
    source_report: Mapping[str, Any],
    source_values: Mapping[tuple[str, str], Mapping[str, float | None]],
) -> tuple[dict[str, Any], dict[int, RankerModel]]:
    validate_historical_research_dataset(dataset)
    _validate_source_gate(source_report)
    dataset_sha = dataset.get("dataset_sha256")
    if baseline_report.get("dataset_sha256") != dataset_sha:
        raise ValueError("round11-20 baseline dataset SHA mismatch")
    if previous_suite.get("dataset_sha256") != dataset_sha:
        raise ValueError("round11-20 previous suite dataset SHA mismatch")
    if previous_suite.get("iteration_count") != 10 or [
        item.get("iteration") for item in previous_suite.get("iterations") or []
    ] != list(range(1, 11)):
        raise ValueError("round11-20 previous suite is not the completed ten-round baseline")
    contexts, coverage = build_ablation_context_rows(dataset)
    baseline_metrics = baseline_report["groups"]["A_technical_baseline"]["metrics"]
    rounds: list[dict[str, Any]] = []
    models: dict[int, RankerModel] = {}
    for spec in extension_specs():
        try:
            result, model = _run_round(
                spec, dataset, contexts, baseline_metrics, source_values
            )
            models[int(spec["iteration"])] = model
            item = {
                "iteration": spec["iteration"],
                "id": spec["id"],
                "axis": spec["axis"],
                "hypothesis": spec["hypothesis"],
                "method": spec["method"],
                "status": "completed",
                "decision": (
                    "eliminate_null_control"
                    if spec.get("rotate_training_labels")
                    else "retain_as_research_evidence_only"
                ),
                "result": result,
            }
        except Exception as exc:  # Failed experiments remain visible in the suite.
            item = {
                "iteration": spec["iteration"],
                "id": spec["id"],
                "axis": spec["axis"],
                "hypothesis": spec["hypothesis"],
                "method": spec["method"],
                "status": "failed",
                "decision": "eliminated_due_to_failure",
                "error": f"{type(exc).__name__}: {exc}",
            }
        rounds.append(item)
    report = {
        "schema_version": EXTENSION_SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "dataset_sha256": dataset_sha,
        "prior_rounds": {
            "iteration_count": 10,
            "suite_schema_version": previous_suite.get("schema_version"),
            "suite_file_sha256": previous_suite_file_sha256,
            "policy": "verified_read_only_reference_not_recomputed",
        },
        "source_rebuild_gate": {
            "schema_version": source_report.get("schema_version"),
            "rebuild_report_sha256": source_report.get("rebuild_report_sha256"),
            "incremental_direction_linkage_experiment_allowed": False,
            "direction_exact_name_observed_rows": int(
                source_report["counts"]["direction_exact_name_observed_rows"]
            ),
            "direction_strict_pit_eligible_rows": 0,
            "linkage_strict_pit_eligible_rows": 0,
            "factor_usage_policy": "observed direction and Linkage values are excluded from every feature matrix",
        },
        "baseline": {
            "schema_version": baseline_report.get("schema_version"),
            "top1_top3_top5_metrics": {
                key: baseline_metrics[key] for key in ("1", "3", "5")
            },
        },
        "source_coverage": coverage,
        "round_count": len(rounds),
        "total_iteration_count": 20,
        "rounds": rounds,
        **_safe_flags(),
        "paper_only_policy": "Every completed round emits a research-only model and registry that the formal loader must reject.",
        "conclusion_scope": "technical robustness only; direction and Linkage V2 remain unvalidated",
        "limitations": [
            "All rounds reuse the same 99-date historical reconstruction window.",
            "Split-changing rounds have different evaluation date sets and their baseline deltas are descriptive only.",
            "Direction and Linkage V2 are excluded because strict source coverage is zero.",
            "Flat cost sensitivity is a stress assumption, not an execution simulator.",
            "No result from this window supports promotion or an OOS claim.",
        ],
        "disclaimer": DISCLAIMER,
    }
    if _forbidden_keys(report):
        raise ValueError("historical iteration extension contains protected fields")
    validate_no_executable_instructions(report, context="historical iteration extension")
    return report, models


def run_historical_iteration_extension(
    dataset: Mapping[str, Any],
    baseline_report: Mapping[str, Any],
    previous_suite: Mapping[str, Any],
    previous_suite_file_sha256: str,
    source_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Run only rounds 11-20; rounds 1-10 are verified and never recomputed."""

    _inventory, source_values = build_candidate_feature_inventory(dataset)
    report, _models = _run_extension_core(
        dataset,
        baseline_report,
        previous_suite,
        previous_suite_file_sha256,
        source_report,
        source_values,
    )
    return report


def _write_model_registry(
    round_dir: Path,
    model: RankerModel,
    *,
    item: Mapping[str, Any],
    dataset_sha256: str,
    prior_rounds: Mapping[str, Any],
    source_gate: Mapping[str, Any],
    feature_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    model_path = round_dir / "model.txt"
    temporary = round_dir / ".model.txt.tmp"
    try:
        model.booster.save_model(str(temporary))
        os.replace(temporary, model_path)
    finally:
        temporary.unlink(missing_ok=True)
    model_sha = _sha256(model_path)
    result = item["result"]
    registry = {
        "schema_version": ROUND_REGISTRY_SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "iteration": int(item["iteration"]),
        "iteration_id": str(item["id"]),
        "experiment_axis": str(item["axis"]),
        "model_version": f"stock-ranker-historical-round-{int(item['iteration']):02d}-{item['id']}",
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "dataset_sha256": dataset_sha256,
        "prior_rounds": dict(prior_rounds),
        "source_rebuild_gate": dict(source_gate),
        "feature_inventory": dict(feature_inventory),
        "feature_schema_version": "ml-stock-historical-iteration-technical-features-v2",
        "feature_schema_sha256": historical_feature_schema_sha256(model.feature_names),
        "feature_names": list(model.feature_names),
        "feature_input_policy": {
            "source": "daily v9 candidate factor_snapshot technical features or an explicit subset",
            "raw_feature_names": list(result["raw_feature_names"]),
            "missing_indicator_names": list(result["missing_indicator_names"]),
            "direction_feature_count": 0,
            "linkage_v2_feature_count": 0,
            "protected_feature_count": 0,
        },
        "label_definition": HISTORICAL_LABEL_DEFINITION,
        "label_price_lineage_status": HISTORICAL_LABEL_LINEAGE_STATUS,
        "training_label_control": result["experiment_contract"]["training_label_control"],
        "experiment_contract": dict(result["experiment_contract"]),
        "training_period": dict(model.metadata["training_period"]),
        "label_maturity_period": dict(model.metadata["label_maturity_period"]),
        "training_records_sha256": model.metadata["training_records_sha256"],
        "parameters": dict(model.metadata["parameters"]),
        "model_artifact": {"path": "model.txt", "sha256": model_sha},
        **_safe_flags(),
        "disclaimer": DISCLAIMER,
    }
    if _forbidden_keys(registry):
        raise ValueError("historical iteration registry contains protected fields")
    validate_no_executable_instructions(registry, context="historical iteration registry")
    write_strict_json_atomic(round_dir / "registry.json", registry)
    return registry


def _evaluation_artifact(
    item: Mapping[str, Any],
    *,
    dataset_sha256: str,
    source_gate: Mapping[str, Any],
    feature_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    result = item["result"]
    core = {
        "schema_version": ROUND_EVALUATION_SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "iteration": int(item["iteration"]),
        "iteration_id": str(item["id"]),
        "experiment_axis": str(item["axis"]),
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "dataset_sha256": dataset_sha256,
        "source_rebuild_gate": dict(source_gate),
        "feature_inventory": dict(feature_inventory),
        "feature_names": list(result["feature_names"]),
        "raw_feature_names": list(result["raw_feature_names"]),
        "missing_indicator_names": list(result["missing_indicator_names"]),
        "experiment_contract": dict(result["experiment_contract"]),
        "prediction_rows_sha256": result["prediction"]["prediction_rows_sha256"],
        "evaluation_label_source": "unaltered_v9_dataset",
        "top_k_values": [1, 3, 5],
        "metrics": result["metrics"],
        "daily_metrics": result["daily_metrics"],
        "fold_stability": result["fold_stability"],
        "regime_slices": result["regime_slices"],
        "cost_sensitivity": result["cost_sensitivity"],
        "baseline_comparison": result["baseline_comparison"],
        **_safe_flags(),
    }
    artifact = {
        **core,
        "evaluation_sha256": canonical_sha256(core),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(artifact, context="historical iteration evaluation")
    return artifact


def validate_historical_iteration_artifact_directory(
    round_dir: Path | str,
) -> dict[str, Any]:
    directory = Path(round_dir)
    files = {path.name for path in directory.iterdir() if path.is_file()}
    if files != ROUND_FILES or any(path.is_dir() for path in directory.iterdir()):
        raise ValueError("historical iteration artifact file contract mismatch")
    manifest, manifest_file_sha = load_strict_json_with_sha256(directory / "manifest.json")
    prediction = load_strict_json(directory / "prediction.json")
    evaluation = load_strict_json(directory / "evaluation.json")
    registry, registry_file_sha = load_strict_json_with_sha256(directory / "registry.json")
    if manifest.get("schema_version") != ROUND_MANIFEST_SCHEMA_VERSION:
        raise ValueError("historical iteration manifest schema mismatch")
    manifest_core = {
        key: value
        for key, value in manifest.items()
        if key not in {"manifest_sha256", "disclaimer"}
    }
    if manifest.get("manifest_sha256") != canonical_sha256(manifest_core):
        raise ValueError("historical iteration manifest logical SHA mismatch")
    references = manifest.get("artifacts")
    if not isinstance(references, Mapping) or set(references) != {
        "prediction", "evaluation", "model", "registry"
    }:
        raise ValueError("historical iteration manifest references are incomplete")
    for name, expected_file in (
        ("prediction", "prediction.json"),
        ("evaluation", "evaluation.json"),
        ("model", "model.txt"),
        ("registry", "registry.json"),
    ):
        reference = references[name]
        if reference.get("path") != expected_file or reference.get("sha256") != _sha256(
            directory / expected_file
        ):
            raise ValueError("historical iteration artifact physical SHA mismatch")
    if registry_file_sha != references["registry"]["sha256"]:
        raise ValueError("historical iteration registry SHA mismatch")
    if registry.get("schema_version") != ROUND_REGISTRY_SCHEMA_VERSION:
        raise ValueError("historical iteration registry schema mismatch")
    if registry.get("model_artifact") != references["model"]:
        raise ValueError("historical iteration registry model binding mismatch")
    identities = {
        (artifact.get("iteration"), artifact.get("iteration_id"))
        for artifact in (manifest, prediction, evaluation, registry)
    }
    if len(identities) != 1:
        raise ValueError("historical iteration artifact identity mismatch")
    dataset_shas = {
        artifact.get("dataset_sha256") for artifact in (manifest, prediction, evaluation, registry)
    }
    if len(dataset_shas) != 1:
        raise ValueError("historical iteration artifact dataset SHA mismatch")
    inventory_path = directory.parent / "feature_inventory.json"
    inventory, inventory_file_sha = load_strict_json_with_sha256(inventory_path)
    inventory_refs = {
        tuple(sorted((artifact.get("feature_inventory") or {}).items()))
        for artifact in (manifest, prediction, evaluation, registry)
    }
    expected_inventory_ref = {
        "path": "../feature_inventory.json",
        "sha256": inventory_file_sha,
        "inventory_sha256": inventory.get("inventory_sha256"),
    }
    if inventory_refs != {tuple(sorted(expected_inventory_ref.items()))}:
        raise ValueError("historical iteration feature inventory binding mismatch")
    inventory_core = {
        key: value
        for key, value in inventory.items()
        if key not in {"inventory_sha256", "disclaimer"}
    }
    if (
        inventory.get("schema_version") != FEATURE_INVENTORY_SCHEMA_VERSION
        or inventory.get("inventory_sha256") != canonical_sha256(inventory_core)
    ):
        raise ValueError("historical iteration feature inventory identity mismatch")
    if prediction.get("prediction_rows_sha256") != canonical_sha256(
        prediction.get("predictions") or []
    ):
        raise ValueError("historical iteration prediction rows SHA mismatch")
    if evaluation.get("prediction_rows_sha256") != prediction.get("prediction_rows_sha256"):
        raise ValueError("historical iteration evaluation prediction binding mismatch")
    evaluation_core = {
        key: value
        for key, value in evaluation.items()
        if key not in {"evaluation_sha256", "disclaimer"}
    }
    if evaluation.get("evaluation_sha256") != canonical_sha256(evaluation_core):
        raise ValueError("historical iteration evaluation logical SHA mismatch")
    feature_names = tuple(registry.get("feature_names") or ())
    if (
        feature_names != tuple(prediction.get("feature_names") or ())
        or feature_names != tuple(evaluation.get("feature_names") or ())
        or FORBIDDEN_FEATURE_NAMES.intersection(feature_names)
        or any(not _allowed_model_feature(name) for name in feature_names)
    ):
        raise ValueError("historical iteration artifact feature contract mismatch")
    for artifact in (manifest, prediction, evaluation, registry):
        if any(artifact.get(key) is not False for key in _safe_flags()):
            raise ValueError("historical iteration artifact safety flags mismatch")
        if _forbidden_keys(artifact):
            raise ValueError("historical iteration artifact contains protected fields")
    gate = registry.get("source_rebuild_gate") or {}
    if (
        gate.get("direction_strict_pit_eligible_rows") != 0
        or gate.get("linkage_strict_pit_eligible_rows") != 0
        or gate.get("incremental_direction_linkage_experiment_allowed") is not False
    ):
        raise ValueError("historical iteration artifact source gate mismatch")
    return {
        "iteration": manifest["iteration"],
        "iteration_id": manifest["iteration_id"],
        "manifest_file_sha256": manifest_file_sha,
        "registry_file_sha256": registry_file_sha,
        "model_file_sha256": references["model"]["sha256"],
        "feature_inventory_file_sha256": inventory_file_sha,
    }


def write_historical_iteration_extension(
    dataset_path: Path | str,
    baseline_path: Path | str,
    previous_suite_path: Path | str,
    source_report_path: Path | str,
    output_root: Path | str,
) -> dict[str, Any]:
    destination = Path(output_root)
    if destination.exists():
        raise FileExistsError(f"historical iteration extension output exists: {destination}")
    dataset = load_strict_json(dataset_path)
    baseline = load_strict_json(baseline_path)
    previous_suite, previous_suite_sha = load_strict_json_with_sha256(previous_suite_path)
    source_report = load_strict_json(source_report_path)
    inventory, source_values = build_candidate_feature_inventory(dataset)
    destination.mkdir(parents=True)
    write_strict_json_atomic(destination / "feature_inventory.json", inventory)
    feature_inventory_ref = {
        "path": "../feature_inventory.json",
        "sha256": _sha256(destination / "feature_inventory.json"),
        "inventory_sha256": inventory["inventory_sha256"],
    }
    report, models = _run_extension_core(
        dataset,
        baseline,
        previous_suite,
        previous_suite_sha,
        source_report,
        source_values,
    )
    suite_rounds: list[dict[str, Any]] = []
    for item in report["rounds"]:
        if item.get("status") != "completed":
            raise RuntimeError(
                f"round {item['iteration']} failed and cannot satisfy the five-artifact contract: {item.get('error')}"
            )
        iteration = int(item["iteration"])
        round_dir = destination / f"iteration_{iteration:02d}_{item['id']}"
        round_dir.mkdir()
        prediction = {
            **item["result"]["prediction"],
            "feature_inventory": feature_inventory_ref,
        }
        write_strict_json_atomic(round_dir / "prediction.json", prediction)
        evaluation = _evaluation_artifact(
            item,
            dataset_sha256=str(report["dataset_sha256"]),
            source_gate=report["source_rebuild_gate"],
            feature_inventory=feature_inventory_ref,
        )
        write_strict_json_atomic(round_dir / "evaluation.json", evaluation)
        registry = _write_model_registry(
            round_dir,
            models[iteration],
            item=item,
            dataset_sha256=str(report["dataset_sha256"]),
            prior_rounds=report["prior_rounds"],
            source_gate=report["source_rebuild_gate"],
            feature_inventory=feature_inventory_ref,
        )
        artifact_refs = {
            name: {"path": filename, "sha256": _sha256(round_dir / filename)}
            for name, filename in (
                ("prediction", "prediction.json"),
                ("evaluation", "evaluation.json"),
                ("model", "model.txt"),
                ("registry", "registry.json"),
            )
        }
        manifest_core = {
            "schema_version": ROUND_MANIFEST_SCHEMA_VERSION,
            "mode": MODE,
            "status": "research_only",
            "iteration": iteration,
            "iteration_id": str(item["id"]),
            "experiment_axis": str(item["axis"]),
            "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
            "dataset_sha256": report["dataset_sha256"],
            "prior_rounds": report["prior_rounds"],
            "source_rebuild_gate": report["source_rebuild_gate"],
            "feature_inventory": feature_inventory_ref,
            "feature_names": item["result"]["feature_names"],
            "raw_feature_names": item["result"]["raw_feature_names"],
            "missing_indicator_names": item["result"]["missing_indicator_names"],
            "experiment_contract": item["result"]["experiment_contract"],
            "artifact_contract": "prediction/evaluation/model/registry are content-bound below",
            "artifacts": artifact_refs,
            **_safe_flags(),
        }
        manifest = {
            **manifest_core,
            "manifest_sha256": canonical_sha256(manifest_core),
            "disclaimer": DISCLAIMER,
        }
        validate_no_executable_instructions(manifest, context="historical iteration manifest")
        write_strict_json_atomic(round_dir / "manifest.json", manifest)
        verified = validate_historical_iteration_artifact_directory(round_dir)
        suite_rounds.append(
            {
                "iteration": iteration,
                "id": item["id"],
                "axis": item["axis"],
                "hypothesis": item["hypothesis"],
                "method": item["method"],
                "status": item["status"],
                "decision": item["decision"],
                "feature_names": item["result"]["feature_names"],
                "raw_feature_names": item["result"]["raw_feature_names"],
                "missing_indicator_names": item["result"]["missing_indicator_names"],
                "experiment_contract": item["result"]["experiment_contract"],
                "metrics": item["result"]["metrics"],
                "cost_sensitivity": item["result"]["cost_sensitivity"],
                "baseline_comparison": item["result"]["baseline_comparison"],
                "artifacts": {
                    **artifact_refs,
                    "manifest": {
                        "path": "manifest.json",
                        "sha256": verified["manifest_file_sha256"],
                    },
                },
            }
        )
    suite = {
        **{key: value for key, value in report.items() if key != "rounds"},
        "feature_inventory": {
            "path": "feature_inventory.json",
            "sha256": feature_inventory_ref["sha256"],
            "inventory_sha256": feature_inventory_ref["inventory_sha256"],
        },
        "rounds": suite_rounds,
        "artifact_contract": {
            "files_per_round": sorted(ROUND_FILES),
            "formal_loader_policy": "every registry uses a non-formal research schema and must be rejected",
        },
    }
    if _forbidden_keys(suite):
        raise ValueError("historical iteration suite contains protected fields")
    validate_no_executable_instructions(suite, context="historical iteration suite")
    write_strict_json_atomic(destination / "suite_report.json", suite)
    return suite
