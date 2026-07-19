"""Historical paper/shadow comparison of formal and direction sector scores."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Sequence

from ..reporting.strict_json import write_strict_json_atomic, write_text_atomic


PAPER_MODE = "paper_shadow_research_only"
DEFAULT_TOP_KS = (3, 5, 8)
DEFAULT_DIRECTION_THRESHOLDS = (55.0, 60.0, 65.0)
DEFAULT_HORIZONS = (1, 3, 5, 10)
COMMON_DATA_QUALITY_FLOOR = 4.0
COMMON_ACCEPTED_RISK_LEVELS = frozenset({"low", "medium"})
FORMAL_ADMISSION_FRACTION = 0.25


def layer_comparison_preregistration(
    *,
    top_ks: Sequence[int] = DEFAULT_TOP_KS,
    direction_thresholds: Sequence[float] = DEFAULT_DIRECTION_THRESHOLDS,
    horizons: Sequence[int] = DEFAULT_HORIZONS,
) -> dict[str, Any]:
    """Return the frozen experiment definition without reading outcome labels."""
    normalized_top_ks = _positive_unique_ints(top_ks, field="top_ks")
    normalized_thresholds = _finite_unique_numbers(
        direction_thresholds, field="direction_thresholds"
    )
    normalized_horizons = _positive_unique_ints(horizons, field="horizons")
    definition = {
        "schema_version": "sector_radar_layer_comparison_preregistration.v1",
        "mode": PAPER_MODE,
        "broker_connection": False,
        "live_order_instruction_generated": False,
        "strict_pit_eligible": False,
        "definition": _preregistration(
            normalized_top_ks, normalized_thresholds, normalized_horizons
        ),
    }
    definition["preregistration_sha256"] = _canonical_sha256(definition)
    return definition


def compare_sector_radar_layers(
    dataset: dict[str, Any],
    *,
    top_ks: Sequence[int] = DEFAULT_TOP_KS,
    direction_thresholds: Sequence[float] = DEFAULT_DIRECTION_THRESHOLDS,
    horizons: Sequence[int] = DEFAULT_HORIZONS,
    cluster_map: dict[str, Sequence[str]] | None = None,
    cluster_map_sha256: str | None = None,
) -> dict[str, Any]:
    """Compare pre-registered A/B/C/D selection rules on a common PIT dataset."""
    normalized_top_ks = _positive_unique_ints(top_ks, field="top_ks")
    normalized_thresholds = _finite_unique_numbers(
        direction_thresholds, field="direction_thresholds"
    )
    normalized_horizons = _positive_unique_ints(horizons, field="horizons")
    preregistration_artifact = layer_comparison_preregistration(
        top_ks=normalized_top_ks,
        direction_thresholds=normalized_thresholds,
        horizons=normalized_horizons,
    )
    samples = dataset.get("samples")
    if not isinstance(samples, list):
        raise ValueError("dataset.samples must be a list")
    source_manifest = dataset.get("source_manifest")
    if not isinstance(source_manifest, dict):
        raise ValueError("dataset.source_manifest must be an object")
    source_documents = source_manifest.get("documents")
    if (
        not isinstance(source_documents, list)
        or _canonical_sha256(source_documents)
        != source_manifest.get("manifest_sha256")
    ):
        raise ValueError("source manifest SHA does not match source documents")
    provenance_audit = dataset.get("provenance_audit")
    if not isinstance(provenance_audit, dict):
        raise ValueError("dataset.provenance_audit must be an object")
    if _pit_sample_manifest_sha(samples) != provenance_audit.get(
        "sample_manifest_sha256"
    ):
        raise ValueError("sample manifest SHA does not match PIT samples")

    feature_eligible_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    feature_date_violations = 0
    label_date_violations = 0
    incomplete_label_rows = 0
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("dataset samples must be objects")
        if not _common_feature_eligible(sample):
            continue
        as_of_date = _iso_date(sample.get("as_of_date"), field="as_of_date")
        feature_max_date = _iso_date(
            sample.get("feature_max_date"), field="feature_max_date"
        )
        if feature_max_date > as_of_date:
            feature_date_violations += 1
            continue
        feature_eligible_by_date[as_of_date.isoformat()].append(sample)
        labels_complete = True
        for horizon in normalized_horizons:
            key = f"{horizon}d"
            return_value = _finite_or_none(
                (sample.get("forward_returns") or {}).get(key)
            )
            label_date_value = (sample.get("forward_label_dates") or {}).get(key)
            if return_value is None or label_date_value is None:
                labels_complete = False
                continue
            label_date = _iso_date(label_date_value, field=f"forward_label_dates.{key}")
            if label_date <= as_of_date:
                label_date_violations += 1
                labels_complete = False
        if not labels_complete:
            incomplete_label_rows += 1

    if feature_date_violations:
        raise ValueError("feature source date exceeds as_of_date")
    if label_date_violations:
        raise ValueError("forward label date must be after as_of_date")
    common_by_date = {
        as_of_date: sorted(rows, key=_sector_identity)
        for as_of_date, rows in sorted(feature_eligible_by_date.items())
        if len(rows) >= 2
    }
    if not common_by_date:
        raise ValueError("no common feature-eligible dates remain")

    normalized_cluster_map = _normalize_cluster_map(cluster_map or {})
    selections: dict[tuple[str, int, float | None], dict[str, list[dict[str, Any]]]] = {}
    score_domains: dict[
        tuple[str, int, float | None], dict[str, list[dict[str, Any]]]
    ] = {}
    formal_admission_counts: dict[tuple[str, int, float | None], int] = {}
    for top_k in normalized_top_ks:
        for group in ("A", "B", "C"):
            key = (group, top_k, None)
            group_selections: dict[str, list[dict[str, Any]]] = {}
            group_domains: dict[str, list[dict[str, Any]]] = {}
            admission_count = 0
            for as_of_date, rows in common_by_date.items():
                formal_ranked = _rank_rows(rows, _formal_score)
                direction_ranked = _rank_rows(rows, _direction_score)
                if group == "A":
                    domain = formal_ranked
                    selected = formal_ranked[:top_k]
                elif group == "B":
                    domain = direction_ranked
                    selected = direction_ranked[:top_k]
                else:
                    admission_size = max(
                        1, math.ceil(len(formal_ranked) * FORMAL_ADMISSION_FRACTION)
                    )
                    admitted = formal_ranked[:admission_size]
                    domain = _rank_rows(admitted, _direction_score)
                    selected = domain[:top_k]
                    admission_count += len(admitted)
                group_selections[as_of_date] = selected
                group_domains[as_of_date] = domain
            selections[key] = group_selections
            score_domains[key] = group_domains
            formal_admission_counts[key] = admission_count

        for threshold in normalized_thresholds:
            key = ("D", top_k, threshold)
            group_selections = {}
            group_domains = {}
            for as_of_date, rows in common_by_date.items():
                formal_top = _rank_rows(rows, _formal_score)[:top_k]
                confirmed = [
                    row for row in formal_top if _direction_score(row) >= threshold
                ]
                group_selections[as_of_date] = confirmed
                group_domains[as_of_date] = _rank_rows(confirmed, _direction_score)
            selections[key] = group_selections
            score_domains[key] = group_domains
            formal_admission_counts[key] = sum(
                len(rows) for rows in group_domains.values()
            )

    selection_manifest = [
        {
            "group": group,
            "top_k": top_k,
            "direction_threshold": threshold,
            "dates": {
                as_of_date: [_sector_identity(row) for row in rows]
                for as_of_date, rows in sorted(group_selection.items())
            },
        }
        for (group, top_k, threshold), group_selection in sorted(
            selections.items(), key=_selection_key_sort
        )
    ]
    selection_manifest_sha256 = _canonical_sha256(selection_manifest)

    results = []
    result_lookup: dict[tuple[str, int, float | None], dict[str, Any]] = {}
    for key in sorted(selections, key=_selection_key_sort):
        group, top_k, threshold = key
        result = _evaluate_configuration(
            group=group,
            top_k=top_k,
            direction_threshold=threshold,
            selections=selections[key],
            score_domains=score_domains[key],
            common_by_date=common_by_date,
            horizons=normalized_horizons,
            cluster_map=normalized_cluster_map,
            formal_admission_count=formal_admission_counts[key],
        )
        results.append(result)
        result_lookup[key] = result

    for result in results:
        baseline = result_lookup[("A", result["top_k"], None)]
        for horizon in normalized_horizons:
            horizon_key = f"{horizon}d"
            result["horizons"][horizon_key]["paired_vs_a"] = _paired_comparison(
                result["_daily_returns"][horizon_key],
                baseline["_daily_returns"][horizon_key],
                common_by_date,
            )

    for result in results:
        result.pop("_daily_returns", None)

    date_values = sorted(common_by_date)
    common_sector_names = {
        str(row.get("sector_name") or _sector_identity(row))
        for rows in common_by_date.values()
        for row in rows
    }
    mapped_common_sector_count = len(common_sector_names & set(normalized_cluster_map))
    promotion = _assess_promotion(results, date_values)
    report = {
        "schema_version": "sector_radar_layer_comparison.v1",
        "mode": PAPER_MODE,
        "broker_connection": False,
        "live_order_instruction_generated": False,
        "disclaimer": (
            "Paper/shadow research only. No broker connection or live order instruction."
        ),
        "strict_pit_eligible": False,
        "evidence_classification": (
            "historical_price_volume_proxy_development_evidence_not_oos"
        ),
        "formal_baseline_status": (
            "historical_pit_reconstruction_proxy_not_full_formal_score"
        ),
        "formal_baseline_limitations": {
            "main_net_inflow": "fixed_neutral_zero",
            "constituent_breadth": "unavailable_empty_constituents",
            "market_temperature": "fixed_neutral_50",
            "data_quality_score": "fixed_70",
            "interpretation": (
                "A reconstructs formal scoring logic from historical price/turnover "
                "inputs but is not a full-fidelity historical formal score."
            ),
        },
        "promotion_status": promotion["promotion_status"],
        "preregistration": preregistration_artifact["definition"],
        "preregistration_sha256": preregistration_artifact[
            "preregistration_sha256"
        ],
        "coverage": {
            "common_start_date": date_values[0],
            "common_end_date": date_values[-1],
            "common_date_count": len(date_values),
            "calendar_span_days": (
                _iso_date(date_values[-1], field="end_date")
                - _iso_date(date_values[0], field="start_date")
            ).days,
            "common_sector_count_min": min(len(rows) for rows in common_by_date.values()),
            "common_sector_count_max": max(len(rows) for rows in common_by_date.values()),
            "common_sample_count": sum(len(rows) for rows in common_by_date.values()),
            "feature_eligible_sample_count": sum(
                len(rows) for rows in feature_eligible_by_date.values()
            ),
            "incomplete_common_label_row_count": incomplete_label_rows,
        },
        "provenance": {
            "source_manifest": source_manifest,
            "source_manifest_sha256": source_manifest.get("manifest_sha256"),
            "sample_manifest_sha256": provenance_audit.get(
                "sample_manifest_sha256"
            ),
            "cluster_map_sha256": cluster_map_sha256,
            "cluster_map_sector_count": len(normalized_cluster_map),
            "cluster_map_common_sector_coverage_ratio": _ratio(
                mapped_common_sector_count, len(common_sector_names)
            ),
            "cluster_map_completeness_status": (
                "complete"
                if mapped_common_sector_count == len(common_sector_names)
                else "partial_unmapped_sectors_treated_as_self_clusters"
            ),
            "cluster_concentration_method": (
                "Configured clusters are used when mapped; each unmapped sector is "
                "treated as its own cluster."
            ),
            "universe_vintage_lookahead_eliminated": False,
            "universe_vintage_limitation": (
                "Historical industry-universe membership snapshots are unavailable."
            ),
            "feature_visibility_timestamp_verified": False,
            "source_revision_immutability_verified": False,
            "record_date_as_of_enforced": True,
        },
        "pit_health": {
            "feature_date_violation_count": 0,
            "forward_label_date_violation_count": 0,
            "future_returns_used_only_as_labels": True,
            "selection_manifest_includes_future_returns": False,
            "selection_universe_independent_of_label_availability": True,
            "common_dates_and_feature_universe_enforced": True,
        },
        "selection_manifest": selection_manifest,
        "selection_manifest_sha256": selection_manifest_sha256,
        "results": results,
        "promotion_assessment": promotion,
    }
    _assert_strict_json(report)
    return report


def write_layer_comparison_report(
    report: dict[str, Any], output_dir: str | Path
) -> tuple[Path, Path]:
    """Persist one strict JSON report and its paired Markdown summary."""
    target = Path(output_dir)
    json_path = target / "sector_radar_layer_comparison.json"
    markdown_path = target / "sector_radar_layer_comparison.md"
    write_strict_json_atomic(json_path, report)
    write_text_atomic(markdown_path, _markdown(report))
    return json_path, markdown_path


def _evaluate_configuration(
    *,
    group: str,
    top_k: int,
    direction_threshold: float | None,
    selections: dict[str, list[dict[str, Any]]],
    score_domains: dict[str, list[dict[str, Any]]],
    common_by_date: dict[str, list[dict[str, Any]]],
    horizons: Sequence[int],
    cluster_map: dict[str, str],
    formal_admission_count: int,
) -> dict[str, Any]:
    selected_count = sum(len(rows) for rows in selections.values())
    zero_dates = sum(not rows for rows in selections.values())
    turnover_values = []
    retention_values = []
    previous: set[str] | None = None
    for as_of_date in sorted(selections):
        current = {_sector_identity(row) for row in selections[as_of_date]}
        if previous is not None:
            denominator = max(len(previous), len(current))
            turnover_values.append(
                0.0 if denominator == 0 else 1.0 - len(previous & current) / denominator
            )
            retention_values.append(
                None
                if not previous
                else len(previous & current) / len(previous)
            )
        previous = current

    cluster_max_shares = []
    cluster_hhis = []
    mapped_selected = 0
    for rows in selections.values():
        if not rows:
            continue
        counts: Counter[str] = Counter()
        for row in rows:
            sector_name = str(row.get("sector_name") or _sector_identity(row))
            cluster = cluster_map.get(sector_name)
            if cluster is None:
                cluster = f"unmapped:{sector_name}"
            else:
                mapped_selected += 1
            counts[cluster] += 1
        shares = [count / len(rows) for count in counts.values()]
        cluster_max_shares.append(max(shares))
        cluster_hhis.append(sum(value * value for value in shares))

    rank_stability_values = []
    prior_scores: dict[str, float] | None = None
    for as_of_date in sorted(score_domains):
        score_getter = _formal_score if group == "A" else _direction_score
        current_scores = {
            _sector_identity(row): score_getter(row)
            for row in score_domains[as_of_date]
        }
        if prior_scores is not None:
            overlap = sorted(set(prior_scores) & set(current_scores))
            if len(overlap) >= 2:
                stability = _spearman(
                    [prior_scores[key] for key in overlap],
                    [current_scores[key] for key in overlap],
                )
                if stability is not None:
                    rank_stability_values.append(stability)
        prior_scores = current_scores

    horizons_result: dict[str, Any] = {}
    daily_returns_by_horizon: dict[str, dict[str, float]] = {}
    for horizon in horizons:
        horizon_key = f"{horizon}d"
        daily_selected: dict[str, float] = {}
        daily_universe: dict[str, float] = {}
        selected_observations = []
        score_return_rows = []
        contribution_by_sector: dict[str, float] = defaultdict(float)
        sector_names: dict[str, str] = {}
        for as_of_date in sorted(common_by_date):
            universe_rows = common_by_date[as_of_date]
            universe_labeled = [
                (row, value)
                for row in universe_rows
                if (value := _forward_return_or_none(row, horizon_key)) is not None
            ]
            universe_returns = [value for _row, value in universe_labeled]
            if not universe_returns:
                continue
            universe_mean = mean(universe_returns)
            daily_universe[as_of_date] = universe_mean
            selected_rows = selections[as_of_date]
            selected_labeled = [
                (row, value)
                for row in selected_rows
                if (value := _forward_return_or_none(row, horizon_key)) is not None
            ]
            if selected_labeled:
                selected_returns = [value for _row, value in selected_labeled]
                selected_mean = mean(selected_returns)
                daily_selected[as_of_date] = selected_mean
                selected_observations.extend(selected_returns)
                for row, return_value in selected_labeled:
                    identity = _sector_identity(row)
                    sector_names[identity] = str(row.get("sector_name") or identity)
                    contribution_by_sector[identity] += max(
                        return_value - universe_mean, 0.0
                    )
            score_getter = _formal_score if group == "A" else _direction_score
            for row in score_domains[as_of_date]:
                return_value = _forward_return_or_none(row, horizon_key)
                if return_value is not None:
                    score_return_rows.append(
                        (as_of_date, score_getter(row), return_value)
                    )

        excess_values = [
            value - daily_universe[as_of_date]
            for as_of_date, value in daily_selected.items()
        ]
        daily_values = list(daily_selected.values())
        path = _path_metrics(daily_selected)
        top_contributors = _top_positive_contributors(
            contribution_by_sector, sector_names=sector_names, count=5
        )
        top3_share = _top_positive_contribution_share(contribution_by_sector, count=3)
        horizons_result[horizon_key] = {
            "effective_date_count": len(daily_selected),
            "selected_candidate_observation_count": selected_count,
            "selected_observation_count": len(selected_observations),
            "label_observation_coverage_ratio": _ratio(
                len(selected_observations), selected_count
            ),
            "label_date_coverage_ratio": _ratio(
                len(daily_selected), len(common_by_date)
            ),
            "mean_daily_candidate_return_pct": _rounded_mean(daily_values),
            "mean_daily_universe_return_pct": _rounded_mean(
                [daily_universe[key] for key in sorted(daily_selected)]
            ),
            "mean_daily_excess_return_pct": _rounded_mean(excess_values),
            "positive_day_rate": _ratio(
                sum(value > 0 for value in daily_values), len(daily_values)
            ),
            "positive_candidate_rate": _ratio(
                sum(value > 0 for value in selected_observations),
                len(selected_observations),
            ),
            "mean_daily_rank_ic": _rounded_mean(
                _daily_rank_ics(score_return_rows)
            ),
            "worst_date": path["worst_date"],
            "worst_daily_candidate_return_pct": path[
                "worst_daily_candidate_return_pct"
            ],
            "cumulative_path_return_pct": path["cumulative_path_return_pct"],
            "max_drawdown_pct": path["max_drawdown_pct"],
            "path_interpretation": (
                "Sequential research-label path; overlapping horizons are not a trade simulation."
            ),
            "positive_excess_top3_sector_share": top3_share,
            "positive_excess_top_contributors": top_contributors,
            "regime_attribution": _regime_attribution(
                daily_selected, daily_universe, common_by_date
            ),
        }
        daily_returns_by_horizon[horizon_key] = daily_selected

    return {
        "group": group,
        "top_k": top_k,
        "direction_threshold": direction_threshold,
        "selection": {
            "date_count": len(common_by_date),
            "selected_candidate_count": selected_count,
            "mean_candidates_per_date": _round(
                selected_count / len(common_by_date)
            ),
            "zero_candidate_date_count": zero_dates,
            "formal_admission_count": formal_admission_count,
            "mean_turnover_rate": _rounded_mean(turnover_values),
            "mean_top_k_retention_rate": _rounded_mean(
                [value for value in retention_values if value is not None]
            ),
            "mean_rank_stability_spearman": _rounded_mean(rank_stability_values),
            "mean_max_cluster_share": _rounded_mean(cluster_max_shares),
            "mean_cluster_hhi": _rounded_mean(cluster_hhis),
            "cluster_map_selected_coverage_ratio": _ratio(
                mapped_selected, selected_count
            ),
        },
        "score_health": _score_health(score_domains, group),
        "horizons": horizons_result,
        "_daily_returns": daily_returns_by_horizon,
    }


def _paired_comparison(
    candidate: dict[str, float],
    baseline: dict[str, float],
    common_by_date: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    common_dates = sorted(set(candidate) & set(baseline))
    differences = {
        value: candidate[value] - baseline[value] for value in common_dates
    }
    by_regime: dict[str, list[float]] = defaultdict(list)
    for as_of_date, difference in differences.items():
        by_regime[_date_regime(common_by_date[as_of_date])].append(difference)
    return {
        "paired_date_count": len(common_dates),
        "missing_pair_date_count": len(common_by_date) - len(common_dates),
        "paired_date_coverage_ratio": _ratio(len(common_dates), len(common_by_date)),
        "mean_daily_difference_pct": _rounded_mean(list(differences.values())),
        "positive_difference_rate": _ratio(
            sum(value > 0 for value in differences.values()), len(differences)
        ),
        "worst_daily_difference_pct": (
            _round(min(differences.values())) if differences else None
        ),
        "regime_differences": {
            regime: {
                "date_count": len(values),
                "mean_daily_difference_pct": _rounded_mean(values),
            }
            for regime, values in sorted(by_regime.items())
        },
    }


def _assess_promotion(
    results: list[dict[str, Any]], common_dates: Sequence[str]
) -> dict[str, Any]:
    baselines = {
        result["top_k"]: result for result in results if result["group"] == "A"
    }
    candidates = []
    for result in results:
        if result["group"] == "A":
            continue
        baseline = baselines[result["top_k"]]
        reasons = []
        if len(common_dates) < 60:
            reasons.append("fewer_than_60_effective_dates")
        span = (
            _iso_date(common_dates[-1], field="end_date")
            - _iso_date(common_dates[0], field="start_date")
        ).days
        if span < 90:
            reasons.append("coverage_shorter_than_three_calendar_months")
        for horizon_key in ("3d", "5d"):
            metrics = result["horizons"][horizon_key]
            baseline_metrics = baseline["horizons"][horizon_key]
            if (metrics["label_date_coverage_ratio"] or 0.0) < 0.9:
                reasons.append(f"{horizon_key}_label_coverage_below_90_percent")
            if not _strictly_greater(
                metrics["mean_daily_excess_return_pct"],
                baseline_metrics["mean_daily_excess_return_pct"],
            ):
                reasons.append(f"{horizon_key}_excess_not_better_than_a")
            if not _not_lower(
                metrics["positive_day_rate"], baseline_metrics["positive_day_rate"]
            ):
                reasons.append(f"{horizon_key}_win_rate_below_a")
        if not _not_lower(
            result["horizons"]["1d"]["max_drawdown_pct"],
            baseline["horizons"]["1d"]["max_drawdown_pct"],
        ):
            reasons.append("1d_max_drawdown_worse_than_a")
        candidate_turnover = result["selection"]["mean_turnover_rate"]
        baseline_turnover = baseline["selection"]["mean_turnover_rate"]
        if (
            candidate_turnover is None
            or baseline_turnover is None
            or candidate_turnover > baseline_turnover * 1.10 + 1e-12
        ):
            reasons.append("turnover_more_than_10_percent_above_a")
        positive_regimes = {
            regime
            for horizon_key in ("3d", "5d")
            for regime, values in result["horizons"][horizon_key]["paired_vs_a"][
                "regime_differences"
            ].items()
            if (values["mean_daily_difference_pct"] or 0.0) > 0
        }
        if len(positive_regimes) < 2:
            reasons.append("advantage_not_positive_in_two_market_regimes")
        concentration_values = [
            result["horizons"][key]["positive_excess_top3_sector_share"]
            for key in ("3d", "5d")
        ]
        if any(value is None or value > 0.5 for value in concentration_values):
            reasons.append("positive_excess_concentrated_in_top3_sectors")
        paired_advantage = _rounded_mean(
            [
                result["horizons"][key]["paired_vs_a"][
                    "mean_daily_difference_pct"
                ]
                for key in ("3d", "5d")
                if result["horizons"][key]["paired_vs_a"][
                    "mean_daily_difference_pct"
                ]
                is not None
            ]
        )
        candidates.append(
            {
                "group": result["group"],
                "top_k": result["top_k"],
                "direction_threshold": result["direction_threshold"],
                "development_gate_passed": not reasons,
                "blocking_reasons": reasons,
                "mean_paired_3d_5d_advantage_pct": paired_advantage,
            }
        )

    descriptive_best = max(
        candidates,
        key=lambda item: (
            item["mean_paired_3d_5d_advantage_pct"]
            if item["mean_paired_3d_5d_advantage_pct"] is not None
            else -math.inf,
            -item["top_k"],
            item["group"],
        ),
    )
    passed = [item for item in candidates if item["development_gate_passed"]]
    blocking_reasons = []
    if len(common_dates) < 60:
        blocking_reasons.append("fewer_than_60_effective_dates")
    if not passed:
        blocking_reasons.append("no_candidate_passed_all_preregistered_performance_gates")
    blocking_reasons.append("historical_industry_universe_not_versioned")
    blocking_reasons.append("formal_baseline_is_price_volume_proxy_not_full_fidelity")
    blocking_reasons.append("source_visibility_and_revision_history_not_verified")
    if passed:
        development_best = max(
            passed,
            key=lambda item: item["mean_paired_3d_5d_advantage_pct"],
        )
        recommended_architecture = {
            "B": "direction_shadow_as_trend_module_replacement_candidate",
            "C": "formal_admission_then_direction_rerank_shadow",
            "D": "formal_top_k_with_direction_confirmation_shadow",
        }[development_best["group"]]
    else:
        development_best = None
        recommended_architecture = "maintain_current_formal_plus_shadow"
    return {
        "promotion_status": "insufficient_evidence",
        "strict_pit_promotion_allowed": False,
        "recommended_architecture": recommended_architecture,
        "descriptive_best_not_a_promotion_decision": descriptive_best,
        "development_gate_best": development_best,
        "blocking_reasons": blocking_reasons,
        "candidate_gates": candidates,
    }


def _preregistration(
    top_ks: Sequence[int], thresholds: Sequence[float], horizons: Sequence[int]
) -> dict[str, Any]:
    return {
        "status": "definition_identity_requires_cli_pre_data_freeze",
        "groups": {
            "A": {
                "definition": "historical_pit_reconstructed_formal_score_proxy_top_k",
                "role": "proxy_baseline",
                "full_formal_score_fidelity": False,
            },
            "B": {"definition": "direction_score_shadow_top_k"},
            "C": {
                "definition": "formal_admission_then_direction_score_shadow_top_k",
                "formal_admission": "top_25_percent_within_common_eligible_universe",
            },
            "D": {
                "definition": "formal_top_k_filtered_by_direction_threshold",
                "empty_dates_retained": True,
            },
        },
        "top_ks": list(top_ks),
        "direction_thresholds": list(thresholds),
        "horizons": [f"{value}d" for value in horizons],
        "common_admission": {
            "data_quality_component_minimum": COMMON_DATA_QUALITY_FLOOR,
            "accepted_risk_levels": sorted(COMMON_ACCEPTED_RISK_LEVELS),
            "price_change_available_required": True,
            "trend_history_status_required": "ok",
            "direction_score_required": True,
            "selection_universe_independent_of_label_availability": True,
        },
        "promotion_gates": {
            "minimum_effective_dates": 60,
            "minimum_calendar_span_days": 90,
            "minimum_3d_5d_label_coverage_ratio": 0.9,
            "3d_5d_excess_strictly_better_than_a": True,
            "3d_5d_win_rate_not_below_a": True,
            "1d_max_drawdown_not_worse_than_a": True,
            "turnover_multiplier_vs_a_maximum": 1.10,
            "minimum_positive_market_regimes": 2,
            "positive_excess_top3_sector_share_maximum": 0.5,
        },
    }


def _common_feature_eligible(sample: dict[str, Any]) -> bool:
    formal = _finite_or_none(sample.get("radar_base_score"))
    breakdown = (sample.get("score_breakdowns") or {}).get("radar_base_score") or {}
    direction = _finite_or_none(
        (breakdown.get("three_layer_shadow") or {}).get("direction_score_shadow")
    )
    data_quality = _finite_or_none(breakdown.get("data_quality"))
    risk_level = (breakdown.get("risk_breakdown") or {}).get("risk_level")
    risk_level = str(getattr(risk_level, "value", risk_level)).lower()
    return bool(
        formal is not None
        and direction is not None
        and data_quality is not None
        and data_quality >= COMMON_DATA_QUALITY_FLOOR
        and risk_level in COMMON_ACCEPTED_RISK_LEVELS
        and breakdown.get("price_change_available") is True
        and breakdown.get("trend_history_status") == "ok"
    )


def _score_health(
    score_domains: dict[str, list[dict[str, Any]]], group: str
) -> dict[str, Any]:
    getter = _formal_score if group == "A" else _direction_score
    constant_dates = 0
    tied_samples = 0
    total_samples = 0
    unique_ratios = []
    for rows in score_domains.values():
        scores = [getter(row) for row in rows]
        if not scores:
            continue
        counts = Counter(scores)
        constant_dates += len(counts) == 1
        tied_samples += sum(count for count in counts.values() if count > 1)
        total_samples += len(scores)
        unique_ratios.append(len(counts) / len(scores))
    return {
        "constant_score_date_count": constant_dates,
        "tied_sample_rate": _ratio(tied_samples, total_samples),
        "mean_unique_score_ratio": _rounded_mean(unique_ratios),
        "finite_score_coverage_ratio": 1.0 if total_samples else 0.0,
    }


def _regime_attribution(
    daily_selected: dict[str, float],
    daily_universe: dict[str, float],
    common_by_date: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for as_of_date, selected_return in daily_selected.items():
        grouped[_date_regime(common_by_date[as_of_date])].append(
            (selected_return, daily_universe[as_of_date])
        )
    return {
        regime: {
            "date_count": len(values),
            "mean_candidate_return_pct": _rounded_mean(
                [value[0] for value in values]
            ),
            "mean_excess_return_pct": _rounded_mean(
                [value[0] - value[1] for value in values]
            ),
            "positive_day_rate": _ratio(
                sum(value[0] > 0 for value in values), len(values)
            ),
        }
        for regime, values in sorted(grouped.items())
    }


def _date_regime(rows: Sequence[dict[str, Any]]) -> str:
    regimes = [
        str((row.get("feature_inputs") or {}).get("market_regime") or "unknown")
        for row in rows
    ]
    return Counter(regimes).most_common(1)[0][0] if regimes else "unknown"


def _path_metrics(daily_returns: dict[str, float]) -> dict[str, Any]:
    if not daily_returns:
        return {
            "worst_date": None,
            "worst_daily_candidate_return_pct": None,
            "cumulative_path_return_pct": None,
            "max_drawdown_pct": None,
        }
    wealth = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in [daily_returns[key] for key in sorted(daily_returns)]:
        wealth *= 1.0 + value / 100.0
        peak = max(peak, wealth)
        max_drawdown = min(max_drawdown, wealth / peak - 1.0)
    worst_date = min(daily_returns, key=lambda key: daily_returns[key])
    return {
        "worst_date": worst_date,
        "worst_daily_candidate_return_pct": _round(daily_returns[worst_date]),
        "cumulative_path_return_pct": _round((wealth - 1.0) * 100.0),
        "max_drawdown_pct": _round(max_drawdown * 100.0),
    }


def _daily_rank_ics(rows: Iterable[tuple[str, float, float]]) -> list[float]:
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for as_of_date, score, return_value in rows:
        grouped[as_of_date].append((score, return_value))
    result = []
    for pairs in grouped.values():
        if len(pairs) < 2:
            continue
        value = _spearman(
            [pair[0] for pair in pairs], [pair[1] for pair in pairs]
        )
        if value is not None:
            result.append(value)
    return result


def _spearman(x_values: Sequence[float], y_values: Sequence[float]) -> float | None:
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return None
    x_ranks = _average_ranks(x_values)
    y_ranks = _average_ranks(y_values)
    x_mean = mean(x_ranks)
    y_mean = mean(y_ranks)
    numerator = sum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x_ranks, y_ranks)
    )
    x_scale = math.sqrt(sum((value - x_mean) ** 2 for value in x_ranks))
    y_scale = math.sqrt(sum((value - y_mean) ** 2 for value in y_ranks))
    if x_scale == 0 or y_scale == 0:
        return None
    return numerator / (x_scale * y_scale)


def _average_ranks(values: Sequence[float]) -> list[float]:
    positions: dict[float, list[int]] = defaultdict(list)
    for index, value in enumerate(values):
        positions[value].append(index)
    result = [0.0] * len(values)
    cursor = 1
    for value in sorted(positions):
        indices = positions[value]
        average_rank = (cursor + cursor + len(indices) - 1) / 2.0
        for index in indices:
            result[index] = average_rank
        cursor += len(indices)
    return result


def _top_positive_contribution_share(
    contributions: dict[str, float], *, count: int
) -> float | None:
    positives = sorted((value for value in contributions.values() if value > 0), reverse=True)
    total = sum(positives)
    return None if total <= 0 else _round(sum(positives[:count]) / total)


def _top_positive_contributors(
    contributions: dict[str, float],
    *,
    sector_names: dict[str, str],
    count: int,
) -> list[dict[str, Any]]:
    ranked = sorted(
        ((identity, value) for identity, value in contributions.items() if value > 0),
        key=lambda item: (-item[1], item[0]),
    )
    total = sum(value for _identity, value in ranked)
    return [
        {
            "sector_id": identity,
            "sector_name": sector_names.get(identity, identity),
            "positive_excess_contribution_pct_points": _round(value),
            "share": _round(value / total),
        }
        for identity, value in ranked[:count]
    ]


def _normalize_cluster_map(cluster_map: dict[str, Sequence[str]]) -> dict[str, str]:
    result = {}
    for cluster, sectors in sorted(cluster_map.items()):
        if not isinstance(sectors, (list, tuple)):
            raise ValueError("cluster members must be a list")
        for sector in sectors:
            name = str(sector)
            if name in result:
                raise ValueError(f"sector appears in multiple clusters: {name}")
            result[name] = str(cluster)
    return result


def _rank_rows(
    rows: Sequence[dict[str, Any]], getter: Any
) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (-getter(row), _sector_identity(row)))


def _formal_score(row: dict[str, Any]) -> float:
    value = _finite_or_none(row.get("radar_base_score"))
    if value is None:
        raise ValueError("radar_base_score must be finite")
    return value


def _direction_score(row: dict[str, Any]) -> float:
    breakdown = (row.get("score_breakdowns") or {}).get("radar_base_score") or {}
    value = _finite_or_none(
        (breakdown.get("three_layer_shadow") or {}).get("direction_score_shadow")
    )
    if value is None:
        raise ValueError("direction_score_shadow must be finite")
    return value


def _forward_return_or_none(
    row: dict[str, Any], horizon_key: str
) -> float | None:
    value = _finite_or_none((row.get("forward_returns") or {}).get(horizon_key))
    return value


def _pit_sample_manifest_sha(samples: Sequence[dict[str, Any]]) -> str:
    rows = [
        {
            "as_of_date": sample["as_of_date"],
            "sector_id": sample["sector_id"],
            "feature_max_date": sample["feature_max_date"],
            "radar_base_score": sample["radar_base_score"],
            "trend_continuation_score": sample["trend_continuation_score"],
            "short_term_burst_score": sample["short_term_burst_score"],
            "three_layer_shadow": sample["score_breakdowns"][
                "radar_base_score"
            ].get("three_layer_shadow"),
        }
        for sample in samples
    ]
    return _canonical_sha256(rows)


def _sector_identity(row: dict[str, Any]) -> str:
    identity = str(row.get("sector_id") or row.get("sector_name") or "")
    if not identity:
        raise ValueError("sector identity is required")
    return identity


def _selection_key_sort(
    item: tuple[str, int, float | None]
    | tuple[tuple[str, int, float | None], Any]
) -> tuple[str, int, float]:
    key = item[0] if len(item) == 2 and isinstance(item[0], tuple) else item
    group, top_k, threshold = key
    return group, top_k, -math.inf if threshold is None else threshold


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _finite_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _positive_unique_ints(values: Sequence[int], *, field: str) -> tuple[int, ...]:
    result = tuple(dict.fromkeys(values))
    if not result or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in result):
        raise ValueError(f"{field} must contain positive integers")
    return result


def _finite_unique_numbers(
    values: Sequence[float], *, field: str
) -> tuple[float, ...]:
    result = tuple(dict.fromkeys(float(value) for value in values))
    if not result or any(not math.isfinite(value) for value in result):
        raise ValueError(f"{field} must contain finite numbers")
    return result


def _iso_date(value: Any, *, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field} must be a canonical ISO date")
    return parsed


def _strictly_greater(candidate: Any, baseline: Any) -> bool:
    return candidate is not None and baseline is not None and candidate > baseline


def _not_lower(candidate: Any, baseline: Any) -> bool:
    return candidate is not None and baseline is not None and candidate >= baseline


def _round(value: float) -> float:
    return round(float(value), 8)


def _rounded_mean(values: Sequence[float]) -> float | None:
    return None if not values else _round(mean(values))


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else _round(numerator / denominator)


def _assert_strict_json(payload: dict[str, Any]) -> None:
    json.dumps(payload, ensure_ascii=False, allow_nan=False)


def _markdown(report: dict[str, Any]) -> str:
    coverage = report["coverage"]
    lines = [
        "# Sector Radar Layer Historical Comparison",
        "",
        "> Paper/shadow research only. No broker connection or live order instruction.",
        "",
        "## Coverage",
        "",
        f"- Dates: {coverage['common_start_date']} to {coverage['common_end_date']} ({coverage['common_date_count']})",
        f"- Common sectors per date: {coverage['common_sector_count_min']} to {coverage['common_sector_count_max']}",
        f"- Strict PIT eligible: {str(report['strict_pit_eligible']).lower()}",
        f"- Formal baseline status: {report['formal_baseline_status']}",
        "- A is a price/turnover reconstruction proxy, not a full-fidelity historical formal score.",
        "- Record-date as-of is enforced; source visibility timestamps and revision immutability are not verified.",
        f"- Promotion status: {report['promotion_status']}",
        "",
        "## Results",
        "",
        "| Group | Top K | Threshold | 3d excess | 3d win | 5d excess | 5d win | 1d drawdown | Turnover |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in report["results"]:
        threshold = result["direction_threshold"]
        lines.append(
            "| "
            f"{result['group']} | {result['top_k']} | {threshold if threshold is not None else 'n/a'} | "
            f"{_fmt(result['horizons']['3d']['mean_daily_excess_return_pct'])} | "
            f"{_fmt(result['horizons']['3d']['positive_day_rate'])} | "
            f"{_fmt(result['horizons']['5d']['mean_daily_excess_return_pct'])} | "
            f"{_fmt(result['horizons']['5d']['positive_day_rate'])} | "
            f"{_fmt(result['horizons']['1d']['max_drawdown_pct'])} | "
            f"{_fmt(result['selection']['mean_turnover_rate'])} |"
        )
    assessment = report["promotion_assessment"]
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Recommended architecture: {assessment['recommended_architecture']}",
            f"- Promotion status: {assessment['promotion_status']}",
            "- Blocking reasons: " + ", ".join(assessment["blocking_reasons"]),
            "- Evidence is historical development evidence, not blind/OOS evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.6f}"
