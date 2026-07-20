"""Preparation-only contracts for an independent industry-sector OOS window."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256


OOS_SAFETY_FLAGS = (
    "strict_pit_eligible",
    "eligible_for_oos_claim",
    "promotion_allowed",
    "live_trading_allowed",
    "formal_predictor_compatible",
)

STRICT_SPLIT_CONTRACT = {
    "label_horizon_days": 5,
    "train_signal_window": {"start": "2026-02-02", "end": "2026-06-19"},
    "train_validation_purge_window": {"start": "2026-06-22", "end": "2026-06-26"},
    "validation_signal_window": {"start": "2026-06-29", "end": "2026-07-03"},
    "validation_test_purge_window": {"start": "2026-07-06", "end": "2026-07-10"},
    "test_signal_window": {"start": "2026-07-13", "end": "2026-07-16"},
    "split_type": "chronological_train_validation_purged_test",
}

CANDIDATE_CONFIGS = (
    {
        "candidate_id": "round28_low_complexity10_v1",
        "source_round": 28,
        "feature_profile": "all_v1",
        "min_train_dates": 60,
        "test_dates": 10,
        "purge_dates": 5,
        "max_train_dates": None,
        "n_estimators": 10,
        "learning_rate": 0.05,
        "num_leaves": 3,
        "random_state": 20260720,
        "relevance_levels": 5,
        "rule_gate_threshold": 50.0,
        "top_k_values": [3, 5, 7],
    },
    {
        "candidate_id": "round39_risk_off_v1",
        "source_round": 39,
        "feature_profile": "all_v1",
        "min_train_dates": 60,
        "test_dates": 10,
        "purge_dates": 5,
        "max_train_dates": None,
        "n_estimators": 40,
        "learning_rate": 0.05,
        "num_leaves": 15,
        "random_state": 20260720,
        "relevance_levels": 5,
        "rule_gate_threshold": 50.0,
        "top_k_values": [3, 5, 7],
        "regime_analysis": "risk_off_only_analysis; model features remain all_v1",
    },
    {
        "candidate_id": "round16_min_train70_v1",
        "source_round": 16,
        "feature_profile": "all_v1",
        "min_train_dates": 70,
        "test_dates": 10,
        "purge_dates": 5,
        "max_train_dates": None,
        "n_estimators": 40,
        "learning_rate": 0.05,
        "num_leaves": 15,
        "random_state": 20260720,
        "relevance_levels": 5,
        "rule_gate_threshold": 50.0,
        "top_k_values": [3, 5, 7],
    },
    {
        "candidate_id": "round18_rolling80_v1",
        "source_round": 18,
        "feature_profile": "all_v1",
        "min_train_dates": 60,
        "test_dates": 10,
        "purge_dates": 5,
        "max_train_dates": 80,
        "n_estimators": 40,
        "learning_rate": 0.05,
        "num_leaves": 15,
        "random_state": 20260720,
        "relevance_levels": 5,
        "rule_gate_threshold": 50.0,
        "top_k_values": [3, 5, 7],
    },
)

EVENT_ENHANCEMENT_AB_CONTRACT = {
    "status": "design_only_not_run",
    "event_source_read": False,
    "event_model_training": False,
    "baseline_arm": {
        "name": "A_baseline",
        "features": "selected_candidate_features_only",
        "label": "future_5d_industry_return_minus_cross_sectional_median",
    },
    "enhanced_arm": {
        "name": "B_event_enhanced",
        "features": "A plus reviewed event features only",
        "requires": [
            "event_source_manifest_sha256",
            "event_record_as_of_timestamp",
            "event_effective_from_not_after_as_of",
            "reviewed_source_registry",
            "same_train_validation_test_dates",
        ],
    },
    "paired_metrics": [
        "mean_excess_return",
        "mean_net_excess_return",
        "rank_ic",
        "ndcg",
        "turnover",
        "max_drawdown",
        "regime_metrics",
    ],
    "acceptance_rule": "Compare A/B on identical frozen folds and report deltas; no automatic promotion.",
    "forbidden": ["formal_predictor", "formal_candidate_selection", "broker", "order", "live"],
}


def calculate_drawdown_metrics(returns: Sequence[float]) -> dict[str, float | int | None]:
    """Return deterministic path and drawdown metrics for paper evaluation only."""

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    peak_index = 0
    trough_index: int | None = None
    for index, value in enumerate(returns):
        equity *= 1.0 + float(value)
        if equity > peak:
            peak = equity
            peak_index = index
        drawdown = 1.0 - equity / peak if peak else 0.0
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            trough_index = index
    return {
        "observations": len(returns),
        "cumulative_return": equity - 1.0,
        "final_equity": equity,
        "max_drawdown": max_drawdown,
        "max_drawdown_peak_index": peak_index if trough_index is not None else None,
        "max_drawdown_trough_index": trough_index,
    }


def _date_values(payload: Mapping[str, Any]) -> list[date]:
    values: list[date] = []
    for row in payload.get("records") or []:
        if not isinstance(row, Mapping):
            continue
        for value in row.values():
            if not isinstance(value, str):
                continue
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                continue
            if date(2020, 1, 1) <= parsed <= date(2035, 1, 1):
                values.append(parsed)
    return values


def inventory_industry_history(source_root: Path | str) -> dict[str, Any]:
    root = Path(source_root).resolve()
    documents: list[dict[str, Any]] = []
    all_dates: list[date] = []
    for path in sorted((root / "industry").glob("*.json")):
        payload, source_sha = load_strict_json_with_sha256(path)
        dates = _date_values(payload)
        all_dates.extend(dates)
        documents.append({
            "path": str(path.resolve()),
            "sha256": source_sha,
            "record_count": len(payload.get("records") or []),
            "source": payload.get("source"),
            "start_date": payload.get("start_date"),
            "end_date": payload.get("end_date"),
        })
    if not documents or not all_dates:
        raise ValueError("industry history inventory is empty")
    return {
        "source_root": str(root),
        "document_count": len(documents),
        "source_values": sorted({str(item["source"]) for item in documents}),
        "record_date_start": min(all_dates).isoformat(),
        "record_date_end": max(all_dates).isoformat(),
        "documents": documents,
    }


def build_oos_readiness_report(
    source_root: Path | str,
    *,
    dataset_counts: Mapping[str, Any],
    review_date: str = "2026-07-20",
) -> dict[str, Any]:
    inventory = inventory_industry_history(source_root)
    source_end = date.fromisoformat(inventory["record_date_end"])
    mature_end = date.fromisoformat(str(dataset_counts["date_end"]))
    test_start = date.fromisoformat(STRICT_SPLIT_CONTRACT["test_signal_window"]["start"])
    report = {
        "schema_version": "ml-industry-sector-oos-readiness-v1",
        "status": "blocked_pending_label_maturity",
        "mode": "paper_shadow_research_only",
        "review_date": review_date,
        "source_inventory": inventory,
        "dataset_counts": dict(dataset_counts),
        "latest_source_record_date": source_end.isoformat(),
        "latest_mature_label_date": mature_end.isoformat(),
        "planned_test_signal_start": test_start.isoformat(),
        "readiness": {
            "source_window_available": source_end >= test_start,
            "labels_mature_for_test": mature_end >= date.fromisoformat(STRICT_SPLIT_CONTRACT["test_signal_window"]["end"]),
            "strict_pit_eligible": False,
            "eligible_for_oos_claim": False,
            "promotion_allowed": False,
            "live_trading_allowed": False,
            "formal_predictor_compatible": False,
        },
        "reason": "Later bars exist through 2026-07-16, but five-day labels for the planned 2026-07-13 test start are not yet mature.",
        "strict_split_contract": STRICT_SPLIT_CONTRACT,
        "candidate_configs": [dict(config) for config in CANDIDATE_CONFIGS],
        "event_enhancement_ab": EVENT_ENHANCEMENT_AB_CONTRACT,
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
    }
    return report
