"""Audit real-data readiness for the ML stock-ranker shadow path."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.contract import canonical_sha256
from theme_sector_radar.ml.readiness import build_data_readiness_report
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


def _code(row) -> str:
    if not isinstance(row, dict):
        return ""
    return str(row.get("code") or row.get("stock_code") or "").zfill(6)


def _record_date(row) -> str | None:
    if not isinstance(row, dict):
        return None
    candidates = []
    for value in row.values():
        if not isinstance(value, str):
            continue
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            continue
        if parsed.isoformat() == value:
            candidates.append(value)
    if len(candidates) > 1:
        raise ValueError("sector history row contains multiple ISO date values")
    return candidates[0] if candidates else None


def _mature_stock_return_count(
    payload: Mapping[str, Any], *, day: str, horizon: str, candidate_codes: set[str]
) -> dict[str, int]:
    values_by_code = payload.get("forward_returns")
    metadata_by_code = payload.get("label_metadata")
    if not isinstance(values_by_code, Mapping) or not isinstance(
        metadata_by_code, Mapping
    ):
        return {
            "mature_candidate_rows": 0,
            "candidate_rows": len(candidate_codes),
            "forward_rows_outside_candidate_pool": 0,
            "candidate_rows_missing_from_forward": len(candidate_codes),
        }
    expected_contract = {
        "schema_version": "forward-return-label-contract-v2",
        "frequency": "1d",
        "adjustment": "qfq",
        "target_date_basis": "versioned_exchange_calendar",
    }
    if payload.get("label_contract") != expected_contract:
        return {
            "mature_candidate_rows": 0,
            "candidate_rows": len(candidate_codes),
            "forward_rows_outside_candidate_pool": len(
                set(values_by_code) - candidate_codes
            ),
            "candidate_rows_missing_from_forward": len(
                candidate_codes - set(values_by_code)
            ),
        }
    mature = 0
    forward_codes = {str(code).zfill(6) for code in values_by_code}
    for code in sorted(candidate_codes & forward_codes):
        values = values_by_code.get(code)
        metadata = metadata_by_code.get(code)
        horizon_metadata = (
            (metadata.get("horizons") or {}).get(horizon)
            if isinstance(metadata, Mapping)
            else None
        )
        if not isinstance(values, Mapping) or not isinstance(horizon_metadata, Mapping):
            continue
        target = str(horizon_metadata.get("target_trading_date") or "")
        try:
            target_date = date.fromisoformat(target)
            signal_date = date.fromisoformat(day)
        except ValueError:
            continue
        if (
            metadata.get("signal_date") == day
            and metadata.get("frequency") == "1d"
            and metadata.get("adjustment") == "qfq"
            and horizon_metadata.get("mature") is True
            and horizon_metadata.get("return_available") is True
            and target_date > signal_date
            and values.get(horizon) is not None
        ):
            mature += 1
    return {
        "mature_candidate_rows": mature,
        "candidate_rows": len(candidate_codes),
        "forward_rows_outside_candidate_pool": len(
            forward_codes - candidate_codes
        ),
        "candidate_rows_missing_from_forward": len(
            candidate_codes - forward_codes
        ),
    }


def _active_candidate_relations(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    formal = payload.get("formal_candidate_selection")
    if (
        isinstance(formal, Mapping)
        and formal.get("status") == "active_for_paper_research"
        and isinstance(formal.get("selected"), list)
    ):
        return list(formal["selected"])
    active = payload.get("direction_linkage_v2_selection_shadow")
    if (
        isinstance(active, Mapping)
        and active.get("schema_version")
        == "direction_linkage_v2_selection_shadow.v1"
        and active.get("mode") == "paper_shadow_research_only"
        and isinstance(active.get("selected"), list)
        and active.get("selected_count") == len(active["selected"])
    ):
        return list(active["selected"])
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-root",
        type=Path,
        default=PROJECT_ROOT / "reports" / "paper_shadow" / "linkage_v2_unified_stockdb",
    )
    parser.add_argument(
        "--forward-root",
        type=Path,
        default=PROJECT_ROOT / "reports" / "paper_shadow",
    )
    parser.add_argument(
        "--sector-history-root",
        type=Path,
        default=PROJECT_ROOT / "data_cache" / "sector_history" / "industry",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            PROJECT_ROOT
            / "reports"
            / "paper_shadow"
            / "ml_stock_ranker"
            / "data_readiness_2026-07-18.json"
        ),
    )
    args = parser.parse_args()

    candidate_snapshots = []
    candidate_sources = []
    candidate_codes_by_date = {}
    for path in sorted(args.candidate_root.glob("*/unified_report.json")):
        payload, sha256 = load_strict_json_with_sha256(path)
        day = str(payload.get("as_of_date") or "")
        relations = _active_candidate_relations(payload)
        if not relations:
            continue
        codes = {_code(row) for row in relations if _code(row)}
        candidate_codes_by_date[day] = codes
        candidate_snapshots.append(
            {
                "as_of_date": day,
                "candidate_count": len(relations),
                "stock_count": len(codes),
                "feature_buildable": len(relations) == len(codes),
                "duplicate_stock_identity_count": max(
                    0, len(relations) - len(codes)
                ),
            }
        )
        candidate_sources.append(
            {"path": str(path), "sha256": sha256, "as_of_date": day}
        )
    candidate_identity = {
        row["sha256"]: row["as_of_date"] for row in candidate_sources
    }

    horizons = ("1d", "3d", "5d")
    stock_return_dates = {horizon: set() for horizon in horizons}
    excess_label_dates = {horizon: set() for horizon in horizons}
    labeled_rows = {horizon: 0 for horizon in horizons}
    candidate_rows = {horizon: 0 for horizon in horizons}
    forward_sources = []
    for path in sorted(args.forward_root.rglob("forward_returns.json")):
        payload, sha256 = load_strict_json_with_sha256(path)
        day = str(payload.get("as_of") or payload.get("as_of_date") or "")
        candidate_input = payload.get("candidate_input")
        candidate_sha = (
            str(candidate_input.get("sha256") or "")
            if isinstance(candidate_input, Mapping)
            else ""
        )
        candidate_bound = bool(
            day and candidate_identity.get(candidate_sha) == day
        )
        horizon_audit = {}
        for horizon in horizons:
            audit = _mature_stock_return_count(
                payload,
                day=day,
                horizon=horizon,
                candidate_codes=(candidate_codes_by_date.get(day, set())),
            )
            if candidate_bound:
                labeled_rows[horizon] += audit["mature_candidate_rows"]
                candidate_rows[horizon] += audit["candidate_rows"]
                if audit["mature_candidate_rows"] > 0:
                    stock_return_dates[horizon].add(day)
            horizon_audit[horizon] = audit
        forward_sources.append(
            {
                "path": str(path),
                "sha256": sha256,
                "as_of_date": day,
                "candidate_input_sha256": candidate_sha or None,
                "candidate_snapshot_bound": candidate_bound,
                "horizons": horizon_audit,
                "ml_sector_excess_labels_present": False,
            }
        )

    sector_dates = set()
    sector_sources = []
    for path in sorted(args.sector_history_root.glob("*.json")):
        payload, sha256 = load_strict_json_with_sha256(path)
        records = payload.get("records") or []
        for row in records:
            record_date = _record_date(row)
            if record_date:
                sector_dates.add(record_date)
        sector_sources.append({"path": str(path), "sha256": sha256})

    source_manifest = {
        "candidate_sources": candidate_sources,
        "candidate_sources_sha256": canonical_sha256(candidate_sources),
        "forward_sources": forward_sources,
        "forward_sources_sha256": canonical_sha256(forward_sources),
        "sector_history": {
            "root": str(args.sector_history_root),
            "file_count": len(sector_sources),
            "source_manifest_sha256": canonical_sha256(sector_sources),
            "files": sector_sources,
            "date_start": min(sector_dates) if sector_dates else None,
            "date_end": max(sector_dates) if sector_dates else None,
        },
    }
    report = build_data_readiness_report(
        candidate_snapshots=candidate_snapshots,
        forward_stock_return_dates_by_horizon={
            horizon: sorted(stock_return_dates[horizon]) for horizon in horizons
        },
        forward_excess_label_dates_by_horizon={
            horizon: sorted(excess_label_dates[horizon]) for horizon in horizons
        },
        forward_label_coverage_by_horizon={
            horizon: (
                labeled_rows[horizon] / candidate_rows[horizon]
                if candidate_rows[horizon]
                else 0.0
            )
            for horizon in horizons
        },
        sector_history_date_count=len(sector_dates),
        historical_candidate_universe_versioned=False,
        source_manifest=source_manifest,
    )
    write_strict_json_atomic(args.output, report)
    print(
        f"status={report['status']} candidate_dates={report['counts']['candidate_snapshot_dates']} "
        f"mature_5d_excess_label_dates={report['counts']['forward_label_dates']} "
        f"sector_history_dates={report['counts']['sector_history_dates']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
