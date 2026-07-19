"""Point-in-time validation for sector radar, trend, and burst scores."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from statistics import mean, median
from typing import Any, Iterable, Sequence

from ..agents.ranking_report.sector_ranking_agent import generate_sector_ranking
from ..agents.sector_scoring.sector_scoring_agent import calculate_sector_scores
from ..cli import _calculate_history_metrics
from ..data.return_validation import trusted_daily_return
from ..models import SectorScore, SectorSnapshot, SectorType
from ..reporting.strict_json import loads_strict_json, write_strict_json_atomic
from ..scoring.sector_composite_score import apply_insufficient_history_cap
from ..scoring.short_term_burst_score import apply_burst_insufficient_history_cap


SCORE_FIELDS = {
    "radar_base_score": "radar_base_score",
    "trend_continuation_score": "trend_continuation_score",
    "short_term_burst_score": "short_term_burst_score",
}

TECHNICAL_CANDIDATE_NAMES = {
    "radar_technical_evidence_v2",
    "radar_technical_evidence_v3",
}

ARTIFACT_STATUSES = {
    "unclassified_shadow_validation",
    "current_path_a_v3",
    "archived_fourth_round",
    "superseded_path_a_v2",
    "superseded_historical_intermediate_snapshot",
}

ABLATION_COMPONENTS = {
    "radar_base_score": (
        "trend_strength",
        "fund_flow",
        "breadth",
        "persistence",
        "market_fit",
        "data_quality",
    ),
    "trend_continuation_score": (
        "radar_score_component",
        "momentum_component",
        "relative_strength_component",
        "persistence_component",
        "drawdown_component",
        "volatility_component",
        "data_quality_component",
    ),
    "short_term_burst_score": (
        "radar_today_component",
        "one_day_change_component",
        "three_day_momentum_component",
        "volume_or_heat_component",
        "rank_jump_component",
        "data_quality_component",
    ),
}


def build_pit_dataset(
    history_root: str | Path,
    *,
    sector_type: str = "industry",
    start_date: str | None = None,
    end_date: str | None = None,
    trend_window: int = 10,
    horizons: Sequence[int] = (1, 3, 5),
    holdout_days: int = 20,
) -> dict[str, Any]:
    """Recompute score features from source records available at each date."""
    if sector_type != "industry":
        raise ValueError("PIT validation currently supports industry history only")
    if trend_window <= 0:
        raise ValueError("trend_window must be positive")
    normalized_horizons = _normalize_horizons(horizons)
    if holdout_days < 0:
        raise ValueError("holdout_days must be non-negative")

    histories, source_manifest = _load_histories(history_root, sector_type)
    source_calendar_dates = sorted(
        {
            record["date"]
            for history in histories.values()
            for record in history["records"]
        }
    )
    all_dates = list(source_calendar_dates)
    if start_date is not None:
        _parse_iso_date(start_date, "start_date")
        all_dates = [value for value in all_dates if value >= start_date]
    if end_date is not None:
        _parse_iso_date(end_date, "end_date")
        all_dates = [value for value in all_dates if value <= end_date]

    labelable_dates = [
        value
        for value in all_dates
        if _labelable_sector_count(
            histories,
            value,
            normalized_horizons,
            source_calendar_dates,
        )
        >= 2
    ]
    if holdout_days > len(labelable_dates):
        raise ValueError("holdout_days exceeds labelable date count")
    holdout_dates = (
        labelable_dates[-holdout_days:] if holdout_days else []
    )
    holdout_set = set(holdout_dates)
    labelable_set = set(labelable_dates)
    calendar_positions = {
        value: index for index, value in enumerate(source_calendar_dates)
    }
    holdout_start = holdout_dates[0] if holdout_dates else None
    purged_development_dates = [
        value
        for value in labelable_dates
        if value not in holdout_set
        and holdout_start is not None
        and any(
            source_calendar_dates[calendar_positions[value] + horizon]
            >= holdout_start
            for horizon in normalized_horizons
        )
    ]
    purged_set = set(purged_development_dates)
    development_dates = [
        value
        for value in labelable_dates
        if value not in holdout_set and value not in purged_set
    ]

    samples = []
    previous_ranks: dict[str, int] = {}
    date_sector_counts: dict[str, int] = {}
    scoring_date_sector_counts: dict[str, int] = {}
    for as_of_date in all_dates:
        snapshots = []
        contexts: dict[str, dict[str, Any]] = {}
        source_position = calendar_positions[as_of_date]
        target_dates = {
            horizon: source_calendar_dates[source_position + horizon]
            for horizon in normalized_horizons
            if source_position + horizon < len(source_calendar_dates)
        }
        for sector_id, history in histories.items():
            index = history["index_by_date"].get(as_of_date)
            if index is None:
                continue
            record = history["records"][index]
            previous_close = (
                history["records"][index - 1]["close"] if index > 0 else None
            )
            price_available = previous_close is not None and previous_close > 0
            change_pct = (
                trusted_daily_return(
                    (record["close"] / previous_close - 1.0) * 100.0,
                    field="PIT derived daily return",
                )
                if price_available
                else 0.0
            )
            snapshots.append(
                SectorSnapshot(
                    sector_id=sector_id,
                    name=history["name"],
                    type=SectorType.INDUSTRY,
                    price_change_pct=change_pct,
                    turnover=record["turnover"],
                    main_net_inflow=0.0,
                    data_quality_score=70.0,
                    price_change_available=price_available,
                    data_sources=[history["source"]],
                    updated_at=as_of_date,
                )
            )
            contexts[sector_id] = {"history": history, "index": index}

        if len(snapshots) < 2:
            continue
        scoring_date_sector_counts[as_of_date] = len(snapshots)
        history_metrics = {}
        for snapshot in snapshots:
            context = contexts[snapshot.sector_id]
            source_records = context["history"]["records"][: context["index"] + 1]
            history_metrics[snapshot.name] = _calculate_history_metrics(
                [
                    {"date": item["date"], "close": item["close"]}
                    for item in source_records
                ]
            )
        ranking = generate_sector_ranking(
            snapshots,
            [],
            market_temperature=50.0,
            top_n=len(snapshots),
            industry_history=history_metrics,
        )
        radar_scores = [
            SectorScore(**row) for row in ranking.data["industry_top"]
        ]
        for score in radar_scores:
            score.previous_rank = previous_ranks.get(score.sector_id)

        feature_inputs_by_id = {
            score.sector_id: _pit_feature_inputs(
                contexts[score.sector_id]["history"],
                contexts[score.sector_id]["index"],
                history_metrics[score.name],
                trend_window,
            )
            for score in radar_scores
        }
        _add_cross_sectional_technical_inputs(feature_inputs_by_id.values())

        derived_output = calculate_sector_scores(
            radar_scores,
            history_metrics,
            sector_type=SectorType.INDUSTRY,
            trend_window=trend_window,
            history_source="sector_history_cache",
        )
        derived_by_id = {
            row["sector_id"]: row for row in derived_output.data["scores"]
        }
        if as_of_date in labelable_set:
            date_sector_counts[as_of_date] = len(radar_scores)

        for radar in radar_scores:
            if as_of_date not in labelable_set:
                continue
            context = contexts[radar.sector_id]
            history = context["history"]
            source_index = context["index"]
            derived = derived_by_id[radar.sector_id]
            if (
                len(target_dates) != len(normalized_horizons)
                or any(
                    target_date not in history["index_by_date"]
                    for target_date in target_dates.values()
                )
            ):
                continue
            labels_withheld = as_of_date in holdout_set or as_of_date in purged_set
            forward_returns = {}
            forward_label_dates = {}
            for horizon in normalized_horizons:
                if labels_withheld:
                    forward_returns[f"{horizon}d"] = None
                    forward_label_dates[f"{horizon}d"] = None
                    continue
                label_record = history["records"][
                    history["index_by_date"][target_dates[horizon]]
                ]
                forward_returns[f"{horizon}d"] = (
                    label_record["close"] / history["records"][source_index]["close"]
                    - 1.0
                ) * 100.0
                forward_label_dates[f"{horizon}d"] = label_record["date"]

            samples.append(
                {
                    "as_of_date": as_of_date,
                    "sector_id": radar.sector_id,
                    "sector_name": radar.name,
                    "feature_max_date": history["records"][source_index]["date"],
                    "forward_returns": forward_returns,
                    "forward_label_dates": forward_label_dates,
                    "radar_base_score": radar.score,
                    "trend_continuation_score": derived["trend_continuation_score"],
                    "short_term_burst_score": derived["short_term_burst_score"],
                    "score_breakdowns": {
                        "radar_base_score": radar.score_breakdown,
                        "trend_continuation_score": derived["trend_breakdown"],
                        "short_term_burst_score": derived["burst_breakdown"],
                    },
                    "feature_inputs": feature_inputs_by_id[radar.sector_id],
                    "rank_metadata": {
                        "radar_rank": radar.current_rank,
                        "radar_rank_tied": radar.rank_tied,
                        "trend_rank": derived["trend_rank"],
                        "trend_rank_tied": derived["trend_rank_tied"],
                        "burst_rank": derived["burst_rank"],
                        "burst_rank_tied": derived["burst_rank_tied"],
                    },
                    "cap_metadata": {
                        "trend_cap_applied": bool(
                            derived["trend_breakdown"].get("_history_cap_applied", False)
                        ),
                        "burst_cap_applied": bool(
                            derived.get("_burst_history_cap_applied", False)
                        ),
                    },
                    "trend_window_status": derived["trend_window_status"],
                    "history_coverage_ratio": derived["history_coverage_ratio"],
                    "history_source": "sector_history_cache",
                }
            )

        previous_ranks = {
            score.sector_id: int(score.current_rank)
            for score in radar_scores
            if score.current_rank is not None
        }

    violations = [
        {
            "as_of_date": sample["as_of_date"],
            "sector_id": sample["sector_id"],
            "feature_max_date": sample["feature_max_date"],
        }
        for sample in samples
        if sample["feature_max_date"] > sample["as_of_date"]
    ]
    if violations:
        raise ValueError("feature source date exceeds as_of_date")

    return {
        "source_manifest": source_manifest,
        "sector_type": sector_type,
        "trend_window": trend_window,
        "horizons": [f"{value}d" for value in normalized_horizons],
        "labelable_dates": labelable_dates,
        "development_dates": development_dates,
        "purged_development_dates": purged_development_dates,
        "holdout": {
            "status": (
                "observed_evaluation_tail" if holdout_dates else "not_configured"
            ),
            "dates": holdout_dates,
            "labels_materialized": False,
            "blind": False,
            "eligible_for_oos_claim": False,
            "boundary_purge_horizon_days": max(normalized_horizons),
            "purged_development_dates": purged_development_dates,
        },
        "date_sector_counts": date_sector_counts,
        "scoring_date_sector_counts": scoring_date_sector_counts,
        "samples": samples,
        "provenance_audit": {
            "feature_date_violation_count": 0,
            "sample_count": len(samples),
            "sample_manifest_sha256": _sample_manifest_sha(samples),
            "record_date_as_of_enforced": True,
            "universe_vintage_lookahead_eliminated": False,
            "universe_vintage_limitation": (
                "historical sector-universe membership snapshots unavailable"
            ),
        },
    }


def evaluate_score_rows(
    rows: Iterable[dict[str, Any]],
    *,
    score_key: str = "score",
    return_key: str = "forward_return",
    top_k: int = 5,
) -> dict[str, Any]:
    """Evaluate score-vs-return relationships by daily cross-section."""
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        score = _finite_or_none(row.get(score_key))
        forward_return = _finite_or_none(row.get(return_key))
        as_of_date = row.get("as_of_date")
        if score is None or forward_return is None or not isinstance(as_of_date, str):
            continue
        grouped[as_of_date].append((score, forward_return))

    daily_rank_ics = []
    daily_top_bottom = []
    daily_top_universe = []
    top_returns = []
    sample_count = 0
    usable_dates = 0
    for as_of_date in sorted(grouped):
        pairs = grouped[as_of_date]
        sample_count += len(pairs)
        if len(pairs) < 2:
            continue
        rank_ic = _spearman(
            [pair[0] for pair in pairs],
            [pair[1] for pair in pairs],
        )
        if rank_ic is not None:
            daily_rank_ics.append(rank_ic)
        top = _select_score_tail(pairs, top_k, highest=True)
        bottom = _select_score_tail(pairs, top_k, highest=False)
        if top and bottom:
            top_mean = mean(pair[1] for pair in top)
            bottom_mean = mean(pair[1] for pair in bottom)
            universe_mean = mean(pair[1] for pair in pairs)
            daily_top_bottom.append(top_mean - bottom_mean)
            daily_top_universe.append(top_mean - universe_mean)
            top_returns.extend(pair[1] for pair in top)
        usable_dates += 1

    return {
        "date_count": usable_dates,
        "sample_count": sample_count,
        "mean_daily_rank_ic": _rounded_mean(daily_rank_ics),
        "median_daily_rank_ic": _rounded_median(daily_rank_ics),
        "positive_daily_rank_ic_rate": _rounded_ratio(
            sum(value > 0 for value in daily_rank_ics), len(daily_rank_ics)
        ),
        "top_bottom_spread": _rounded_mean(daily_top_bottom),
        "top_universe_spread": _rounded_mean(daily_top_universe),
        "top_k_positive_rate": _rounded_ratio(
            sum(value > 0 for value in top_returns), len(top_returns)
        ),
        "top_k_observation_count": len(top_returns),
    }


def build_walk_forward_folds(
    dates: Sequence[str],
    *,
    fold_count: int = 4,
    purge_days: int = 5,
    embargo_days: int = 2,
    initial_train_ratio: float = 0.4,
) -> list[dict[str, Any]]:
    """Build expanding folds with a fixed purge plus embargo gap."""
    ordered_dates = sorted(dict.fromkeys(dates))
    if fold_count <= 0:
        raise ValueError("fold_count must be positive")
    if purge_days < 0 or embargo_days < 0:
        raise ValueError("purge_days and embargo_days must be non-negative")
    if not 0 < initial_train_ratio < 1:
        raise ValueError("initial_train_ratio must be between zero and one")
    if len(ordered_dates) < 2:
        return []

    initial_train = max(1, int(len(ordered_dates) * initial_train_ratio))
    remaining = ordered_dates[initial_train:]
    if len(remaining) < fold_count:
        return []
    chunks = _split_evenly(remaining, fold_count)
    gap = purge_days + embargo_days
    folds = []
    positions = {value: index for index, value in enumerate(ordered_dates)}
    for index, test_dates in enumerate(chunks, start=1):
        if not test_dates:
            continue
        test_start = positions[test_dates[0]]
        train_end = max(0, test_start - gap)
        train_dates = ordered_dates[:train_end]
        if not train_dates:
            continue
        folds.append(
            {
                "fold": index,
                "train_dates": train_dates,
                "test_dates": test_dates,
                "purge_days": purge_days,
                "embargo_days": embargo_days,
            }
        )
    return folds


def run_pit_validation(
    history_root: str | Path,
    *,
    sector_type: str = "industry",
    start_date: str | None = None,
    end_date: str | None = None,
    trend_window: int = 10,
    horizons: Sequence[int] = (1, 3, 5),
    holdout_days: int = 20,
    top_k: int = 5,
    fold_count: int = 4,
    purge_days: int | None = None,
    embargo_days: int = 2,
    artifact_status: str = "unclassified_shadow_validation",
) -> dict[str, Any]:
    """Build the PIT dataset and return a shadow-only validation report."""
    if artifact_status not in ARTIFACT_STATUSES:
        raise ValueError(f"unsupported artifact_status: {artifact_status}")
    dataset = build_pit_dataset(
        history_root,
        sector_type=sector_type,
        start_date=start_date,
        end_date=end_date,
        trend_window=trend_window,
        horizons=horizons,
        holdout_days=holdout_days,
    )
    development_set = set(dataset["development_dates"])
    development_samples = [
        sample
        for sample in dataset["samples"]
        if sample["as_of_date"] in development_set
    ]
    normalized_horizons = [int(value[:-1]) for value in dataset["horizons"]]
    maximum_horizon = max(normalized_horizons)
    if purge_days is not None and purge_days < maximum_horizon:
        raise ValueError(
            f"purge_days must be at least maximum horizon {maximum_horizon}"
        )
    effective_purge = maximum_horizon if purge_days is None else purge_days
    folds = build_walk_forward_folds(
        dataset["development_dates"],
        fold_count=fold_count,
        purge_days=effective_purge,
        embargo_days=embargo_days,
    )

    score_results = {}
    for score_name, score_field in SCORE_FIELDS.items():
        horizon_results = {}
        walk_forward = {}
        for horizon in dataset["horizons"]:
            rows = [
                {
                    "as_of_date": sample["as_of_date"],
                    "score": sample[score_field],
                    "forward_return": sample["forward_returns"][horizon],
                }
                for sample in development_samples
            ]
            horizon_results[horizon] = evaluate_score_rows(rows, top_k=top_k)
            fold_results = []
            for fold in folds:
                train_set = set(fold["train_dates"])
                test_set = set(fold["test_dates"])
                train_rows = [
                    row for row in rows if row["as_of_date"] in train_set
                ]
                test_rows = [
                    row for row in rows if row["as_of_date"] in test_set
                ]
                fold_results.append(
                    {
                        "fold": fold["fold"],
                        "train_start": fold["train_dates"][0],
                        "train_end": fold["train_dates"][-1],
                        "test_start": fold["test_dates"][0],
                        "test_end": fold["test_dates"][-1],
                        "train_date_count": len(fold["train_dates"]),
                        "test_date_count": len(fold["test_dates"]),
                        "purge_days": fold["purge_days"],
                        "embargo_days": fold["embargo_days"],
                        "train_metrics": evaluate_score_rows(
                            train_rows, top_k=top_k
                        ),
                        "metrics": evaluate_score_rows(test_rows, top_k=top_k),
                    }
                )
            walk_forward[horizon] = fold_results

        score_results[score_name] = {
            "horizons": horizon_results,
            "score_health": _score_health(development_samples, score_name),
            "ablation": _ablation_results(
                development_samples,
                score_name,
                dataset["horizons"],
                top_k,
            ),
            "walk_forward": walk_forward,
        }

    report = {
        "schema_version": "sector_score_pit_validation.v1",
        "artifact_status": artifact_status,
        "mode": "paper_shadow_research",
        "evidence_classification": (
            "retrospective_record_date_slice_with_unversioned_current_sector_universe"
        ),
        "strict_pit_eligible": False,
        "sector_type": sector_type,
        "parameters": {
            "start_date": start_date,
            "end_date": end_date,
            "trend_window": trend_window,
            "horizons": dataset["horizons"],
            "top_k": top_k,
            "holdout_days": holdout_days,
            "fold_count": fold_count,
            "purge_days": effective_purge,
            "embargo_days": embargo_days,
            "artifact_status": artifact_status,
        },
        "source_manifest": dataset["source_manifest"],
        "coverage": {
            "labelable_date_count": len(dataset["labelable_dates"]),
            "labelable_start_date": (
                dataset["labelable_dates"][0] if dataset["labelable_dates"] else None
            ),
            "labelable_end_date": (
                dataset["labelable_dates"][-1] if dataset["labelable_dates"] else None
            ),
            "development_date_count": len(dataset["development_dates"]),
            "development_start_date": (
                dataset["development_dates"][0] if dataset["development_dates"] else None
            ),
            "development_end_date": (
                dataset["development_dates"][-1] if dataset["development_dates"] else None
            ),
            "boundary_purged_date_count": len(
                dataset["purged_development_dates"]
            ),
            "boundary_purged_dates": dataset["purged_development_dates"],
            "sample_count": len(dataset["samples"]),
            "development_sample_count": len(development_samples),
            "date_sector_counts": dataset["date_sector_counts"],
            "scoring_date_sector_counts": dataset["scoring_date_sector_counts"],
        },
        "provenance_audit": dataset["provenance_audit"],
        "holdout": dataset["holdout"],
        "score_results": score_results,
        "shadow_candidates": _evaluate_shadow_candidates(
            development_samples,
            dataset["horizons"],
            folds,
            top_k,
            score_results,
        ),
        "promotion_gate": {
            "promotion_allowed": False,
            "reason": (
                "prospective_holdout_not_available"
                if dataset["holdout"]["status"] == "observed_evaluation_tail"
                else "no_prospective_holdout_configured"
            ),
            "blocking_reasons": [
                "prospective_holdout_not_available",
                "historical_sector_universe_not_versioned",
            ],
            "strict_pit_eligible": False,
            "live_trading_ready": False,
        },
        "disclaimer": (
            "Paper/shadow research only. No broker connection and no live order instruction."
        ),
    }
    _assert_strict_json(report)
    return report


def write_validation_report(report: dict[str, Any], path: str | Path) -> None:
    """Write a report with strict JSON semantics."""
    _assert_strict_json(report)
    output = Path(path)
    write_strict_json_atomic(output, report)


def _load_histories(
    history_root: str | Path,
    sector_type: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    root = Path(history_root).resolve()
    sector_root = root / sector_type
    if not sector_root.is_dir():
        raise FileNotFoundError(f"sector history directory not found: {sector_root}")

    histories = {}
    sector_names: set[str] = set()
    documents = []
    for path in sorted(sector_root.glob("*.json"), key=lambda item: item.name):
        raw = path.read_bytes()
        payload = loads_strict_json(raw.decode("utf-8-sig"), context=str(path))
        if not isinstance(payload, dict):
            raise ValueError(f"sector history document must be a JSON object: {path}")
        name = str(payload.get("sector_name") or path.stem).strip()
        if not name:
            raise ValueError(f"sector history name is missing: {path}")
        if name in sector_names:
            raise ValueError(f"duplicate sector name: {name}")
        sector_names.add(name)
        sector_id = str(payload.get("sector_code") or f"pit_{sector_type}_{name}")
        if sector_id in histories:
            raise ValueError(f"duplicate sector id: {sector_id}")
        records = []
        seen_dates = set()
        for raw_record in payload.get("records") or []:
            record_date = raw_record.get("日期", raw_record.get("date"))
            parsed_date = _parse_iso_date(record_date, "source date").isoformat()
            if parsed_date in seen_dates:
                raise ValueError(f"duplicate source date: {parsed_date}")
            seen_dates.add(parsed_date)
            close = _required_finite(raw_record.get("收盘价", raw_record.get("close")), "close")
            turnover = _required_finite(
                raw_record.get("成交额", raw_record.get("turnover", 0.0)),
                "turnover",
            )
            if close <= 0:
                raise ValueError("source close must be positive")
            if turnover < 0:
                raise ValueError("source turnover must be non-negative")
            records.append(
                {"date": parsed_date, "close": close, "turnover": turnover}
            )
        records.sort(key=lambda item: item["date"])
        if not records:
            raise ValueError(
                f"sector history document must contain at least one record: {path}"
            )
        histories[sector_id] = {
            "sector_id": sector_id,
            "name": str(name),
            "source": str(payload.get("source") or "sector_history"),
            "records": records,
            "index_by_date": {
                record["date"]: index for index, record in enumerate(records)
            },
        }
        documents.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "record_count": len(records),
                "first_date": records[0]["date"],
                "last_date": records[-1]["date"],
            }
        )
    if len(histories) < 2:
        raise ValueError("at least two sector histories are required")
    manifest_payload = json.dumps(
        documents, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return histories, {
        "root": str(root),
        "document_count": len(documents),
        "documents": documents,
        "manifest_sha256": hashlib.sha256(manifest_payload).hexdigest(),
        "universe_vintage_status": "not_point_in_time_versioned",
        "strict_pit_eligible": False,
        "universe_vintage_limitation": (
            "current sector file set is projected backward because dated universe "
            "membership snapshots are unavailable"
        ),
    }


def _labelable_sector_count(
    histories: dict[str, dict[str, Any]],
    as_of_date: str,
    horizons: Sequence[int],
    calendar_dates: Sequence[str],
) -> int:
    positions = {value: index for index, value in enumerate(calendar_dates)}
    source_position = positions.get(as_of_date)
    if source_position is None:
        return 0
    target_dates = [
        calendar_dates[source_position + horizon]
        for horizon in horizons
        if source_position + horizon < len(calendar_dates)
    ]
    if len(target_dates) != len(horizons):
        return 0
    count = 0
    for history in histories.values():
        if as_of_date in history["index_by_date"] and all(
            target_date in history["index_by_date"] for target_date in target_dates
        ):
            count += 1
    return count


def _score_health(
    samples: Sequence[dict[str, Any]],
    score_name: str,
) -> dict[str, Any]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for sample in samples:
        value = _finite_or_none(sample.get(score_name))
        if value is not None:
            grouped[sample["as_of_date"]].append(value)
    all_values = [value for values in grouped.values() for value in values]
    tied_samples = 0
    constant_dates = 0
    for values in grouped.values():
        counts = Counter(round(value, 8) for value in values)
        tied_samples += sum(count for count in counts.values() if count > 1)
        constant_dates += len(counts) <= 1
    cap_key = (
        "trend_cap_applied"
        if score_name == "trend_continuation_score"
        else "burst_cap_applied"
        if score_name == "short_term_burst_score"
        else None
    )
    capped = (
        sum(bool(sample["cap_metadata"].get(cap_key)) for sample in samples)
        if cap_key
        else 0
    )
    return {
        "date_count": len(grouped),
        "sample_count": len(all_values),
        "unique_value_count": len(set(round(value, 8) for value in all_values)),
        "unique_value_ratio": _rounded_ratio(
            len(set(round(value, 8) for value in all_values)), len(all_values)
        ),
        "constant_date_rate": _rounded_ratio(constant_dates, len(grouped)),
        "tied_sample_rate": _rounded_ratio(tied_samples, len(all_values)),
        "cap_rate": _rounded_ratio(capped, len(samples)),
    }


def _pit_feature_inputs(
    history: dict[str, Any],
    source_index: int,
    metrics: dict[str, Any],
    trend_window: int,
) -> dict[str, Any]:
    returns = list(metrics.get("recent_returns") or [])
    source_records = history["records"]
    current_record = source_records[source_index]
    recent_turnovers = [
        item["turnover"]
        for item in source_records[max(0, source_index - 4) : source_index + 1]
    ]
    turnover_median = median(recent_turnovers) if recent_turnovers else 0.0
    current_turnover = current_record["turnover"]
    technical_window_complete = source_index >= 20
    trailing_turnovers = (
        [
            item["turnover"]
            for item in source_records[source_index - 19 : source_index + 1]
        ]
        if technical_window_complete
        else []
    )
    trailing_turnover_median = (
        median(trailing_turnovers) if trailing_turnovers else 0.0
    )
    turnover_ratio_20d = (
        current_turnover / trailing_turnover_median
        if trailing_turnover_median > 0
        else None
    )
    one_day_return = returns[-1] if returns else None
    five_day_return = _compound_returns(returns[-5:])
    trailing_closes = (
        [
            item["close"]
            for item in source_records[source_index - 19 : source_index + 1]
        ]
        if technical_window_complete
        else []
    )
    prior_closes = (
        [
            item["close"]
            for item in source_records[source_index - 20 : source_index]
        ]
        if technical_window_complete
        else []
    )
    trailing_high = max(trailing_closes) if trailing_closes else None
    drawdown_from_20d_high = (
        (current_record["close"] / trailing_high - 1.0) * 100.0
        if trailing_high and trailing_high > 0
        else None
    )
    effective_breakout_20d = (
        1.0
        if technical_window_complete
        and current_record["close"] > max(prior_closes)
        and _finite_or_none(one_day_return) is not None
        and float(one_day_return) > 0.0
        else 0.0
    )
    breakout_distance_pct = (
        (current_record["close"] / max(prior_closes) - 1.0) * 100.0
        if technical_window_complete and prior_closes
        else None
    )
    continuous_breakout_quality_20d = (
        _clip_scale(breakout_distance_pct, -2.0, 2.0)
        if breakout_distance_pct is not None
        else None
    )
    healthy_volume_confirmation = (
        _healthy_volume_confirmation(one_day_return, turnover_ratio_20d)
        if technical_window_complete
        else None
    )
    volume_exhaustion_risk = (
        _volume_exhaustion_risk(
            one_day_return,
            five_day_return,
            turnover_ratio_20d,
        )
        if technical_window_complete
        else None
    )
    price_volume_efficiency = (
        _price_volume_efficiency(one_day_return, turnover_ratio_20d)
        if technical_window_complete
        else None
    )
    return {
        "feature_max_date": current_record["date"],
        "one_day_return": one_day_return,
        "five_day_return": five_day_return,
        "trend_window_return": _compound_returns(returns[-trend_window:]),
        "persistence_ratio": (
            sum(value > 0 for value in returns[-trend_window:])
            / len(returns[-trend_window:])
            if returns[-trend_window:]
            else None
        ),
        "turnover_ratio_5d": (
            current_turnover / turnover_median if turnover_median > 0 else None
        ),
        "turnover_ratio_20d": turnover_ratio_20d,
        "healthy_volume_confirmation": healthy_volume_confirmation,
        "effective_breakout_20d": (
            effective_breakout_20d if technical_window_complete else None
        ),
        "breakout_distance_pct_20d": breakout_distance_pct,
        "continuous_breakout_quality_20d": continuous_breakout_quality_20d,
        "price_volume_efficiency": price_volume_efficiency,
        "drawdown_from_20d_high": (
            drawdown_from_20d_high if technical_window_complete else None
        ),
        "volume_exhaustion_risk": volume_exhaustion_risk,
        "technical_window_status": (
            "complete_20_session_history"
            if technical_window_complete
            else "insufficient_20_session_history"
        ),
        "history_days": int(metrics.get("history_days") or 0),
    }


def _add_cross_sectional_technical_inputs(
    feature_inputs: Iterable[dict[str, Any]],
) -> None:
    """Add same-date relative ranks without consulting labels or later sessions."""
    rows = list(feature_inputs)
    for source_key, target_key in (
        ("trend_window_return", "relative_strength_percentile"),
        ("five_day_return", "five_day_momentum_percentile"),
    ):
        finite_values = [
            float(value)
            for row in rows
            if (value := _finite_or_none(row.get(source_key))) is not None
        ]
        for row in rows:
            value = _finite_or_none(row.get(source_key))
            row[target_key] = (
                _cross_sectional_percentile(float(value), finite_values)
                if value is not None
                else None
            )

    one_day_values = [
        float(value)
        for row in rows
        if (value := _finite_or_none(row.get("one_day_return"))) is not None
    ]
    market_median = median(one_day_values) if one_day_values else None
    positive_ratio = (
        sum(value > 0.0 for value in one_day_values) / len(one_day_values)
        if one_day_values
        else None
    )
    if market_median is None or positive_ratio is None:
        market_regime = "neutral"
    elif market_median >= 0.5 and positive_ratio >= 0.6:
        market_regime = "risk_on"
    elif market_median <= -0.5 or positive_ratio <= 0.4:
        market_regime = "risk_off"
    else:
        market_regime = "neutral"
    regime_factor = {"risk_on": 1.0, "neutral": 0.95, "risk_off": 0.85}[
        market_regime
    ]
    for row in rows:
        row["market_cross_section_median_return"] = market_median
        row["market_cross_section_positive_ratio"] = positive_ratio
        row["market_regime"] = market_regime
        row["market_regime_factor"] = regime_factor


def _cross_sectional_percentile(value: float, values: Sequence[float]) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return 0.5
    lower = sum(item < value for item in values)
    equal = sum(item == value for item in values)
    return (lower + (equal - 1) / 2.0) / (len(values) - 1)


def _healthy_volume_confirmation(
    one_day_return: Any,
    turnover_ratio_20d: float | None,
) -> float:
    change = _finite_or_none(one_day_return)
    ratio = _finite_or_none(turnover_ratio_20d)
    if change is None or ratio is None or change <= 0.0:
        return 0.0
    price_confirmation = _clip_scale(change, 0.0, 3.0)
    moderate_volume = _clip_scale(ratio, 1.0, 2.0)
    excess_volume_discount = 1.0 - _clip_scale(ratio, 2.0, 3.0)
    return max(0.0, min(1.0, min(price_confirmation, moderate_volume) * excess_volume_discount))


def _price_volume_efficiency(
    one_day_return: Any,
    turnover_ratio_20d: float | None,
) -> float:
    change = _finite_or_none(one_day_return)
    ratio = _finite_or_none(turnover_ratio_20d)
    if change is None or ratio is None or change <= 0.0:
        return 0.0
    return _clip_scale(change / max(ratio, 0.5), 0.0, 3.0)


def _volume_exhaustion_risk(
    one_day_return: Any,
    five_day_return: Any,
    turnover_ratio_20d: float | None,
) -> float:
    change = _finite_or_none(one_day_return)
    five_day = _finite_or_none(five_day_return)
    ratio = _finite_or_none(turnover_ratio_20d)
    if change is None or five_day is None or ratio is None:
        return 0.0
    high_volume = _clip_scale(ratio, 2.0, 3.5)
    stagnation = 1.0 - _clip_scale(abs(change), 0.5, 3.0)
    decline = _clip_scale(-change, 0.0, 3.0)
    overheat = _clip_scale(five_day, 8.0, 16.0)
    return high_volume * max(stagnation, decline, overheat)


def _evaluate_shadow_candidates(
    samples: Sequence[dict[str, Any]],
    horizons: Sequence[str],
    folds: Sequence[dict[str, Any]],
    top_k: int,
    production_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    definitions = {
        "radar_continuous_inputs_v1": {
            "target": "radar_base_score",
            "formula": (
                "30*clip_scale(one_day_return,-5,5) + "
                "30*clip_scale(five_day_return,-10,10) + "
                "20*persistence_ratio + 20*clip_scale(turnover_ratio_5d,0.5,2.0) "
                "- risk_penalty"
            ),
        },
        "radar_technical_evidence_v2": {
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
            "formula": (
                "20*relative_strength_percentile + 25*persistence_ratio + "
                "20*healthy_volume_confirmation + 20*effective_breakout_20d + "
                "15*five_day_momentum_percentile - 8*volume_exhaustion_risk - "
                "7*clip_scale(abs(min(drawdown_from_20d_high,0)),2,12) - risk_penalty"
            ),
            "scope": "same_session_cross_section_and_as_of_history_only",
            "minimum_history_sessions": 21,
            "incomplete_feature_behavior": "excluded_from_candidate_evaluation",
            "volume_exhaustion_risk_definition": {
                "high_volume": "clip_scale(turnover_ratio_20d,2.0,3.5)",
                "stagnation": "1-clip_scale(abs(one_day_return),0.5,3.0)",
                "decline": "clip_scale(-one_day_return,0,3)",
                "overheat": "clip_scale(five_day_return,8,16)",
                "result": "high_volume*max(stagnation,decline,overheat)",
            },
        },
        "radar_technical_evidence_v3": {
            "target": "radar_base_score",
            "weights": {
                "relative_strength_percentile": 20.0,
                "persistence_ratio": 20.0,
                "continuous_breakout_quality_20d": 20.0,
                "price_volume_efficiency": 15.0,
                "healthy_volume_confirmation": 10.0,
                "five_day_momentum_percentile": 15.0,
            },
            "penalties": {
                "volume_exhaustion_risk": 8.0,
                "drawdown_from_20d_high": 7.0,
            },
            "required_features": ["market_regime_factor"],
            "market_regime_calibration": {
                "risk_on": 1.0,
                "neutral": 0.95,
                "risk_off": 0.85,
            },
            "market_regime_definition": {
                "risk_on": "median_return>=0.5 AND positive_ratio>=0.6",
                "risk_off": "median_return<=-0.5 OR positive_ratio<=0.4",
                "neutral": "otherwise",
            },
            "price_volume_efficiency_definition": {
                "raw": "max(one_day_return,0)/max(turnover_ratio_20d,0.5)",
                "scale": "clip_scale(raw,0,3)",
            },
            "volume_exhaustion_risk_definition": {
                "high_volume": "clip_scale(turnover_ratio_20d,2.0,3.5)",
                "stagnation": "1-clip_scale(abs(one_day_return),0.5,3.0)",
                "decline": "clip_scale(-one_day_return,0,3)",
                "overheat": "clip_scale(five_day_return,8,16)",
                "result": "high_volume*max(stagnation,decline,overheat)",
            },
            "formula": (
                "regime_factor*(20*relative_strength_percentile + "
                "20*persistence_ratio + 20*continuous_breakout_quality_20d + "
                "15*price_volume_efficiency + 10*healthy_volume_confirmation + "
                "15*five_day_momentum_percentile) - 8*volume_exhaustion_risk - "
                "7*clip_scale(abs(min(drawdown_from_20d_high,0)),2,12) - risk_penalty"
            ),
            "scope": "same_session_cross_section_and_as_of_history_only",
            "minimum_history_sessions": 21,
            "incomplete_feature_behavior": "excluded_from_candidate_evaluation",
            "constituent_breadth_status": (
                "not_evaluated_historical_data_unavailable"
            ),
        },
        "trend_evidence_balance_v1": {
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
        },
        "burst_momentum_balance_v1": {
            "target": "short_term_burst_score",
            "weights": {
                "radar_today_component": 20.0,
                "one_day_change_component": 25.0,
                "three_day_momentum_component": 25.0,
                "volume_or_heat_component": 10.0,
                "rank_jump_component": 5.0,
                "data_quality_component": 10.0,
            },
        },
    }
    candidates = {}
    for candidate_name, definition in definitions.items():
        eligible_samples = [
            sample
            for sample in samples
            if _candidate_feature_eligible(candidate_name, sample, definition)
        ]
        excluded_samples = len(samples) - len(eligible_samples)
        candidate_folds = folds
        if candidate_name in TECHNICAL_CANDIDATE_NAMES:
            eligible_dates = sorted(
                {sample["as_of_date"] for sample in eligible_samples}
            )
            candidate_folds = (
                build_walk_forward_folds(
                    eligible_dates,
                    fold_count=len(folds),
                    purge_days=folds[0]["purge_days"],
                    embargo_days=folds[0]["embargo_days"],
                )
                if folds
                else []
            )
        scored_rows = []
        for sample in eligible_samples:
            scored_rows.append(
                {
                    "as_of_date": sample["as_of_date"],
                    "score": _shadow_candidate_score(candidate_name, sample, definition),
                    "cap_applied": _candidate_cap_applied(
                        candidate_name, sample, definition
                    ),
                    "sample": sample,
                }
            )
        horizon_results = {}
        walk_forward = {}
        for horizon in horizons:
            rows = [
                {
                    "as_of_date": row["as_of_date"],
                    "score": row["score"],
                    "forward_return": row["sample"]["forward_returns"][horizon],
                }
                for row in scored_rows
            ]
            horizon_results[horizon] = evaluate_score_rows(rows, top_k=top_k)
            walk_forward[horizon] = _candidate_walk_forward(
                rows, candidate_folds, top_k
            )
        candidate_health = _generic_score_health(scored_rows)
        production_result = (
            _candidate_production_baseline(
                eligible_samples,
                definition["target"],
                horizons,
                candidate_folds,
                top_k,
            )
            if candidate_name in TECHNICAL_CANDIDATE_NAMES
            else production_results[definition["target"]]
        )
        candidates[candidate_name] = {
            **definition,
            "feature_eligibility": {
                "total_development_samples": len(samples),
                "eligible_technical_samples": len(eligible_samples),
                "excluded_incomplete_technical_samples": excluded_samples,
            },
            "production_baseline_scope": {
                "method": (
                    "same_eligible_technical_samples"
                    if candidate_name in TECHNICAL_CANDIDATE_NAMES
                    else "all_development_samples"
                ),
                "sample_count": len(eligible_samples),
            },
            "walk_forward_scope": {
                "method": (
                    "eligible_candidate_dates"
                    if candidate_name in TECHNICAL_CANDIDATE_NAMES
                    else "all_development_dates"
                ),
                "date_count": len(
                    {sample["as_of_date"] for sample in eligible_samples}
                ),
                "fold_count": len(candidate_folds),
            },
            "horizons": horizon_results,
            "score_health": candidate_health,
            "walk_forward": walk_forward,
            "factor_ablation": (
                _candidate_factor_ablation_results(
                    candidate_name,
                    definition,
                    scored_rows,
                    horizons,
                    top_k,
                )
                if candidate_name in TECHNICAL_CANDIDATE_NAMES
                else {}
            ),
            "regime_attribution": (
                _candidate_regime_attribution(scored_rows, horizons, top_k)
                if candidate_name in TECHNICAL_CANDIDATE_NAMES
                else {}
            ),
            "development_gate": _development_candidate_gate(
                horizon_results,
                walk_forward,
                scored_rows,
                candidate_health=candidate_health,
                production_result=production_result,
            ),
        }
    return {
        "status": "development_challengers_only",
        "holdout_labels_used": False,
        "definitions_locked_before_holdout_evaluation": False,
        "eligible_for_oos_claim": False,
        "candidates": candidates,
    }


def _candidate_feature_eligible(
    candidate_name: str,
    sample: dict[str, Any],
    definition: dict[str, Any],
) -> bool:
    if candidate_name not in TECHNICAL_CANDIDATE_NAMES:
        return True
    inputs = sample.get("feature_inputs") or {}
    required_keys = (
        tuple(definition["weights"])
        + tuple(definition["penalties"])
        + tuple(definition.get("required_features") or ())
    )
    return (
        inputs.get("technical_window_status") == "complete_20_session_history"
        and all(_finite_or_none(inputs.get(key)) is not None for key in required_keys)
    )


def _candidate_production_baseline(
    samples: Sequence[dict[str, Any]],
    score_name: str,
    horizons: Sequence[str],
    folds: Sequence[dict[str, Any]],
    top_k: int,
) -> dict[str, Any]:
    """Evaluate production only on the exact challenger-eligible sample scope."""
    scored_rows = [
        {
            "as_of_date": sample["as_of_date"],
            "score": sample[score_name],
            "cap_applied": False,
            "sample": sample,
        }
        for sample in samples
    ]
    horizon_results = {}
    walk_forward = {}
    for horizon in horizons:
        rows = [
            {
                "as_of_date": row["as_of_date"],
                "score": row["score"],
                "forward_return": row["sample"]["forward_returns"][horizon],
            }
            for row in scored_rows
        ]
        horizon_results[horizon] = evaluate_score_rows(rows, top_k=top_k)
        walk_forward[horizon] = _candidate_walk_forward(rows, folds, top_k)
    return {
        "horizons": horizon_results,
        "walk_forward": walk_forward,
        "score_health": _generic_score_health(scored_rows),
    }


def _candidate_factor_ablation_results(
    candidate_name: str,
    definition: dict[str, Any],
    scored_rows: Sequence[dict[str, Any]],
    horizons: Sequence[str],
    top_k: int,
) -> dict[str, Any]:
    components = list(definition["weights"]) + list(definition["penalties"])
    components.append("production_risk_penalty")
    if candidate_name == "radar_technical_evidence_v3":
        components.append("market_regime_calibration")
    variants = {}
    for component in components:
        rows_by_horizon = {horizon: [] for horizon in horizons}
        for row in scored_rows:
            sample = row["sample"]
            inputs = dict(sample["feature_inputs"])
            if component == "market_regime_calibration":
                inputs["market_regime"] = "risk_on"
                inputs["market_regime_factor"] = 1.0
                ablated_sample = {**sample, "feature_inputs": inputs}
                method = (
                    "neutralize_market_regime_factor_to_1_and_recompute_candidate"
                )
            elif component == "production_risk_penalty":
                score_breakdowns = dict(sample["score_breakdowns"])
                score_breakdowns["radar_base_score"] = {
                    **score_breakdowns["radar_base_score"],
                    "risk_penalty": 0.0,
                }
                ablated_sample = {
                    **sample,
                    "feature_inputs": inputs,
                    "score_breakdowns": score_breakdowns,
                }
                method = "zero_production_risk_penalty_and_recompute_candidate"
            else:
                inputs[component] = 0.0
                ablated_sample = {**sample, "feature_inputs": inputs}
                method = "zero_component_and_recompute_candidate"
            ablated_score = _shadow_candidate_score(
                candidate_name,
                ablated_sample,
                definition,
            )
            for horizon in horizons:
                rows_by_horizon[horizon].append(
                    {
                        "as_of_date": row["as_of_date"],
                        "score": ablated_score,
                        "forward_return": sample["forward_returns"][horizon],
                    }
                )
        variants[component] = {
            "method": method,
            "horizons": {
                horizon: evaluate_score_rows(rows, top_k=top_k)
                for horizon, rows in rows_by_horizon.items()
            },
        }
    return variants


def _candidate_regime_attribution(
    scored_rows: Sequence[dict[str, Any]],
    horizons: Sequence[str],
    top_k: int,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in scored_rows:
        regime = str(
            row["sample"].get("feature_inputs", {}).get("market_regime")
            or "unknown"
        )
        grouped[regime].append(row)
    return {
        regime: {
            "date_count": len({row["as_of_date"] for row in rows}),
            "sample_count": len(rows),
            "horizons": {
                horizon: evaluate_score_rows(
                    [
                        {
                            "as_of_date": row["as_of_date"],
                            "score": row["score"],
                            "forward_return": row["sample"]["forward_returns"][
                                horizon
                            ],
                        }
                        for row in rows
                    ],
                    top_k=top_k,
                )
                for horizon in horizons
            },
        }
        for regime, rows in sorted(grouped.items())
    }


def _shadow_candidate_score(
    candidate_name: str,
    sample: dict[str, Any],
    definition: dict[str, Any],
) -> float:
    if candidate_name == "radar_continuous_inputs_v1":
        inputs = sample["feature_inputs"]
        required = (
            inputs.get("one_day_return"),
            inputs.get("five_day_return"),
            inputs.get("persistence_ratio"),
            inputs.get("turnover_ratio_5d"),
        )
        if any(_finite_or_none(value) is None for value in required):
            return sample["radar_base_score"]
        penalty = (
            _finite_or_none(
                sample["score_breakdowns"]["radar_base_score"].get("risk_penalty")
            )
            or 0.0
        )
        value = (
            30.0 * _clip_scale(float(required[0]), -5.0, 5.0)
            + 30.0 * _clip_scale(float(required[1]), -10.0, 10.0)
            + 20.0 * float(required[2])
            + 20.0 * _clip_scale(float(required[3]), 0.5, 2.0)
            - penalty
        )
        return max(0.0, min(100.0, value))

    if candidate_name in TECHNICAL_CANDIDATE_NAMES:
        inputs = sample["feature_inputs"]
        required_keys = tuple(definition["weights"])
        required = tuple(inputs.get(key) for key in required_keys)
        if any(_finite_or_none(value) is None for value in required):
            return 0.0
        value = sum(
            float(inputs[key]) * float(weight)
            for key, weight in definition["weights"].items()
        )
        if candidate_name == "radar_technical_evidence_v3":
            regime = str(inputs.get("market_regime") or "neutral")
            expected_factor = float(
                definition["market_regime_calibration"].get(regime, 0.95)
            )
            actual_factor = _finite_or_none(inputs.get("market_regime_factor"))
            if actual_factor is None or abs(actual_factor - expected_factor) > 1e-12:
                return 0.0
            value *= actual_factor
        exhaustion = _finite_or_none(inputs.get("volume_exhaustion_risk")) or 0.0
        drawdown = _finite_or_none(inputs.get("drawdown_from_20d_high")) or 0.0
        value -= exhaustion * float(definition["penalties"]["volume_exhaustion_risk"])
        value -= _clip_scale(abs(min(drawdown, 0.0)), 2.0, 12.0) * float(
            definition["penalties"]["drawdown_from_20d_high"]
        )
        penalty = (
            _finite_or_none(
                sample["score_breakdowns"]["radar_base_score"].get("risk_penalty")
            )
            or 0.0
        )
        return max(0.0, min(100.0, value - penalty))

    target = definition["target"]
    breakdown = sample["score_breakdowns"][target]
    baseline_maxima = (
        {
            "radar_score_component": 25.0,
            "momentum_component": 20.0,
            "relative_strength_component": 15.0,
            "persistence_component": 15.0,
            "drawdown_component": 10.0,
            "volatility_component": 10.0,
            "data_quality_component": 5.0,
        }
        if target == "trend_continuation_score"
        else {
            "radar_today_component": 30.0,
            "one_day_change_component": 20.0,
            "three_day_momentum_component": 15.0,
            "volume_or_heat_component": 10.0,
            "rank_jump_component": 10.0,
            "data_quality_component": 10.0,
        }
    )
    value = 0.0
    for component, weight in definition["weights"].items():
        component_value = _finite_or_none(breakdown.get(component)) or 0.0
        value += component_value / baseline_maxima[component] * weight
    penalty_key = (
        "burst_risk_penalty"
        if target == "short_term_burst_score"
        else "risk_penalty"
    )
    value -= _finite_or_none(breakdown.get(penalty_key)) or 0.0
    value = max(0.0, min(100.0, value))
    if target == "trend_continuation_score":
        return apply_insufficient_history_cap(
            value,
            str(sample.get("trend_window_status") or ""),
            float(sample.get("history_coverage_ratio") or 0.0),
        )
    history_days = int((sample.get("feature_inputs") or {}).get("history_days") or 0)
    adjusted, _applied, _reason = apply_burst_insufficient_history_cap(
        value,
        history_days=history_days,
        actual_history_days=history_days,
    )
    return adjusted


def _candidate_cap_applied(
    candidate_name: str,
    sample: dict[str, Any],
    definition: dict[str, Any],
) -> bool:
    if candidate_name not in {
        "trend_evidence_balance_v1",
        "burst_momentum_balance_v1",
    }:
        return False
    adjusted = _shadow_candidate_score(candidate_name, sample, definition)
    uncapped_sample = dict(sample)
    uncapped_sample["trend_window_status"] = "ok"
    uncapped_sample["history_coverage_ratio"] = 1.0
    uncapped_sample["feature_inputs"] = {
        **(sample.get("feature_inputs") or {}),
        "history_days": max(
            3,
            int((sample.get("feature_inputs") or {}).get("history_days") or 0),
        ),
    }
    uncapped = _shadow_candidate_score(candidate_name, uncapped_sample, definition)
    return adjusted < uncapped


def _candidate_walk_forward(
    rows: Sequence[dict[str, Any]],
    folds: Sequence[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    output = []
    for fold in folds:
        train_set = set(fold["train_dates"])
        test_set = set(fold["test_dates"])
        output.append(
            {
                "fold": fold["fold"],
                "train_start": fold["train_dates"][0],
                "train_end": fold["train_dates"][-1],
                "test_start": fold["test_dates"][0],
                "test_end": fold["test_dates"][-1],
                "train_date_count": len(fold["train_dates"]),
                "test_date_count": len(fold["test_dates"]),
                "purge_days": fold["purge_days"],
                "embargo_days": fold["embargo_days"],
                "train_metrics": evaluate_score_rows(
                    [row for row in rows if row["as_of_date"] in train_set],
                    top_k=top_k,
                ),
                "metrics": evaluate_score_rows(
                    [row for row in rows if row["as_of_date"] in test_set],
                    top_k=top_k,
                ),
            }
        )
    return output


def _generic_score_health(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        value = _finite_or_none(row.get("score"))
        if value is not None:
            grouped[row["as_of_date"]].append(value)
    values = [value for daily_values in grouped.values() for value in daily_values]
    tied = 0
    constant_dates = 0
    for daily_values in grouped.values():
        counts = Counter(round(value, 8) for value in daily_values)
        tied += sum(count for count in counts.values() if count > 1)
        constant_dates += len(counts) <= 1
    return {
        "date_count": len(grouped),
        "sample_count": len(values),
        "unique_value_count": len(set(round(value, 8) for value in values)),
        "constant_date_rate": _rounded_ratio(constant_dates, len(grouped)),
        "tied_sample_rate": _rounded_ratio(tied, len(values)),
        "cap_rate": _rounded_ratio(
            sum(bool(row.get("cap_applied")) for row in rows), len(rows)
        ),
    }


def _development_candidate_gate(
    horizon_results: dict[str, dict[str, Any]],
    walk_forward: dict[str, list[dict[str, Any]]],
    rows: Sequence[dict[str, Any]],
    *,
    candidate_health: dict[str, Any],
    production_result: dict[str, Any],
) -> dict[str, Any]:
    primary_horizon = "3d" if "3d" in horizon_results else next(iter(horizon_results))
    metrics = horizon_results[primary_horizon]
    folds = walk_forward[primary_horizon]
    required_horizons = {"1d", "3d", "5d"}
    all_horizon_folds = [
        fold
        for horizon_folds in walk_forward.values()
        for fold in horizon_folds
    ]
    date_counts = Counter(row["as_of_date"] for row in rows)
    production_horizons = production_result["horizons"]
    production_walk_forward = production_result["walk_forward"]
    production_health = production_result["score_health"]
    horizon_comparison = {
        horizon: _candidate_metric_comparison(
            candidate_metrics,
            production_horizons.get(horizon, {}),
        )
        for horizon, candidate_metrics in horizon_results.items()
    }
    fold_comparison = {
        horizon: _candidate_fold_comparison(
            candidate_folds,
            production_walk_forward.get(horizon, []),
        )
        for horizon, candidate_folds in walk_forward.items()
    }
    checks = {
        "required_1d_3d_5d_horizons_present": (
            set(horizon_results) == required_horizons
            and set(walk_forward) == required_horizons
            and set(production_horizons) == required_horizons
            and set(production_walk_forward) == required_horizons
        ),
        "at_least_20_sectors_per_date": bool(date_counts)
        and min(date_counts.values()) >= 20,
        "mean_daily_rank_ic_at_least_0_02": (
            metrics["mean_daily_rank_ic"] is not None
            and metrics["mean_daily_rank_ic"] >= 0.02
        ),
        "top_bottom_spread_positive": (
            metrics["top_bottom_spread"] is not None
            and metrics["top_bottom_spread"] > 0
        ),
        "every_fold_rank_ic_positive": bool(folds)
        and all(
            fold["metrics"]["mean_daily_rank_ic"] is not None
            and fold["metrics"]["mean_daily_rank_ic"] > 0
            for fold in folds
        ),
        "every_fold_top_bottom_spread_positive": bool(folds)
        and all(
            fold["metrics"]["top_bottom_spread"] is not None
            and fold["metrics"]["top_bottom_spread"] > 0
            for fold in folds
        ),
        "every_fold_has_at_least_10_dates": bool(folds)
        and all(fold["metrics"]["date_count"] >= 10 for fold in folds),
        "every_fold_train_has_at_least_10_dates": bool(folds)
        and all(
            fold["train_metrics"]["date_count"] >= 10 for fold in folds
        ),
        "every_fold_train_rank_ic_positive": bool(folds)
        and all(
            fold["train_metrics"]["mean_daily_rank_ic"] is not None
            and fold["train_metrics"]["mean_daily_rank_ic"] > 0
            for fold in folds
        ),
        "every_fold_train_top_bottom_spread_positive": bool(folds)
        and all(
            fold["train_metrics"]["top_bottom_spread"] is not None
            and fold["train_metrics"]["top_bottom_spread"] > 0
            for fold in folds
        ),
        "all_horizon_train_folds_rank_ic_positive": bool(all_horizon_folds)
        and all(
            fold["train_metrics"]["mean_daily_rank_ic"] is not None
            and fold["train_metrics"]["mean_daily_rank_ic"] > 0
            for fold in all_horizon_folds
        ),
        "all_horizon_train_folds_top_bottom_spread_positive": bool(
            all_horizon_folds
        )
        and all(
            fold["train_metrics"]["top_bottom_spread"] is not None
            and fold["train_metrics"]["top_bottom_spread"] > 0
            for fold in all_horizon_folds
        ),
        "all_horizon_test_folds_rank_ic_positive": bool(all_horizon_folds)
        and all(
            fold["metrics"]["mean_daily_rank_ic"] is not None
            and fold["metrics"]["mean_daily_rank_ic"] > 0
            for fold in all_horizon_folds
        ),
        "all_horizon_test_folds_top_bottom_spread_positive": bool(
            all_horizon_folds
        )
        and all(
            fold["metrics"]["top_bottom_spread"] is not None
            and fold["metrics"]["top_bottom_spread"] > 0
            for fold in all_horizon_folds
        ),
        "all_horizon_folds_have_at_least_10_dates": bool(all_horizon_folds)
        and all(fold["metrics"]["date_count"] >= 10 for fold in all_horizon_folds),
        "all_horizon_train_folds_have_at_least_10_dates": bool(
            all_horizon_folds
        )
        and all(
            fold["train_metrics"]["date_count"] >= 10
            for fold in all_horizon_folds
        ),
        "all_horizons_rank_ic_positive": bool(horizon_results)
        and all(
            value["mean_daily_rank_ic"] is not None
            and value["mean_daily_rank_ic"] > 0
            for value in horizon_results.values()
        ),
        "all_horizons_top_bottom_spread_positive": bool(horizon_results)
        and all(
            value["top_bottom_spread"] is not None
            and value["top_bottom_spread"] > 0
            for value in horizon_results.values()
        ),
        "all_horizons_not_worse_than_production": bool(horizon_comparison)
        and all(value["passed"] for value in horizon_comparison.values()),
        "all_walk_forward_folds_not_worse_than_production": bool(fold_comparison)
        and all(
            comparison["passed"] for comparison in fold_comparison.values()
        ),
        "candidate_tie_rate_not_worse_than_production": _rate_not_higher(
            candidate_health.get("tied_sample_rate"),
            production_health.get("tied_sample_rate"),
        ),
        "candidate_constant_rate_not_worse_than_production": _rate_not_higher(
            candidate_health.get("constant_date_rate"),
            production_health.get("constant_date_rate"),
        ),
        "candidate_cap_rate_not_worse_than_production": _rate_not_higher(
            candidate_health.get("cap_rate"),
            production_health.get("cap_rate"),
        ),
    }
    return {
        "primary_horizon": primary_horizon,
        "passed": all(checks.values()),
        "checks": checks,
        "production_baseline_comparison": {
            "horizons": horizon_comparison,
            "walk_forward": fold_comparison,
            "candidate_score_health": candidate_health,
            "production_score_health": production_health,
        },
        "decision": (
            "eligible_for_locked_holdout_evaluation"
            if all(checks.values())
            else "remain_shadow_development"
        ),
    }


def _candidate_metric_comparison(
    candidate: dict[str, Any],
    production: dict[str, Any],
) -> dict[str, Any]:
    comparisons = {
        key: _metric_not_lower(candidate.get(key), production.get(key))
        for key in ("mean_daily_rank_ic", "top_bottom_spread")
    }
    return {
        "passed": all(comparisons.values()),
        "checks": comparisons,
        "candidate_mean_daily_rank_ic": candidate.get("mean_daily_rank_ic"),
        "production_mean_daily_rank_ic": production.get("mean_daily_rank_ic"),
        "candidate_top_bottom_spread": candidate.get("top_bottom_spread"),
        "production_top_bottom_spread": production.get("top_bottom_spread"),
    }


def _candidate_fold_comparison(
    candidate_folds: Sequence[dict[str, Any]],
    production_folds: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    production_by_fold = {fold["fold"]: fold for fold in production_folds}
    comparisons = []
    for candidate_fold in candidate_folds:
        production_fold = production_by_fold.get(candidate_fold["fold"])
        if production_fold is None:
            comparisons.append(
                {
                    "fold": candidate_fold["fold"],
                    "passed": False,
                    "train": {"passed": False, "reason": "missing_production_fold"},
                    "test": {"passed": False, "reason": "missing_production_fold"},
                }
            )
            continue
        train_comparison = _candidate_metric_comparison(
            candidate_fold["train_metrics"], production_fold["train_metrics"]
        )
        test_comparison = _candidate_metric_comparison(
            candidate_fold["metrics"], production_fold["metrics"]
        )
        comparisons.append(
            {
                "fold": candidate_fold["fold"],
                "passed": train_comparison["passed"] and test_comparison["passed"],
                "train": train_comparison,
                "test": test_comparison,
            }
        )
    return {
        "passed": bool(comparisons)
        and len(comparisons) == len(production_folds)
        and all(item["passed"] for item in comparisons),
        "folds": comparisons,
    }


def _metric_not_lower(candidate: Any, production: Any) -> bool:
    candidate_value = _finite_or_none(candidate)
    production_value = _finite_or_none(production)
    return (
        candidate_value is not None
        and production_value is not None
        and candidate_value + 1e-12 >= production_value
    )


def _rate_not_higher(candidate: Any, production: Any) -> bool:
    candidate_value = _finite_or_none(candidate)
    production_value = _finite_or_none(production)
    return (
        candidate_value is not None
        and production_value is not None
        and candidate_value <= production_value + 1e-12
    )


def _ablation_results(
    samples: Sequence[dict[str, Any]],
    score_name: str,
    horizons: Sequence[str],
    top_k: int,
) -> dict[str, Any]:
    variants = {}
    for component in ABLATION_COMPONENTS[score_name]:
        by_horizon = {}
        for horizon in horizons:
            rows = []
            for sample in samples:
                breakdown = sample["score_breakdowns"][score_name]
                component_value = _finite_or_none(breakdown.get(component))
                if component_value is None:
                    continue
                ablated = _ablated_score(sample, score_name, component_value)
                rows.append(
                    {
                        "as_of_date": sample["as_of_date"],
                        "score": ablated,
                        "forward_return": sample["forward_returns"][horizon],
                    }
                )
            by_horizon[horizon] = evaluate_score_rows(rows, top_k=top_k)
        variants[component] = {
            "method": "remove_one_component_recompute_from_breakdown",
            "horizons": by_horizon,
        }
    return variants


def _ablated_score(
    sample: dict[str, Any],
    score_name: str,
    component_value: float,
) -> float:
    breakdown = sample["score_breakdowns"][score_name]
    positive_score = _finite_or_none(breakdown.get("positive_score"))
    if positive_score is None:
        positive_score = sample[score_name]
    if score_name == "short_term_burst_score":
        penalty = _finite_or_none(breakdown.get("burst_risk_penalty")) or 0.0
    else:
        penalty = _finite_or_none(breakdown.get("risk_penalty")) or 0.0
    value = max(0.0, min(100.0, positive_score - component_value - penalty))
    cap_key = (
        "trend_cap_applied"
        if score_name == "trend_continuation_score"
        else "burst_cap_applied"
        if score_name == "short_term_burst_score"
        else None
    )
    if cap_key and sample["cap_metadata"].get(cap_key):
        value = min(value, sample[score_name])
    return value


def _select_score_tail(
    pairs: Sequence[tuple[float, float]],
    top_k: int,
    *,
    highest: bool,
) -> list[tuple[float, float]]:
    ordered = sorted(pairs, key=lambda pair: pair[0], reverse=highest)
    boundary_index = min(top_k, len(ordered)) - 1
    boundary_score = ordered[boundary_index][0]
    if highest:
        return [pair for pair in ordered if pair[0] >= boundary_score]
    return [pair for pair in ordered if pair[0] <= boundary_score]


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
    x_variance = sum((value - x_mean) ** 2 for value in x_ranks)
    y_variance = sum((value - y_mean) ** 2 for value in y_ranks)
    denominator = math.sqrt(x_variance * y_variance)
    if denominator == 0:
        return None
    return numerator / denominator


def _average_ranks(values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(indexed):
        end = start + 1
        while end < len(indexed) and indexed[end][1] == indexed[start][1]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        for position in range(start, end):
            ranks[indexed[position][0]] = average_rank
        start = end
    return ranks


def _split_evenly(values: Sequence[str], count: int) -> list[list[str]]:
    base, remainder = divmod(len(values), count)
    chunks = []
    cursor = 0
    for index in range(count):
        size = base + (1 if index < remainder else 0)
        chunks.append(list(values[cursor : cursor + size]))
        cursor += size
    return chunks


def _compound_returns(values: Sequence[float]) -> float | None:
    if not values:
        return None
    wealth = 1.0
    for value in values:
        finite = _finite_or_none(value)
        if finite is None:
            return None
        wealth *= 1.0 + finite / 100.0
    return (wealth - 1.0) * 100.0


def _clip_scale(value: float, lower: float, upper: float) -> float:
    if upper <= lower:
        raise ValueError("upper must be greater than lower")
    return (min(max(value, lower), upper) - lower) / (upper - lower)


def _normalize_horizons(horizons: Sequence[int]) -> tuple[int, ...]:
    values = tuple(sorted(set(int(value) for value in horizons)))
    if not values or any(value <= 0 for value in values):
        raise ValueError("horizons must contain positive integers")
    return values


def _parse_iso_date(value: Any, field: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid {field}: {value}") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"invalid {field}: {value}")
    return parsed


def _required_finite(value: Any, field: str) -> float:
    result = _finite_or_none(value)
    if result is None:
        raise ValueError(f"{field} must be finite")
    return result


def _finite_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _rounded_mean(values: Sequence[float]) -> float | None:
    return round(mean(values), 6) if values else None


def _rounded_median(values: Sequence[float]) -> float | None:
    return round(median(values), 6) if values else None


def _rounded_ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _sample_manifest_sha(samples: Sequence[dict[str, Any]]) -> str:
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
    payload = json.dumps(
        rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _assert_strict_json(payload: dict[str, Any]) -> None:
    json.dumps(payload, ensure_ascii=False, allow_nan=False)
