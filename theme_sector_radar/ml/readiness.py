"""Fail-closed data readiness for the ML stock-ranker shadow path."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)

from .contract import canonical_sha256, optional_ml_dependency_readiness, require_finite
from .schema import DISCLAIMER, MODE


def _dates(values: Sequence[str], *, context: str) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value)
        try:
            parsed = date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"{context} contains an invalid date: {text!r}") from exc
        if parsed.isoformat() != text:
            raise ValueError(f"{context} contains a non-canonical date: {text!r}")
        result.append(text)
    if len(result) != len(set(result)):
        raise ValueError(f"{context} contains duplicate dates")
    return sorted(result)


def build_data_readiness_report(
    *,
    candidate_snapshots: Sequence[Mapping[str, Any]],
    forward_stock_return_dates_by_horizon: Mapping[str, Sequence[str]],
    forward_excess_label_dates_by_horizon: Mapping[str, Sequence[str]],
    forward_label_coverage_by_horizon: Mapping[str, float],
    sector_history_date_count: int,
    historical_candidate_universe_versioned: bool,
    source_manifest: Mapping[str, Any],
    pit_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assess whether real stock-candidate history can support model training."""

    candidate_dates = _dates(
        [str(row.get("as_of_date") or "") for row in candidate_snapshots],
        context="candidate snapshots",
    )
    required_horizons = ("1d", "3d", "5d")
    stock_return_dates = {
        horizon: _dates(
            list(forward_stock_return_dates_by_horizon.get(horizon, [])),
            context=f"forward stock returns {horizon}",
        )
        for horizon in required_horizons
    }
    excess_label_dates = {
        horizon: _dates(
            list(forward_excess_label_dates_by_horizon.get(horizon, [])),
            context=f"forward excess labels {horizon}",
        )
        for horizon in required_horizons
    }
    coverage_by_horizon: dict[str, float] = {}
    for horizon in required_horizons:
        coverage = float(forward_label_coverage_by_horizon.get(horizon, 0.0))
        if not 0.0 <= coverage <= 1.0:
            raise ValueError(f"forward label coverage {horizon} must be within [0, 1]")
        coverage_by_horizon[horizon] = coverage
    primary_label_dates = excess_label_dates["5d"]
    evidence_verified = False
    prospective_candidate_dates: list[str] = []
    verified_training_dates: list[str] = []
    pit_evidence_sha256 = None
    if pit_evidence is not None:
        if not isinstance(pit_evidence, Mapping):
            raise ValueError("PIT evidence must be an object")
        evidence_core = {
            key: value for key, value in pit_evidence.items() if key != "evidence_sha256"
        }
        pit_evidence_sha256 = str(pit_evidence.get("evidence_sha256") or "")
        if canonical_sha256(evidence_core) != pit_evidence_sha256:
            raise ValueError("PIT evidence SHA mismatch")
        if (
            pit_evidence.get("schema_version") != "ml-stock-pit-evidence-v1"
            or pit_evidence.get("mode") != MODE
            or pit_evidence.get("status") != "verified"
            or pit_evidence.get("verifier")
            != "theme_sector_radar.ml.accumulation.verify_accumulation_archive"
            or pit_evidence.get("promotion_allowed") is not False
        ):
            raise ValueError("PIT evidence contract mismatch")
        evidence_snapshots = pit_evidence.get("snapshots")
        evidence_labels = pit_evidence.get("labels")
        if not isinstance(evidence_snapshots, list) or not isinstance(evidence_labels, list):
            raise ValueError("PIT evidence source manifests are missing")
        evidence_candidate_dates = _dates(
            [str(row.get("as_of_date") or "") for row in evidence_snapshots],
            context="PIT evidence candidate snapshots",
        )
        if evidence_candidate_dates != candidate_dates:
            raise ValueError("PIT evidence candidate date universe mismatch")
        prospective_candidate_dates = _dates(
            [
                str(row.get("as_of_date") or "")
                for row in evidence_snapshots
                if row.get("strict_pit_eligible") is True
            ],
            context="PIT evidence prospective candidate snapshots",
        )
        verified_training_dates = _dates(
            list(pit_evidence.get("verified_training_dates") or []),
            context="PIT evidence verified training dates",
        )
        strict_label_dates = {
            str(row.get("signal_date") or "")
            for row in evidence_labels
            if row.get("strict_pit_eligible") is True
        }
        if not set(verified_training_dates).issubset(
            set(prospective_candidate_dates) & strict_label_dates & set(primary_label_dates)
        ):
            raise ValueError("PIT evidence verified training date intersection mismatch")
        counts = pit_evidence.get("counts")
        if (
            not isinstance(counts, Mapping)
            or counts.get("prospective_candidate_snapshot_dates")
            != len(prospective_candidate_dates)
            or counts.get("verified_training_dates") != len(verified_training_dates)
        ):
            raise ValueError("PIT evidence counts mismatch")
        evidence_verified = True
    dependencies = optional_ml_dependency_readiness()
    reasons: list[str] = []
    feature_buildable = all(
        bool(row.get("feature_buildable", True)) for row in candidate_snapshots
    )
    if not feature_buildable:
        reasons.append("candidate_snapshot_stock_identity_not_unique")
    candidate_gate_count = (
        len(prospective_candidate_dates) if evidence_verified else len(candidate_dates)
    )
    label_gate_count = (
        len(verified_training_dates) if evidence_verified else len(primary_label_dates)
    )
    if candidate_gate_count < 60:
        reasons.append("fewer_than_60_candidate_snapshot_dates")
    historical_universe_verified = bool(
        evidence_verified
        and historical_candidate_universe_versioned
        and pit_evidence.get("historical_candidate_universe_versioned") is True
    )
    if not historical_candidate_universe_versioned:
        reasons.append("historical_candidate_universe_not_trusted")
    elif not historical_universe_verified:
        reasons.append("strict_pit_evidence_unverified")
    if label_gate_count < 60:
        reasons.append("fewer_than_60_mature_5d_excess_label_dates")
    if coverage_by_horizon["5d"] < 0.90:
        reasons.append("five_day_excess_label_coverage_below_90_percent")
    if dependencies["status"] != "ready":
        reasons.append("optional_ml_dependencies_missing")
    strict_pit_eligible = bool(
        evidence_verified
        and pit_evidence.get("strict_pit_eligible") is True
        and len(verified_training_dates) >= 60
        and len(prospective_candidate_dates) >= 60
    )
    if not strict_pit_eligible and not reasons:
        reasons.append("strict_pit_evidence_unverified")
    model_training_ready = not reasons and strict_pit_eligible
    report = {
        "schema_version": "ml-stock-data-readiness-v1",
        "mode": MODE,
        "status": "ready" if model_training_ready else "insufficient_data",
        "model_training_ready": model_training_ready,
        "feature_build_ready": bool(candidate_dates) and feature_buildable,
        "dependency_readiness": dependencies,
        "strict_pit_eligible": strict_pit_eligible,
        "pit_evidence_status": (
            "verified_prospective_archive"
            if strict_pit_eligible
            else (
                "verified_but_below_minimum_history"
                if evidence_verified
                else "unverified_no_trusted_verifier"
            )
        ),
        "pit_evidence_sha256": pit_evidence_sha256,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "minimum_requirements": {
            "candidate_snapshot_dates": 60,
            "forward_label_dates": 60,
            "historical_candidate_universe_versioned": True,
            "maximum_label_horizon": 5,
            "minimum_purge_dates": 5,
        },
        "counts": {
            "candidate_snapshot_dates": len(candidate_dates),
            "prospective_candidate_snapshot_dates": len(
                prospective_candidate_dates
            ),
            "verified_training_dates": len(verified_training_dates),
            "candidate_rows": sum(int(row.get("candidate_count") or 0) for row in candidate_snapshots),
            "unique_stock_observations": sum(int(row.get("stock_count") or 0) for row in candidate_snapshots),
            "feature_buildable_snapshot_dates": sum(
                bool(row.get("feature_buildable", True)) for row in candidate_snapshots
            ),
            "forward_label_dates": len(primary_label_dates),
            "forward_stock_return_dates_by_horizon": {
                horizon: len(stock_return_dates[horizon])
                for horizon in required_horizons
            },
            "forward_excess_label_dates_by_horizon": {
                horizon: len(excess_label_dates[horizon])
                for horizon in required_horizons
            },
            "forward_label_coverage_by_horizon": coverage_by_horizon,
            "sector_history_dates": int(sector_history_date_count),
        },
        "date_ranges": {
            "candidate_snapshots": {
                "start": candidate_dates[0] if candidate_dates else None,
                "end": candidate_dates[-1] if candidate_dates else None,
            },
            "forward_labels": {
                "start": primary_label_dates[0] if primary_label_dates else None,
                "end": primary_label_dates[-1] if primary_label_dates else None,
            },
        },
        "historical_candidate_universe_versioned": bool(
            historical_candidate_universe_versioned
        ),
        "historical_candidate_universe_verified": historical_universe_verified,
        "blocking_reasons": reasons,
        "source_manifest": dict(source_manifest),
        "next_required_evidence": [
            "persist one strictly as-of candidate and feature snapshot per trading date",
            "persist matching 1d/3d/5d labels only after maturity",
            "version sector membership and candidate universe by date",
            "freeze a prospective observed tail after the model contract is registered",
        ],
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    require_finite(report, context="ML data readiness")
    validate_no_executable_instructions(report, context="ML data readiness")
    return report
