#!/usr/bin/env python
"""Run point-in-time sector score validation in paper/shadow mode."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.backtest.sector_score_pit_validation import (  # noqa: E402
    run_pit_validation,
    write_validation_report,
)
from theme_sector_radar.reporting.strict_json import write_text_atomic  # noqa: E402


def _parse_horizons(value: str) -> tuple[int, ...]:
    try:
        horizons = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("horizons must be comma-separated integers") from exc
    if not horizons or any(item <= 0 for item in horizons):
        raise argparse.ArgumentTypeError("horizons must be positive")
    return horizons


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Sector Score PIT Validation",
        "",
        "> Paper/shadow research only. No broker connection or live order instruction.",
        "",
        "## Coverage",
        "",
        f"- Source documents: {report['source_manifest']['document_count']}",
        f"- Labelable dates: {report['coverage']['labelable_date_count']}",
        f"- Development dates: {report['coverage']['development_date_count']}",
        f"- Samples: {report['coverage']['sample_count']}",
        f"- Holdout: {report['holdout']['status']} ({len(report['holdout']['dates'])} dates)",
        f"- Holdout blind: {str(report['holdout']['blind']).lower()}",
        "- Holdout eligible for OOS claim: "
        + str(report["holdout"]["eligible_for_oos_claim"]).lower(),
        f"- Evidence classification: {report['evidence_classification']}",
        f"- Strict PIT eligible: {str(report['strict_pit_eligible']).lower()}",
        f"- Artifact status: {report['artifact_status']}",
        "",
        "## Score Evidence",
        "",
        "| Score | Horizon | Mean daily Rank IC | Top-bottom spread | Top-K positive rate | Tie rate | Cap rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for score_name, score_result in report["score_results"].items():
        health = score_result["score_health"]
        for horizon, metrics in score_result["horizons"].items():
            lines.append(
                "| "
                f"{score_name} | {horizon} | {_fmt(metrics['mean_daily_rank_ic'])} | "
                f"{_fmt(metrics['top_bottom_spread'])} | "
                f"{_fmt(metrics['top_k_positive_rate'])} | "
                f"{_fmt(health['tied_sample_rate'])} | {_fmt(health['cap_rate'])} |"
            )
    lines.extend(
        [
            "",
            "## Shadow Candidates",
            "",
        ]
    )
    for candidate_name, candidate in report["shadow_candidates"]["candidates"].items():
        eligibility = candidate["feature_eligibility"]
        walk_scope = candidate["walk_forward_scope"]
        lines.extend(
            [
                f"### {candidate_name}",
                "",
                f"- Decision: {candidate['development_gate']['decision']}",
                f"- Eligible samples: {eligibility['eligible_technical_samples']}",
                f"- Excluded incomplete samples: {eligibility['excluded_incomplete_technical_samples']}",
                f"- Walk-forward scope: {walk_scope['method']} ({walk_scope['date_count']} dates, {walk_scope['fold_count']} folds)",
                "",
                "| Horizon | Rank IC | Top-bottom spread | Top-universe spread |",
                "|---|---:|---:|---:|",
            ]
        )
        for horizon, metrics in candidate["horizons"].items():
            lines.append(
                f"| {horizon} | {_fmt(metrics['mean_daily_rank_ic'])} | "
                f"{_fmt(metrics['top_bottom_spread'])} | "
                f"{_fmt(metrics['top_universe_spread'])} |"
            )
        ablations = candidate.get("factor_ablation") or {}
        if ablations:
            lines.extend(
                [
                    "",
                    "| Ablation | Horizon | Rank IC | Top-bottom spread |",
                    "|---|---|---:|---:|",
                ]
            )
            for component, variant in ablations.items():
                for horizon, metrics in variant["horizons"].items():
                    lines.append(
                        f"| {component} | {horizon} | "
                        f"{_fmt(metrics['mean_daily_rank_ic'])} | "
                        f"{_fmt(metrics['top_bottom_spread'])} |"
                    )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            f"- Promotion allowed: {str(report['promotion_gate']['promotion_allowed']).lower()}",
            f"- Reason: {report['promotion_gate']['reason']}",
            "- Blocking reasons: "
            + ", ".join(report["promotion_gate"].get("blocking_reasons") or []),
            f"- Live trading ready: {str(report['promotion_gate']['live_trading_ready']).lower()}",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):.6f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--history-root",
        type=Path,
        default=PROJECT_ROOT / "data_cache" / "sector_history",
    )
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports" / "sector_score_pit_validation")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--trend-window", type=int, default=10)
    parser.add_argument("--horizons", type=_parse_horizons, default=(1, 3, 5))
    parser.add_argument("--holdout-days", type=int, default=20)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--fold-count", type=int, default=4)
    parser.add_argument("--purge-days", type=int)
    parser.add_argument("--embargo-days", type=int, default=2)
    parser.add_argument(
        "--artifact-status",
        choices=(
            "unclassified_shadow_validation",
            "current_path_a_v3",
            "archived_fourth_round",
            "superseded_path_a_v2",
            "superseded_historical_intermediate_snapshot",
        ),
        default="unclassified_shadow_validation",
    )
    args = parser.parse_args()

    report = run_pit_validation(
        args.history_root,
        start_date=args.start_date,
        end_date=args.end_date,
        trend_window=args.trend_window,
        horizons=args.horizons,
        holdout_days=args.holdout_days,
        top_k=args.top_k,
        fold_count=args.fold_count,
        purge_days=args.purge_days,
        embargo_days=args.embargo_days,
        artifact_status=args.artifact_status,
    )
    start = report["coverage"]["labelable_start_date"] or "none"
    end = report["coverage"]["labelable_end_date"] or "none"
    output_dir = args.output_root / f"{start}_to_{end}"
    json_path = output_dir / "sector_score_pit_validation.json"
    markdown_path = output_dir / "sector_score_pit_validation.md"
    write_validation_report(report, json_path)
    write_text_atomic(markdown_path, _markdown(report))
    print(json_path)
    print(markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
