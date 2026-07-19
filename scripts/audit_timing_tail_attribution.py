#!/usr/bin/env python3
"""Attribute tail losses for paper-only timing strategy versions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_timing_strategy_overfit import _load_samples  # noqa: E402
from scripts.run_timing_combination_experiment import _float  # noqa: E402
from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous  # noqa: E402
from theme_sector_radar.timing.combination_experiment import (  # noqa: E402
    StrategyVersion,
    build_default_strategy_versions,
)


RISK_BUCKET_ORDER = (
    "market_pressure",
    "sector_weakness",
    "failed_breakout",
    "late_breakdown",
    "late_surge_exhaustion",
    "vwap_extension",
    "close_giveback",
    "execution_liquidity",
    "unknown",
)


def run_tail_attribution(
    *,
    candidate_root: Path,
    output_dir: Path,
    as_of: str,
    snapshot_label: str,
    version_ids: Sequence[str],
    start: str | None = None,
    end: str | None = None,
    selection_validation_root: Path | None = PROJECT_ROOT / "reports" / "selection_validation",
    tail_loss_pct: float = -5.0,
) -> dict[str, Any]:
    samples = _load_samples(candidate_root, start, end, selection_validation_root)
    versions = _select_versions(version_ids)
    report = {
        "schema_version": "timing_tail_attribution.v1",
        "as_of": as_of,
        "snapshot_label": snapshot_label,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
        "parameters": {
            "candidate_root": str(candidate_root),
            "selection_validation_root": str(selection_validation_root) if selection_validation_root else None,
            "start": start,
            "end": end,
            "tail_loss_pct": tail_loss_pct,
            "version_ids": list(version_ids),
        },
        "sample_summary": _sample_summary(samples),
        "versions": {},
    }
    for version in versions:
        report["versions"][version.version_id] = _attribute_version(samples, version, tail_loss_pct=tail_loss_pct)

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"timing_tail_attribution_{as_of}_{snapshot_label}.json"
    markdown_path = output_dir / f"timing_tail_attribution_{as_of}_{snapshot_label}.md"
    archived_json_path = write_text_preserving_previous(
        json_path,
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
    )
    archived_markdown_path = write_text_preserving_previous(markdown_path, _markdown(report))
    return {
        "status": "ok",
        "json_path": json_path,
        "markdown_path": markdown_path,
        "archived_previous_paths": [path for path in (archived_json_path, archived_markdown_path) if path],
        "report": report,
    }


def _select_versions(version_ids: Sequence[str]) -> list[StrategyVersion]:
    versions_by_id = {version.version_id: version for version in build_default_strategy_versions()}
    missing = [version_id for version_id in version_ids if version_id not in versions_by_id]
    if missing:
        raise ValueError(f"Unknown strategy version ids: {', '.join(missing)}")
    return [versions_by_id[version_id] for version_id in version_ids]


def _attribute_version(samples: Sequence[Mapping[str, Any]], version: StrategyVersion, *, tail_loss_pct: float) -> dict[str, Any]:
    labeled = [row for row in samples if _float(row.get("forward_return_pct")) is not None]
    selected = [row for row in labeled if all(condition.matches(row) for condition in version.conditions)]
    tail_rows = [row for row in selected if (_float(row.get("forward_return_pct")) or 0.0) <= tail_loss_pct]
    attributed_rows = [_tail_row_summary(row) for row in tail_rows]
    bucket_counts = {bucket: 0 for bucket in RISK_BUCKET_ORDER}
    for row in attributed_rows:
        bucket_counts[row["dominant_risk_bucket"]] += 1
    bucket_counts = {bucket: count for bucket, count in bucket_counts.items() if count}
    returns = [_float(row.get("forward_return_pct")) for row in selected]
    clean_returns = [value for value in returns if value is not None]
    return {
        "version_id": version.version_id,
        "description": version.description,
        "selected_count": len(selected),
        "tail_loss_count": len(tail_rows),
        "tail_loss_rate": round(len(tail_rows) / len(selected), 4) if selected else None,
        "selected_avg_return_pct": round(sum(clean_returns) / len(clean_returns), 4) if clean_returns else None,
        "selected_min_return_pct": round(min(clean_returns), 4) if clean_returns else None,
        "tail_bucket_counts": bucket_counts,
        "tail_rows": attributed_rows,
        "paper_trading_only": True,
        "no_execution_signals": True,
    }


def _tail_row_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    bucket, reasons = _risk_bucket(row)
    boards = row.get("boards")
    if not isinstance(boards, list):
        boards = []
    return {
        "date": row.get("_sample_date"),
        "code": row.get("code"),
        "name": row.get("name"),
        "boards": boards[:5],
        "forward_return_pct": _round(_float(row.get("forward_return_pct"))),
        "dominant_risk_bucket": bucket,
        "risk_reasons": reasons,
        "risk_snapshot": {
            "market_regime_score": _round(_float(row.get("market_regime_score"))),
            "sector_breadth_quality_score": _round(_float(row.get("sector_breadth_quality_score"))),
            "failed_breakout_risk": _round(_float(row.get("failed_breakout_risk"))),
            "cashout_failed_late_breakout_risk": _round(_float(row.get("cashout_failed_late_breakout_risk"))),
            "late_breakdown_risk": _round(_float(row.get("late_breakdown_risk"))),
            "late_amount_surge_score": _round(_float(row.get("late_amount_surge_score"))),
            "volume_without_price_progress_risk": _round(_float(row.get("volume_without_price_progress_risk"))),
            "execution_vwap_slippage_risk": _round(_float(row.get("execution_vwap_slippage_risk"))),
            "cashout_vwap_extension_risk": _round(_float(row.get("cashout_vwap_extension_risk"))),
            "high_to_close_drawdown_score": _round(_float(row.get("high_to_close_drawdown_score"))),
            "cashout_close_giveback_risk": _round(_float(row.get("cashout_close_giveback_risk"))),
            "execution_tradeability_score": _round(_float(row.get("execution_tradeability_score"))),
        },
    }


def _risk_bucket(row: Mapping[str, Any]) -> tuple[str, list[str]]:
    checks = (
        (
            "market_pressure",
            (
                ("market_regime_score", "<=", 40.0),
                ("market_environment_composite_score", "<=", 40.0),
                ("market_environment_limit_down_risk", ">=", 60.0),
            ),
        ),
        (
            "sector_weakness",
            (
                ("sector_breadth_quality_score", "<=", 45.0),
                ("sector_continuation_composite_score", "<=", 45.0),
                ("sector_late_breadth_score", "<=", 45.0),
            ),
        ),
        (
            "failed_breakout",
            (
                ("failed_breakout_risk", ">=", 50.0),
                ("cashout_failed_late_breakout_risk", ">=", 50.0),
            ),
        ),
        (
            "late_breakdown",
            (
                ("late_breakdown_risk", ">=", 8.0),
                ("cashout_late_fade_risk", ">=", 45.0),
                ("weak_close_after_volume_risk", ">=", 45.0),
            ),
        ),
        (
            "late_surge_exhaustion",
            (
                ("late_amount_surge_score", ">=", 50.0),
                ("cashout_late_surge_risk", ">=", 45.0),
                ("volume_without_price_progress_risk", ">=", 10.0),
            ),
        ),
        (
            "vwap_extension",
            (
                ("execution_vwap_slippage_risk", ">=", 45.0),
                ("cashout_vwap_extension_risk", ">=", 45.0),
            ),
        ),
        (
            "close_giveback",
            (
                ("high_to_close_drawdown_score", ">=", 18.0),
                ("cashout_close_giveback_risk", ">=", 40.0),
            ),
        ),
        (
            "execution_liquidity",
            (
                ("execution_tradeability_score", "<=", 50.0),
                ("execution_price_impact_risk", ">=", 55.0),
            ),
        ),
    )
    for bucket, rules in checks:
        reasons = _matching_reasons(row, rules)
        if reasons:
            return bucket, reasons
    return "unknown", []


def _matching_reasons(row: Mapping[str, Any], rules: Sequence[tuple[str, str, float]]) -> list[str]:
    reasons = []
    for field, operator, threshold in rules:
        value = _float(row.get(field))
        if value is None:
            continue
        if operator == ">=" and value >= threshold:
            reasons.append(f"{field} {operator} {threshold:g} (actual {value:g})")
        elif operator == "<=" and value <= threshold:
            reasons.append(f"{field} {operator} {threshold:g} (actual {value:g})")
    return reasons


def _sample_summary(samples: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    dates = sorted({str(row.get("_sample_date")) for row in samples if row.get("_sample_date")})
    return {
        "sample_count": len(samples),
        "labeled_sample_count": sum(1 for row in samples if _float(row.get("forward_return_pct")) is not None),
        "date_count": len(dates),
        "start": dates[0] if dates else None,
        "end": dates[-1] if dates else None,
    }


def _markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Timing Tail Attribution",
        "",
        f"As of: `{report.get('as_of')}`",
        f"Snapshot: `{report.get('snapshot_label')}`",
        "",
        "- Paper-only: `True`",
        "- No execution signals: `True`",
        "- Does not modify official scores: `True`",
        "",
        "## Version Summary",
        "",
        "| Version | Selected | Tail losses | Tail rate | Avg % | Min % | Buckets |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for version_id, item in (report.get("versions") or {}).items():
        buckets = ", ".join(f"{key}: {value}" for key, value in (item.get("tail_bucket_counts") or {}).items())
        lines.append(
            f"| `{version_id}` | {item.get('selected_count')} | {item.get('tail_loss_count')} | "
            f"{item.get('tail_loss_rate')} | {item.get('selected_avg_return_pct')} | "
            f"{item.get('selected_min_return_pct')} | {buckets or '-'} |"
        )
    for version_id, item in (report.get("versions") or {}).items():
        lines.extend(["", f"## Tail Rows: `{version_id}`", ""])
        lines.extend(["| Date | Code | Name | Return % | Bucket | Reasons |", "|---|---|---|---:|---|---|"])
        for row in item.get("tail_rows") or []:
            reasons = "; ".join(row.get("risk_reasons") or [])
            lines.append(
                f"| {row.get('date')} | `{row.get('code')}` | {row.get('name') or ''} | "
                f"{row.get('forward_return_pct')} | `{row.get('dominant_risk_bucket')}` | {reasons or '-'} |"
            )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- This report is for paper-only timing research.",
            "- It does not connect to brokers or emit executable buy/sell signals.",
            "- It does not modify official scores.",
        ]
    )
    return "\n".join(lines) + "\n"


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Attribute paper-only timing strategy tail losses")
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--snapshot-label", required=True)
    parser.add_argument("--version-id", action="append", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--selection-validation-root", default=str(PROJECT_ROOT / "reports" / "selection_validation"))
    parser.add_argument("--tail-loss-pct", type=float, default=-5.0)
    args = parser.parse_args(argv)
    result = run_tail_attribution(
        candidate_root=Path(args.candidate_root),
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        snapshot_label=args.snapshot_label,
        version_ids=args.version_id,
        start=args.start,
        end=args.end,
        selection_validation_root=Path(args.selection_validation_root) if args.selection_validation_root else None,
        tail_loss_pct=args.tail_loss_pct,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
