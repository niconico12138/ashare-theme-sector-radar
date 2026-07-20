"""Paper-only historical feature ablation for direction and Linkage V2."""

from __future__ import annotations

from collections import defaultdict
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256

from .contract import canonical_sha256, require_finite
from .historical_research import (
    HISTORICAL_DATASET_CLASSIFICATION,
    HISTORICAL_FEATURE_PROFILES,
    build_historical_research_dataset,
    validate_historical_research_dataset,
)
from .ranker import walk_forward_ranker_predictions
from .schema import DISCLAIMER, MODE


ABLATION_SCHEMA_VERSION = "ml-stock-historical-factor-ablation-v1"
BASE_FEATURE_NAMES = tuple(HISTORICAL_FEATURE_PROFILES["stability_core_v1"])
DIRECTION_FEATURE_NAMES = (
    "direction_score",
    "direction_score_missing",
)
LINKAGE_COMPONENTS = (
    ("return_comovement_20d", "linkage_return_comovement_20d"),
    ("relative_strength_5d_10d", "linkage_relative_strength_5d_10d"),
    ("constituent_weight", "linkage_constituent_weight"),
    ("fund_flow_alignment", "linkage_fund_flow_alignment"),
    ("data_quality", "linkage_data_quality"),
)
LINKAGE_FEATURE_NAMES = (
    "linkage_score",
    "linkage_available_weight",
    "linkage_score_missing",
    "linkage_present",
    *tuple(name for _component, name in LINKAGE_COMPONENTS),
    *tuple(f"{name}_missing" for _component, name in LINKAGE_COMPONENTS),
)
INTERACTION_FEATURE_NAMES = (
    "direction_x_linkage_score",
    "direction_x_linkage_score_missing",
    *tuple(
        f"direction_x_{name}"
        for _component, name in LINKAGE_COMPONENTS
    ),
    *tuple(
        f"direction_x_{name}_missing"
        for _component, name in LINKAGE_COMPONENTS
    ),
)
FEATURE_GROUPS = {
    "A_technical_baseline": BASE_FEATURE_NAMES,
    "B_plus_direction": BASE_FEATURE_NAMES + DIRECTION_FEATURE_NAMES,
    "C_plus_linkage_v2": BASE_FEATURE_NAMES + LINKAGE_FEATURE_NAMES,
    "D_direction_linkage_interaction": (
        BASE_FEATURE_NAMES
        + DIRECTION_FEATURE_NAMES
        + LINKAGE_FEATURE_NAMES
        + INTERACTION_FEATURE_NAMES
    ),
}
ALL_ABLATION_FEATURE_NAMES = frozenset(
    name for names in FEATURE_GROUPS.values() for name in names
)
REGIME_BUCKETS = ("risk_off", "neutral", "risk_on", "unknown")


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _normalised_score(value: Any, *, maximum: float) -> float | None:
    number = _finite(value)
    if number is None or not 0.0 <= number <= maximum:
        return None
    return number / maximum


def _regime_bucket(value: Any) -> str:
    number = _normalised_score(value, maximum=100.0)
    if number is None:
        return "unknown"
    if number < 0.45:
        return "risk_off"
    if number < 0.60:
        return "neutral"
    return "risk_on"


def _linkage_mapping(candidate: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for key in ("linkage_v2_shadow", "linkage_v2", "linkage_v2_breakdown"):
        value = candidate.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _identity(day: str, code: Any) -> tuple[str, str]:
    return day, str(code or "").zfill(6)


def _empty_context() -> dict[str, Any]:
    context = {
        "direction_score": 0.0,
        "direction_score_missing": 1.0,
        "linkage_score": 0.0,
        "linkage_available_weight": 0.0,
        "linkage_score_missing": 1.0,
        "linkage_present": 0.0,
        "regime": "unknown",
    }
    for _component, name in LINKAGE_COMPONENTS:
        context[name] = 0.0
        context[f"{name}_missing"] = 1.0
    return context


def _extract_context(candidate: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    context = _empty_context()
    quality = {
        "direction_present": 0,
        "direction_invalid": 0,
        "linkage_present": 0,
        "linkage_score_present": 0,
        "linkage_component_present": 0,
        "linkage_component_invalid": 0,
        "regime_present": 0,
    }

    direction_value = candidate.get("sector_direction_score")
    if direction_value is None:
        direction_value = candidate.get("direction_score_shadow")
    direction = _normalised_score(direction_value, maximum=100.0)
    if direction is None:
        if direction_value is not None:
            quality["direction_invalid"] += 1
    else:
        context["direction_score"] = direction
        context["direction_score_missing"] = 0.0
        quality["direction_present"] += 1

    linkage = _linkage_mapping(candidate)
    if linkage is not None:
        context["linkage_present"] = 1.0
        quality["linkage_present"] += 1
        score = _normalised_score(linkage.get("score"), maximum=1.0)
        available_weight = _normalised_score(
            linkage.get("available_weight"), maximum=1.0
        )
        if score is not None:
            context["linkage_score"] = score
            context["linkage_score_missing"] = 0.0
            quality["linkage_score_present"] += 1
        if available_weight is not None:
            context["linkage_available_weight"] = available_weight
        components = linkage.get("components")
        if isinstance(components, Mapping):
            for component, name in LINKAGE_COMPONENTS:
                item = components.get(component)
                raw = item.get("score") if isinstance(item, Mapping) else None
                value = _normalised_score(raw, maximum=1.0)
                if value is None:
                    if raw is not None:
                        quality["linkage_component_invalid"] += 1
                    continue
                context[name] = value
                context[f"{name}_missing"] = 0.0
                quality["linkage_component_present"] += 1

    regime = _normalised_score(candidate.get("market_regime_score"), maximum=100.0)
    if regime is not None:
        quality["regime_present"] += 1
    context["regime"] = _regime_bucket(candidate.get("market_regime_score"))
    return context, quality


def build_ablation_context_rows(
    dataset: Mapping[str, Any],
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    """Replay candidate source files and extract only approved research fields."""

    validate_historical_research_dataset(dataset)
    contexts: dict[tuple[str, str], dict[str, Any]] = {}
    totals = {
        "candidate_rows": 0,
        "candidate_dates": set(),
        "as_of_matches": 0,
        "direction_present_rows": 0,
        "direction_invalid_rows": 0,
        "linkage_present_rows": 0,
        "linkage_score_present_rows": 0,
        "linkage_component_present_values": 0,
        "linkage_component_invalid_values": 0,
        "regime_present_rows": 0,
    }
    component_denominator = 0
    for entry in dataset["source_manifest"]["candidate_sources"]:
        path = Path(str(entry["path"]))
        payload, source_sha = load_strict_json_with_sha256(path)
        if source_sha != entry.get("sha256"):
            raise ValueError("historical ablation candidate source SHA mismatch")
        day = str(entry.get("as_of_date") or "")
        if payload.get("as_of") != day:
            raise ValueError("historical ablation candidate as-of mismatch")
        candidates = payload.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError("historical ablation candidate rows are missing")
        totals["candidate_dates"].add(day)
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                raise ValueError("historical ablation candidate must be an object")
            identity = _identity(day, candidate.get("code"))
            if identity in contexts:
                raise ValueError(f"duplicate historical ablation identity: {identity}")
            context, quality = _extract_context(candidate)
            contexts[identity] = context
            totals["candidate_rows"] += 1
            totals["as_of_matches"] += int(payload.get("as_of") == day)
            totals["direction_present_rows"] += quality["direction_present"]
            totals["direction_invalid_rows"] += quality["direction_invalid"]
            totals["linkage_present_rows"] += quality["linkage_present"]
            totals["linkage_score_present_rows"] += quality["linkage_score_present"]
            totals["linkage_component_present_values"] += quality[
                "linkage_component_present"
            ]
            totals["linkage_component_invalid_values"] += quality[
                "linkage_component_invalid"
            ]
            totals["regime_present_rows"] += quality["regime_present"]
            component_denominator += len(LINKAGE_COMPONENTS)
    rows = totals["candidate_rows"]
    coverage = {
        "candidate_rows": rows,
        "candidate_dates": len(totals["candidate_dates"]),
        "as_of_match_rows": totals["as_of_matches"],
        "direction": {
            "field_candidates": [
                "sector_direction_score",
                "direction_score_shadow",
            ],
            "present_rows": totals["direction_present_rows"],
            "present_date_count": len(
                {day for (day, _code), value in contexts.items() if not value["direction_score_missing"]}
            ),
            "invalid_rows": totals["direction_invalid_rows"],
            "coverage_ratio": totals["direction_present_rows"] / rows if rows else 0.0,
            "pit_status": "historical_reconstruction_not_prospective",
        },
        "linkage_v2": {
            "field_candidates": [
                "linkage_v2_shadow",
                "linkage_v2",
                "linkage_v2_breakdown",
            ],
            "present_rows": totals["linkage_present_rows"],
            "score_present_rows": totals["linkage_score_present_rows"],
            "component_present_values": totals["linkage_component_present_values"],
            "component_invalid_values": totals["linkage_component_invalid_values"],
            "component_value_count": component_denominator,
            "coverage_ratio": (
                totals["linkage_component_present_values"] / component_denominator
                if component_denominator
                else 0.0
            ),
            "pit_status": "historical_reconstruction_not_prospective",
        },
        "regime_slice": {
            "source_field": "market_regime_score",
            "present_rows": totals["regime_present_rows"],
            "coverage_ratio": totals["regime_present_rows"] / rows if rows else 0.0,
            "bucket_policy": {
                "risk_off": "score < 45",
                "neutral": "45 <= score < 60",
                "risk_on": "score >= 60",
                "unknown": "missing or invalid",
            },
        },
        "source_identity": {
            "candidate_source_count": len(dataset["source_manifest"]["candidate_sources"]),
            "calendar_sha256": dataset["source_manifest"]["calendar"]["sha256"],
            "source_rebuild_bound": True,
        },
    }
    return contexts, coverage


def _features(row: Mapping[str, Any], context: Mapping[str, Any], group: str) -> dict[str, float]:
    values = {name: float(row["features"][name]) for name in BASE_FEATURE_NAMES}
    for name in FEATURE_GROUPS[group][len(BASE_FEATURE_NAMES):]:
        values[name] = float(context.get(name, 0.0))
    if group == "D_direction_linkage_interaction":
        direction = float(context["direction_score"])
        direction_missing = bool(context["direction_score_missing"])
        for component, name in LINKAGE_COMPONENTS:
            linkage_value = float(context[name])
            missing = direction_missing or bool(context[f"{name}_missing"])
            values[f"direction_x_{name}"] = (
                direction * linkage_value if not missing else 0.0
            )
            values[f"direction_x_{name}_missing"] = float(missing)
        linkage_missing = bool(context["linkage_score_missing"])
        values["direction_x_linkage_score"] = (
            direction * float(context["linkage_score"])
            if not direction_missing and not linkage_missing
            else 0.0
        )
        values["direction_x_linkage_score_missing"] = float(
            direction_missing or linkage_missing
        )
    if tuple(values) != FEATURE_GROUPS[group]:
        raise ValueError(f"historical ablation feature order mismatch: {group}")
    require_finite(values, context=f"historical ablation features {group}")
    return values


def build_ablation_views(
    dataset: Mapping[str, Any],
    contexts: Mapping[tuple[str, str], Mapping[str, Any]],
    group: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if group not in FEATURE_GROUPS:
        raise ValueError(f"unknown historical ablation group: {group}")
    records = []
    universe = []
    for source, target in (
        (dataset["records"], records),
        (dataset["feature_universe_records"], universe),
    ):
        for row in source:
            identity = _identity(row["as_of_date"], row["stock_code"])
            context = contexts.get(identity)
            if context is None:
                raise ValueError(f"historical ablation source identity missing: {identity}")
            target.append(
                {
                    **dict(row),
                    "features": _features(row, context, group),
                    "regime": context["regime"],
                }
            )
    return records, universe


def _average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    result = [0.0] * len(values)
    cursor = 0
    while cursor < len(order):
        end = cursor + 1
        while end < len(order) and values[order[end]] == values[order[cursor]]:
            end += 1
        rank = (cursor + 1 + end) / 2.0
        for index in range(cursor, end):
            result[order[index]] = rank
        cursor = end
    return result


def _rank_ic(scores: Sequence[float], labels: Sequence[float]) -> float:
    if len(scores) < 2 or len(scores) != len(labels):
        return 0.0
    left = _average_ranks(scores)
    right = _average_ranks(labels)
    lm = mean(left)
    rm = mean(right)
    numerator = sum((a - lm) * (b - rm) for a, b in zip(left, right))
    denominator = math.sqrt(
        sum((a - lm) ** 2 for a in left) * sum((b - rm) ** 2 for b in right)
    )
    return numerator / denominator if denominator else 0.0


def _summary(rows: Sequence[Mapping[str, Any]], top_k: int) -> dict[str, Any]:
    if not rows:
        return {
            "date_count": 0,
            "row_count": 0,
            "universe_mean_return": None,
            "top_k_mean_return": None,
            "lift_vs_universe": None,
            "win_rate_vs_universe": None,
            "positive_date_rate": None,
            "mean_rank_ic": None,
        }
    lifts = [float(row["lift_vs_universe"]) for row in rows]
    return {
        "date_count": len(rows),
        "row_count": sum(int(row["row_count"]) for row in rows),
        "universe_mean_return": mean(float(row["universe_mean_return"]) for row in rows),
        "top_k_mean_return": mean(float(row["top_k_mean_return"]) for row in rows),
        "lift_vs_universe": mean(lifts),
        "win_rate_vs_universe": mean(float(row["win_vs_universe"]) for row in rows),
        "positive_date_rate": mean(
            float(float(row["top_k_mean_return"]) > 0) for row in rows
        ),
        "mean_rank_ic": mean(float(row["rank_ic"]) for row in rows),
        "lift_std": pstdev(lifts) if len(lifts) > 1 else 0.0,
        "lift_min": min(lifts),
        "lift_max": max(lifts),
    }


def evaluate_ablation_predictions(
    dataset: Mapping[str, Any],
    prediction_report: Mapping[str, Any],
    contexts: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    top_ks: Sequence[int] = (1, 3, 5),
) -> dict[str, Any]:
    labels = {
        _identity(row["as_of_date"], row["stock_code"]): float(row["training_label"])
        for row in dataset["records"]
    }
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in prediction_report.get("predictions") or []:
        identity = _identity(row.get("as_of_date"), row.get("stock_code"))
        label = labels.get(identity)
        score = _finite(row.get("ml_quant_score_shadow"))
        if label is None or score is None:
            continue
        by_date[identity[0]].append(
            {
                "stock_code": identity[1],
                "score": score,
                "label": label,
                "fold": int(row.get("fold") or 0),
                "regime": str(contexts[identity]["regime"]),
            }
        )
    def daily_rows(
        rows_by_date: Mapping[str, Sequence[Mapping[str, Any]]], top_k: int
    ) -> list[dict[str, Any]]:
        daily = []
        for day, rows in sorted(rows_by_date.items()):
            if len(rows) < 2:
                continue
            ordered = sorted(rows, key=lambda row: (-row["score"], row["stock_code"]))
            selected = ordered[: min(top_k, len(ordered))]
            universe = mean(row["label"] for row in rows)
            selected_mean = mean(row["label"] for row in selected)
            daily.append(
                {
                    "as_of_date": day,
                    "fold": rows[0]["fold"],
                    "row_count": len(rows),
                    "top_k": min(top_k, len(rows)),
                    "universe_mean_return": universe,
                    "top_k_mean_return": selected_mean,
                    "lift_vs_universe": selected_mean - universe,
                    "win_vs_universe": selected_mean > universe,
                    "rank_ic": _rank_ic(
                        [row["score"] for row in rows],
                        [row["label"] for row in rows],
                    ),
                }
            )
        return daily

    daily_by_k: dict[str, list[dict[str, Any]]] = {
        str(top_k): daily_rows(by_date, top_k) for top_k in top_ks
    }

    fold_stability: dict[str, dict[str, Any]] = {}
    regime_slices: dict[str, dict[str, Any]] = {}
    for top_k in top_ks:
        daily = daily_by_k[str(top_k)]
        fold_stability[str(top_k)] = {
            str(fold): _summary(
                [row for row in daily if row["fold"] == fold], top_k
            )
            for fold in sorted({row["fold"] for row in daily})
        }
        regime_slices[str(top_k)] = {
            regime: _summary(
                daily_rows(
                    {
                        day: [row for row in rows if row["regime"] == regime]
                        for day, rows in by_date.items()
                    },
                    top_k,
                ),
                top_k,
            )
            for regime in REGIME_BUCKETS
        }
    return {
        "metrics": {
            str(top_k): _summary(daily_by_k[str(top_k)], top_k)
            for top_k in top_ks
        },
        "daily_metrics": daily_by_k,
        "fold_stability": fold_stability,
        "regime_slices": regime_slices,
    }


def run_historical_factor_ablation(
    dataset: Mapping[str, Any],
    *,
    min_train_dates: int = 60,
    test_dates: int = 5,
    purge_dates: int = 5,
    max_label_horizon: int = 5,
    n_estimators: int = 80,
    top_ks: Sequence[int] = (1, 3, 5),
) -> dict[str, Any]:
    """Run A/B/C/D with one fixed expanding walk-forward contract."""

    if any(
        value <= 0
        for value in (min_train_dates, test_dates, purge_dates, max_label_horizon, n_estimators)
    ):
        raise ValueError("historical ablation numeric parameters must be positive")
    if purge_dates < max_label_horizon:
        raise ValueError("historical ablation purge must cover label horizon")
    validate_historical_research_dataset(dataset)
    contexts, coverage = build_ablation_context_rows(dataset)
    groups: dict[str, Any] = {}
    for group, feature_names in FEATURE_GROUPS.items():
        records, universe = build_ablation_views(dataset, contexts, group)
        prediction = walk_forward_ranker_predictions(
            records,
            prediction_universe_records=universe,
            feature_names=feature_names,
            min_train_dates=min_train_dates,
            test_dates=test_dates,
            purge_dates=purge_dates,
            max_label_horizon=max_label_horizon,
            n_estimators=n_estimators,
        )
        if prediction.get("status") != "ok":
            raise ValueError(f"historical ablation group unavailable: {group}")
        prediction = {
            **prediction,
            "schema_version": f"{ABLATION_SCHEMA_VERSION}-predictions",
            "ablation_group": group,
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
        groups[group] = {
            "feature_names": list(feature_names),
            "prediction": prediction,
            **metrics,
        }
    baseline = groups["A_technical_baseline"]["metrics"]
    for group, result in groups.items():
        result["delta_vs_A"] = {
            key: {
                metric: (
                    result["metrics"][key].get(metric) - baseline[key].get(metric)
                    if isinstance(result["metrics"][key].get(metric), (int, float))
                    and isinstance(baseline[key].get(metric), (int, float))
                    else None
                )
                for metric in ("lift_vs_universe", "mean_rank_ic", "win_rate_vs_universe")
            }
            for key in baseline
        }
    report = {
        "schema_version": ABLATION_SCHEMA_VERSION,
        "mode": MODE,
        "status": "research_only",
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "dataset_sha256": dataset["dataset_sha256"],
        "experiment": {
            "split_type": "expanding_date_grouped_walk_forward",
            "min_train_dates": min_train_dates,
            "test_dates": test_dates,
            "purge_dates": purge_dates,
            "max_label_horizon": max_label_horizon,
            "n_estimators": n_estimators,
            "top_ks": list(top_ks),
            "same_contract_for_all_groups": True,
        },
        "feature_contract": {
            "base_features": list(BASE_FEATURE_NAMES),
            "direction_features": list(DIRECTION_FEATURE_NAMES),
            "linkage_features": list(LINKAGE_FEATURE_NAMES),
            "interaction_features": list(INTERACTION_FEATURE_NAMES),
            "missing_values": "raw values are zero only when paired missing indicator is 1",
            "forbidden_feature_count": 0,
        },
        "source_coverage": coverage,
        "groups": groups,
        "strict_pit_eligible": False,
        "pit_evidence_status": "historical_reconstruction_not_prospective",
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "formal_loader_policy": "No formal model bundle is emitted; any historical schema is rejected by the formal loader.",
        "limitations": [
            "Direction and Linkage V2 fields have zero coverage in the 99-day candidate archive.",
            "Regime slicing uses market_regime_score only for reporting, never as a model feature.",
            "Historical source bars remain non-PIT and are not promotion evidence.",
        ],
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(report, context="historical factor ablation")
    return report


def validate_historical_factor_ablation_report(report: Mapping[str, Any]) -> None:
    if (
        report.get("schema_version") != ABLATION_SCHEMA_VERSION
        or report.get("mode") != MODE
        or report.get("status") != "research_only"
        or report.get("dataset_classification") != HISTORICAL_DATASET_CLASSIFICATION
    ):
        raise ValueError("historical factor ablation contract mismatch")
    for key in (
        "strict_pit_eligible",
        "eligible_for_oos_claim",
        "promotion_allowed",
        "live_trading_allowed",
        "formal_predictor_compatible",
    ):
        if report.get(key) is not False:
            raise ValueError(f"historical factor ablation safety flag mismatch: {key}")
    for names in FEATURE_GROUPS.values():
        if any(name not in ALL_ABLATION_FEATURE_NAMES for name in names):
            raise ValueError("historical factor ablation feature contract drift")
    validate_no_executable_instructions(report, context="historical factor ablation")
