"""Same-day paired evaluation of rule and ML shadow rankings."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import math
from statistics import mean, pstdev
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)

from .contract import canonical_sha256, require_finite
from .schema import DISCLAIMER, MODE


def _identity(row: Mapping[str, Any]) -> tuple[str, str]:
    return str(row.get("as_of_date") or ""), str(row.get("stock_code") or "").zfill(6)


def _unique_index(
    rows: Sequence[Mapping[str, Any]], *, context: str
) -> dict[tuple[str, str], Mapping[str, Any]]:
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        identity = _identity(row)
        if not identity[0] or len(identity[1]) != 6:
            raise ValueError(f"invalid {context} identity")
        if identity in result:
            raise ValueError(f"duplicate {context} identity: {identity}")
        result[identity] = row
    return result


def _average_ranks(values: Sequence[float]) -> list[float]:
    ordered = sorted(range(len(values)), key=lambda index: (values[index], index))
    ranks = [0.0] * len(values)
    cursor = 0
    while cursor < len(ordered):
        end = cursor + 1
        while end < len(ordered) and values[ordered[end]] == values[ordered[cursor]]:
            end += 1
        average_rank = (cursor + 1 + end) / 2.0
        for offset in range(cursor, end):
            ranks[ordered[offset]] = average_rank
        cursor = end
    return ranks


def _spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    if len(x) < 2 or len(x) != len(y):
        return None
    rx = _average_ranks(x)
    ry = _average_ranks(y)
    mx = mean(rx)
    my = mean(ry)
    numerator = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    denominator = math.sqrt(
        sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)
    )
    return numerator / denominator if denominator > 0 else None


def _max_drawdown(daily_returns: Sequence[float]) -> float | None:
    if not daily_returns:
        return None
    wealth = 1.0
    peak = 1.0
    worst = 0.0
    for value in daily_returns:
        wealth *= 1.0 + value
        peak = max(peak, wealth)
        worst = min(worst, wealth / peak - 1.0)
    return abs(worst)


def _selection_metrics(
    *,
    selected_by_date: Mapping[str, Sequence[tuple[str, str]]],
    labels: Mapping[tuple[str, str], Mapping[str, Any]],
    score_by_id: Mapping[tuple[str, str], float],
    eligible_by_date: Mapping[str, Sequence[tuple[str, str]]],
    sector_by_id: Mapping[tuple[str, str], str],
    horizon: int,
    top_k: int,
) -> dict[str, Any]:
    raw_key = f"future_return_{horizon}d"
    excess_key = f"future_excess_return_{horizon}d"
    raw_values: list[float] = []
    excess_values: list[float] = []
    daily_means: list[tuple[str, float]] = []
    sectors: Counter[str] = Counter()
    selected_total = 0
    labeled_total = 0
    for day in sorted(selected_by_date):
        identities = list(selected_by_date[day])
        daily_raw: list[float] = []
        for identity in identities:
            sectors[sector_by_id.get(identity, "")] += 1
            label_row = labels.get(identity)
            if label_row is None:
                continue
            label_values = label_row.get("labels") or {}
            if label_values.get(raw_key) is None or label_values.get(excess_key) is None:
                continue
            raw = float(label_values[raw_key])
            excess = float(label_values[excess_key])
            if not math.isfinite(raw) or not math.isfinite(excess):
                raise ValueError("evaluation labels contain non-finite values")
            labeled_total += 1
            raw_values.append(raw)
            excess_values.append(excess)
            daily_raw.append(raw)
        selected_total += len(identities)
        if daily_raw:
            daily_means.append((day, mean(daily_raw)))

    turnovers: list[float] = []
    prior: set[str] | None = None
    for day in sorted(selected_by_date):
        current = {identity[1] for identity in selected_by_date[day]}
        if prior is not None:
            denominator = max(len(prior), len(current), 1)
            turnovers.append(1.0 - len(prior & current) / denominator)
        prior = current

    daily_ics: list[float] = []
    for day in sorted(eligible_by_date):
        identities = [
            identity
            for identity in eligible_by_date[day]
            if identity in score_by_id
            and identity in labels
            and (labels[identity].get("labels") or {}).get(excess_key) is not None
        ]
        scores = [score_by_id[identity] for identity in identities]
        outcomes = [float((labels[identity].get("labels") or {})[excess_key]) for identity in identities]
        value = _spearman(scores, outcomes)
        if value is not None:
            daily_ics.append(value)
    expected = top_k * len(selected_by_date)
    concentration = max(sectors.values()) / selected_total if selected_total else None
    worst = min(daily_means, key=lambda item: item[1]) if daily_means else None
    return {
        "mean_return": mean(raw_values) if raw_values else None,
        "mean_excess_return": mean(excess_values) if excess_values else None,
        "win_rate": sum(value > 0 for value in raw_values) / len(raw_values) if raw_values else None,
        "spearman_ic": mean(daily_ics) if daily_ics else None,
        "max_drawdown": (
            _max_drawdown([value for _day, value in daily_means])
            if horizon == 1
            else None
        ),
        "worst_date": worst[0] if worst else None,
        "worst_date_return": worst[1] if worst else None,
        "turnover": mean(turnovers) if turnovers else None,
        "sector_concentration": concentration,
        "coverage_ratio": labeled_total / selected_total if selected_total else 0.0,
        "selection_fill_ratio": selected_total / expected if expected else 0.0,
        "selected_row_count": selected_total,
        "labeled_row_count": labeled_total,
        "evaluated_date_count": len(daily_means),
    }


def _same_day_percentiles(
    identities_by_date: Mapping[str, Sequence[tuple[str, str]]],
    values: Mapping[tuple[str, str], float | None],
) -> dict[tuple[str, str], float]:
    result: dict[tuple[str, str], float] = {}
    for day, identities in identities_by_date.items():
        available = [identity for identity in identities if values.get(identity) is not None]
        ranked = sorted(
            available,
            key=lambda identity: (-float(values[identity]), identity[1]),
        )
        count = len(ranked)
        for rank, identity in enumerate(ranked, start=1):
            result[identity] = 100.0 if count == 1 else (count - rank) / (count - 1) * 100.0
    return result


def _prediction_drift(
    predictions: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    by_date: dict[str, list[float]] = defaultdict(list)
    for identity, row in predictions.items():
        if row.get("prediction") is None:
            return {
                "status": "unavailable",
                "reason": "raw_prediction_not_supplied",
            }
        value = float(row["prediction"])
        if math.isfinite(value):
            by_date[identity[0]].append(value)
    dates = sorted(by_date)
    if len(dates) < 2:
        return {"status": "unavailable", "reason": "fewer_than_two_prediction_dates"}
    midpoint = max(1, len(dates) // 2)
    reference_dates = dates[:midpoint]
    latest_dates = dates[midpoint:]
    reference = [value for day in reference_dates for value in by_date[day]]
    latest = [value for day in latest_dates for value in by_date[day]]
    if not latest:
        return {"status": "unavailable", "reason": "prediction_drift_partition_empty"}

    def quantile(values: Sequence[float], probability: float) -> float:
        ordered = sorted(values)
        position = (len(ordered) - 1) * probability
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    reference_mean = mean(reference)
    latest_mean = mean(latest)
    reference_std = pstdev(reference) if len(reference) >= 2 else 0.0
    latest_std = pstdev(latest) if len(latest) >= 2 else 0.0
    reference_iqr = quantile(reference, 0.75) - quantile(reference, 0.25)
    latest_iqr = quantile(latest, 0.75) - quantile(latest, 0.25)
    return {
        "status": "ok",
        "method": "raw_prediction_distribution_shift",
        "reference_start": reference_dates[0],
        "reference_end": reference_dates[-1],
        "latest_start": latest_dates[0],
        "latest_end": latest_dates[-1],
        "reference_mean": reference_mean,
        "latest_mean": latest_mean,
        "mean_shift": latest_mean - reference_mean,
        "reference_std": reference_std,
        "latest_std": latest_std,
        "std_shift": latest_std - reference_std,
        "reference_iqr": reference_iqr,
        "latest_iqr": latest_iqr,
        "iqr_shift": latest_iqr - reference_iqr,
        "date_count": len(dates),
        "row_count": sum(len(values) for values in by_date.values()),
    }


def _feature_drift(dataset: Mapping[str, Any]) -> dict[str, Any]:
    rows = dataset.get("records")
    if not isinstance(rows, list):
        return {"status": "unavailable", "reason": "feature_reference_not_supplied"}
    by_date: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if isinstance(row, Mapping) and isinstance(row.get("features"), Mapping):
            by_date[str(row.get("as_of_date") or "")].append(row)
    dates = sorted(day for day in by_date if day)
    if len(dates) < 2:
        return {"status": "unavailable", "reason": "fewer_than_two_feature_dates"}
    midpoint = max(1, len(dates) // 2)
    reference = [row for day in dates[:midpoint] for row in by_date[day]]
    latest = [row for day in dates[midpoint:] for row in by_date[day]]
    if not reference or not latest:
        return {"status": "unavailable", "reason": "feature_reference_partition_empty"}
    names = tuple(reference[0]["features"].keys())
    shifts: dict[str, float] = {}
    for name in names:
        left = [float(row["features"][name]) for row in reference]
        right = [float(row["features"][name]) for row in latest]
        left_mean = mean(left)
        right_mean = mean(right)
        scale = math.sqrt(mean([(value - left_mean) ** 2 for value in left]))
        shifts[name] = (right_mean - left_mean) / max(scale, 1e-12)
    return {
        "status": "ok",
        "reference_date_count": midpoint,
        "latest_date_count": len(dates) - midpoint,
        "max_abs_standardized_mean_shift": max(abs(value) for value in shifts.values()),
        "feature_shifts": shifts,
        "drifted_feature_count": sum(abs(value) >= 1.0 for value in shifts.values()),
    }


def evaluate_rule_vs_ml_shadow(
    prediction_report: Mapping[str, Any],
    dataset: Mapping[str, Any],
    rule_rows: Sequence[Mapping[str, Any]],
    *,
    top_ks: tuple[int, ...] = (10, 20, 30),
    horizons: tuple[int, ...] = (1, 3, 5),
    rule_score_field: str = "rule_score",
    feature_drift_report: Mapping[str, Any] | None = None,
    baseline_strict_pit_eligible: bool | None = None,
    hybrid_quant_weight: float = 0.65,
    hybrid_linkage_weight: float = 0.35,
    hybrid_partial_linkage_weight: float = 0.20,
) -> dict[str, Any]:
    """Evaluate independent rule/Linkage/Hybrid/ML rankings on paired identities."""

    if prediction_report.get("status") != "ok":
        raise ValueError("ML prediction report is not available")
    if dataset.get("strict_pit_eligible") is True:
        from .dataset import validate_training_dataset

        validate_training_dataset(dataset)
    fixture_only = bool(prediction_report.get("fixture_only", False))
    if fixture_only != bool(dataset.get("fixture_only", False)):
        raise ValueError("prediction and dataset fixture identity mismatch")
    predictions = _unique_index(
        list(prediction_report.get("predictions") or []), context="prediction"
    )
    label_rows = dataset.get("evaluation_label_records")
    if not isinstance(label_rows, list):
        label_rows = dataset.get("records") or []
    labels = _unique_index(list(label_rows), context="dataset")
    rules = _unique_index(rule_rows, context="rule")
    split = prediction_report.get("split")
    folds = split.get("folds") if isinstance(split, Mapping) else None
    if isinstance(folds, list) and folds:
        expected_prediction_rows = sum(int(row.get("test_row_count") or 0) for row in folds)
        if len(predictions) != expected_prediction_rows:
            raise ValueError("prediction universe does not match the walk-forward fold audit")
    if dataset.get("strict_pit_eligible") is True:
        source_manifest = dataset.get("source_manifest")
        archive_root = (
            source_manifest.get("archive_root")
            if isinstance(source_manifest, Mapping)
            else None
        )
        if not archive_root:
            raise ValueError("strict dataset archive root is unavailable")
        from .accumulation import load_verified_training_inputs

        verified = load_verified_training_inputs(archive_root)
        if canonical_sha256(list(rule_rows)) != canonical_sha256(
            verified["baseline_rows"]
        ):
            raise ValueError("rule rows do not match the verified archive baseline")
        prediction_rows = list(prediction_report.get("predictions") or [])
        if (
            prediction_report.get("strict_pit_eligible") is not True
            or prediction_report.get("dataset_sha256")
            != dataset.get("dataset_sha256")
            or prediction_report.get("prediction_rows_sha256")
            != canonical_sha256(prediction_rows)
        ):
            raise ValueError("strict prediction report is not bound to the dataset")
        if not isinstance(folds, list) or not folds:
            raise ValueError("strict prediction split audit is missing")
        feature_universe = list(dataset.get("feature_universe_records") or [])
        feature_dates = sorted(
            {str(row.get("as_of_date") or "") for row in feature_universe}
        )
        expected_test_dates: set[str] = set()
        for fold in folds:
            if not isinstance(fold, Mapping):
                raise ValueError("strict prediction fold audit is invalid")
            start = str(fold.get("test_start") or "")
            end = str(fold.get("test_end") or "")
            fold_dates = [day for day in feature_dates if start <= day <= end]
            if len(fold_dates) != int(fold.get("test_date_count") or 0):
                raise ValueError("strict prediction fold test dates do not reproduce")
            expected_test_dates.update(fold_dates)
        expected_universe_rows = [
            row
            for row in feature_universe
            if str(row.get("as_of_date") or "") in expected_test_dates
        ]
        if set(predictions) != {_identity(row) for row in expected_universe_rows}:
            raise ValueError("strict prediction universe does not match the dataset")
        if prediction_report.get("prediction_universe_sha256") != canonical_sha256(
            expected_universe_rows
        ):
            raise ValueError("strict prediction universe SHA mismatch")
        feature_sectors = {
            _identity(row): str(row.get("sector_name") or "")
            for row in expected_universe_rows
        }
        if any(
            str(row.get("sector_name") or "") != feature_sectors[identity]
            for identity, row in predictions.items()
        ):
            raise ValueError("strict prediction sector identity mismatch")
        if baseline_strict_pit_eligible is not True:
            raise ValueError("strict evaluation baseline evidence is missing")
    universe = sorted(predictions.keys() & rules.keys())
    if not universe:
        raise ValueError("no same-day paired rule/ML identities")
    by_date: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for identity in universe:
        by_date[identity[0]].append(identity)
    for identities in by_date.values():
        identities.sort(key=lambda identity: identity[1])

    ml_scores = {
        identity: float(predictions[identity]["ml_quant_score_shadow"])
        for identity in universe
    }
    sector_by_id = {
        identity: str(predictions[identity].get("sector_name") or "")
        for identity in universe
    }
    require_finite(ml_scores, context="ML evaluation scores")
    multi_baseline = any(
        "quant_baseline_score_shadow" in rules[identity] for identity in universe
    )
    baseline_configuration: dict[str, Any] | None = None
    ranking_audit: list[dict[str, Any]] = []
    if multi_baseline:
        if any(
            "quant_baseline_score_shadow" not in rules[identity]
            or "linkage_v2_status" not in rules[identity]
            for identity in universe
        ):
            raise ValueError("multi-baseline rows must contain Quant and Linkage V2 fields")
        if (
            hybrid_quant_weight < 0
            or hybrid_linkage_weight < 0
            or hybrid_partial_linkage_weight < 0
            or hybrid_quant_weight + hybrid_linkage_weight <= 0
            or hybrid_partial_linkage_weight > 1
        ):
            raise ValueError("Hybrid weights are invalid")
        quant_raw = {
            identity: float(rules[identity]["quant_baseline_score_shadow"])
            for identity in universe
        }
        linkage_raw: dict[tuple[str, str], float | None] = {}
        linkage_status: dict[tuple[str, str], str] = {}
        for identity in universe:
            status = str(rules[identity].get("linkage_v2_status") or "")
            if status not in {"ok", "partial", "unavailable"}:
                raise ValueError("Linkage V2 baseline status is invalid")
            linkage_status[identity] = status
            value = rules[identity].get("linkage_v2_baseline_score_shadow")
            linkage_raw[identity] = None if value is None else float(value)
            if status == "unavailable" and value is not None:
                raise ValueError("unavailable Linkage V2 baseline must not have a score")
            if status != "unavailable" and value is None:
                raise ValueError("available Linkage V2 baseline must have a score")
        require_finite(quant_raw, context="Quant baseline scores")
        require_finite(linkage_raw, context="Linkage V2 baseline scores")
        quant_scores = _same_day_percentiles(by_date, quant_raw)
        linkage_scores = _same_day_percentiles(by_date, linkage_raw)
        for identity in universe:
            if linkage_status[identity] == "unavailable":
                linkage_scores[identity] = -1.0
        hybrid_scores: dict[tuple[str, str], float] = {}
        hybrid_rows: dict[tuple[str, str], dict[str, Any]] = {}
        for identity in universe:
            status = linkage_status[identity]
            q_score = quant_scores[identity]
            if status == "ok":
                q_weight = hybrid_quant_weight / (hybrid_quant_weight + hybrid_linkage_weight)
                l_weight = hybrid_linkage_weight / (hybrid_quant_weight + hybrid_linkage_weight)
                confidence = "high"
                reason = None
                score = q_score * q_weight + float(linkage_scores[identity]) * l_weight
            elif status == "partial":
                l_weight = hybrid_partial_linkage_weight
                q_weight = 1.0 - l_weight
                confidence = "medium"
                reason = "linkage_v2_partial_weight_reduced"
                score = q_score * q_weight + float(linkage_scores[identity]) * l_weight
            else:
                q_weight = 1.0
                l_weight = 0.0
                confidence = "low"
                reason = "linkage_v2_unavailable_quant_only"
                score = q_score
            hybrid_scores[identity] = round(score, 6)
            hybrid_rows[identity] = {
                "score": round(score, 6),
                "confidence": confidence,
                "effective_quant_weight": q_weight,
                "effective_linkage_weight": l_weight,
                "degradation_reason": reason,
            }
        baseline_eligible = {
            identity
            for identity in universe
            if bool(rules[identity].get("rule_eligible", True))
        }
        score_maps = {
            "A_quant": quant_scores,
            "B_linkage_v2": linkage_scores,
            "C_hybrid": hybrid_scores,
            "D_ml": ml_scores,
        }
        common_eligible = {
            day: [identity for identity in identities if identity in baseline_eligible]
            for day, identities in by_date.items()
        }
        eligible_maps = {
            strategy: {day: list(identities) for day, identities in common_eligible.items()}
            for strategy in score_maps
        }
        baseline_configuration = {
            "hybrid": {
                "quant_weight": float(hybrid_quant_weight),
                "linkage_v2_weight": float(hybrid_linkage_weight),
                "partial_linkage_v2_weight": float(hybrid_partial_linkage_weight),
                "method": "same_day_percentile_weighted",
            },
            "linkage_unavailable_policy": "fail_closed_lowest_rank_common_pool_and_quant_only_hybrid",
        }
    else:
        rule_scores = {
            identity: float(rules[identity][rule_score_field]) for identity in universe
        }
        require_finite(rule_scores, context="rule evaluation scores")
        rule_eligible = {
            identity
            for identity in universe
            if bool(rules[identity].get("rule_eligible", True))
        }
        score_maps = {
            "A_rule": rule_scores,
            "B_ml": ml_scores,
            "C_rule_gate_ml_rank": ml_scores,
            "D_consensus": rule_scores,
        }
        eligible_maps = {}

    results: list[dict[str, Any]] = []
    for top_k in sorted(set(int(value) for value in top_ks)):
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        selected: dict[str, dict[str, list[tuple[str, str]]]] = {
            strategy: {} for strategy in score_maps
        }
        eligible: dict[str, dict[str, list[tuple[str, str]]]] = {
            strategy: {} for strategy in score_maps
        }
        for strategy, score_map in score_maps.items():
            for day, identities in sorted(by_date.items()):
                candidates = list(eligible_maps[strategy].get(day, identities)) if multi_baseline else list(identities)
                ranked = sorted(
                    [identity for identity in candidates if identity in score_map],
                    key=lambda item: (-float(score_map[item]), item[1]),
                )
                selected[strategy][day] = ranked[:top_k]
                eligible[strategy][day] = candidates
        if not multi_baseline:
            for day, identities in sorted(by_date.items()):
                rule_ranked = sorted(identities, key=lambda item: (-score_maps["A_rule"][item], item[1]))
                ml_ranked = sorted(identities, key=lambda item: (-ml_scores[item], item[1]))
                gated = [identity for identity in ml_ranked if identity in rule_eligible]
                selected["A_rule"][day] = rule_ranked[:top_k]
                selected["B_ml"][day] = ml_ranked[:top_k]
                selected["C_rule_gate_ml_rank"][day] = gated[:top_k]
                selected["D_consensus"][day] = [
                    identity for identity in rule_ranked[:top_k]
                    if identity in set(ml_ranked[:top_k])
                ]
                eligible["A_rule"][day] = identities
                eligible["B_ml"][day] = identities
                eligible["C_rule_gate_ml_rank"][day] = [
                    identity for identity in identities if identity in rule_eligible
                ]
                eligible["D_consensus"][day] = identities
        if multi_baseline:
            for day in sorted(by_date):
                ranking_audit.append(
                    {
                        "as_of_date": day,
                        "top_k": top_k,
                        "selections": {
                            strategy: [identity[1] for identity in selected[strategy][day]]
                            for strategy in selected
                        },
                        "hybrid_rows": {
                            identity[1]: hybrid_rows[identity]
                            for identity in by_date[day]
                        },
                    }
                )
        for strategy in selected:
            score_map = score_maps[strategy]
            for horizon in sorted(set(int(value) for value in horizons)):
                metrics = _selection_metrics(
                    selected_by_date=selected[strategy],
                    labels=labels,
                    score_by_id=score_map,
                    eligible_by_date=eligible[strategy],
                    sector_by_id=sector_by_id,
                    horizon=horizon,
                    top_k=top_k,
                )
                results.append(
                    {
                        "strategy": strategy,
                        "top_k": top_k,
                        "horizon": horizon,
                        **metrics,
                    }
                )

    paired_date_count = len(by_date)
    label_coverage_by_horizon = {}
    for horizon in sorted(set(int(value) for value in horizons)):
        key = f"future_excess_return_{horizon}d"
        labeled = sum(
            identity in labels
            and (labels[identity].get("labels") or {}).get(key) is not None
            for identity in universe
        )
        label_coverage_by_horizon[f"{horizon}d"] = labeled / len(universe)
    label_coverage = label_coverage_by_horizon.get("5d", 0.0)
    strict_pit = bool(
        prediction_report.get("strict_pit_eligible") is True
        and dataset.get("strict_pit_eligible") is True
        and (
            baseline_strict_pit_eligible is True
            if baseline_strict_pit_eligible is not None
            else multi_baseline
        )
    )
    minimum_dates = paired_date_count >= 60
    coverage_gate = label_coverage >= 0.9
    # Stage 1 is architecture-only. Performance promotion remains impossible
    # until every pre-registered return/risk/stability gate is implemented.
    promotion_allowed = False
    promotion_gates = {
        "strict_pit_eligible": strict_pit,
        "minimum_60_paired_dates": minimum_dates,
        "minimum_90pct_label_coverage": coverage_gate,
        "pre_registered_3d_excess_gate": False,
        "pre_registered_5d_excess_gate": False,
        "win_rate_non_degradation_gate": False,
        "max_drawdown_non_degradation_gate": False,
        "turnover_max_10pct_degradation_gate": False,
        "walk_forward_fold_stability_gate": False,
        "cross_regime_stability_reviewed": False,
        "complete_performance_hard_gates": False,
    }
    report = {
        "schema_version": "ml-stock-rule-comparison-v1",
        "mode": MODE,
        "status": "ok",
        "fixture_only": fixture_only,
        "strict_pit_eligible": strict_pit,
        "eligible_for_oos_claim": False,
        "paired_date_count": paired_date_count,
        "prediction_rule_universe_row_count": len(universe),
        "paired_row_count": sum(
            identity in labels
            and (labels[identity].get("labels") or {}).get(
                "future_excess_return_5d"
            )
            is not None
            for identity in universe
        ),
        "label_coverage": label_coverage,
        "label_coverage_by_horizon": label_coverage_by_horizon,
        "results": results,
        "feature_drift": dict(
            feature_drift_report
            or (
                _feature_drift(dataset)
                if multi_baseline
                else {
                    "status": "unavailable",
                    "reason": "training_feature_reference_not_supplied",
                }
            )
        ),
        "prediction_drift": _prediction_drift(predictions),
        "market_regime_breakdown": {
            "status": "unavailable",
            "reason": "market_regime_labels_not_supplied",
        },
        "promotion_gates": promotion_gates,
        "promotion_status": "architecture_only_shadow",
        "promotion_allowed": promotion_allowed,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    if multi_baseline:
        status_counts = Counter(
            linkage_status[identity] for identity in universe
        )
        confidence_counts = Counter(
            hybrid_rows[identity]["confidence"] for identity in universe
        )
        report["baseline_configuration"] = baseline_configuration
        report["baseline_quality"] = {
            "row_count": len(universe),
            "linkage_status_counts": dict(status_counts),
            "hybrid_confidence_counts": dict(confidence_counts),
            "linkage_available_row_count": sum(
                status_counts.get(status, 0) for status in ("ok", "partial")
            ),
            "linkage_unavailable_policy": "fail_closed_lowest_rank_common_pool_quant_only_hybrid",
        }
        report["ranking_audit"] = ranking_audit
    require_finite(report, context="ML evaluation report")
    validate_no_executable_instructions(report, context="ML evaluation report")
    return report
