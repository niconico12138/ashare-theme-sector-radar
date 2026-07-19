#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Any-time realtime A-share preview report.

This script only writes realtime preview artifacts under
``reports/realtime_preview/<DATE>/<SNAPSHOT_LABEL>/``.  It intentionally avoids
the formal daily bridge, forward-return, and scoring-calibration paths.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

if sys.stdout.encoding and sys.stdout.encoding.lower() in {"gbk", "cp936", "cp1252"}:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.data.today_realtime_client import TodayRealtimeClient
from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous
from theme_sector_radar.timing.paper_trading import build_timing_paper_trading_records


TIMING_PAPER_FIELD_ALLOWLIST = {
    "boards",
    "source_boards",
    "open_to_midday_resilience_score",
    "midday_hold_score",
    "vwap_above_ratio_score",
    "late_high_near_close_score",
    "high_to_close_drawdown_score",
    "lower_low_sequence_risk",
    "stock_vs_market_intraday_alpha_score",
    "relative_resilience_score",
    "optimized_watch_score",
    "late_amount_surge_score",
    "failed_breakout_risk",
    "execution_tradeability_score",
    "execution_turnover_depth_score",
    "late_breakdown_risk",
    "weak_close_after_volume_risk",
    "sector_breadth_quality_score",
    "market_regime_score",
}


def normalize_as_of(value: str | None = None, now: datetime | None = None) -> str:
    if not value:
        return (now or datetime.now()).strftime("%Y-%m-%d")
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text[:10]


def default_snapshot_label(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%H%M%S")


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _clean_code(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text[-6:] if len(text) >= 6 else text


def _is_st_name(name: str) -> bool:
    upper = str(name or "").strip().upper()
    return upper.startswith("ST") or upper.startswith("*ST") or "ST" in upper


def _is_main_board_code(code: str) -> bool:
    if not code or len(code) != 6 or not code.isdigit():
        return False
    return code.startswith(("600", "601", "603", "605", "000", "001", "002", "003"))


def build_candidates(spot_result: dict[str, Any], top_n: int = 30) -> tuple[list[dict[str, Any]], list[str]]:
    rows = spot_result.get("rows") or []
    source = spot_result.get("source") or "unknown"
    warnings: list[str] = []
    filtered: list[dict[str, Any]] = []

    if not rows:
        return [], ["Realtime source returned no rows"]

    skipped_missing_code = 0
    skipped_st = 0
    skipped_non_main_board = 0
    skipped_missing_fields = 0

    for row in rows:
        code = _clean_code(row.get("code"))
        name = str(row.get("name") or "").strip()
        latest_price = _coerce_float(row.get("latest_price"))
        change_pct = _coerce_float(row.get("change_pct"))
        volume = _coerce_float(row.get("volume")) or 0.0
        amount = _coerce_float(row.get("amount")) or 0.0

        if not code:
            skipped_missing_code += 1
            continue
        if not _is_main_board_code(code):
            skipped_non_main_board += 1
            continue
        if _is_st_name(name):
            skipped_st += 1
            continue
        if latest_price is None or change_pct is None:
            skipped_missing_fields += 1
            continue

        filtered.append(
            {
                "code": code,
                "name": name,
                "latest_price": latest_price,
                "change_pct": change_pct,
                "volume": volume,
                "amount": amount,
                "source": source,
                "data_semantics": "intraday_snapshot",
                **{key: row.get(key) for key in TIMING_PAPER_FIELD_ALLOWLIST if key in row},
            }
        )

    filtered.sort(
        key=lambda item: (
            item.get("change_pct") or 0.0,
            item.get("amount") or 0.0,
            item.get("volume") or 0.0,
        ),
        reverse=True,
    )

    candidates: list[dict[str, Any]] = []
    for index, item in enumerate(filtered[:top_n], start=1):
        candidates.append({**item, "rank_intraday": index})

    if skipped_missing_code:
        warnings.append(f"Skipped {skipped_missing_code} row(s) with missing code")
    if skipped_st:
        warnings.append(f"Skipped {skipped_st} ST row(s)")
    if skipped_non_main_board:
        warnings.append(f"Skipped {skipped_non_main_board} non-main-board row(s)")
    if skipped_missing_fields:
        warnings.append(f"Skipped {skipped_missing_fields} row(s) with missing price or change_pct")
    if not candidates:
        warnings.append("No valid realtime preview candidates after filtering")

    return candidates, warnings


def build_report(
    as_of: str,
    snapshot_label: str,
    spot_result: dict[str, Any],
    top_n: int = 30,
    generated_at: str | None = None,
    minute_bars_by_code: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    candidates, warnings = build_candidates(spot_result, top_n=top_n)
    normalized_as_of = normalize_as_of(as_of)
    signal_session_closed = _signal_session_closed(
        snapshot_label,
        source_generated_at=spot_result.get("generated_at"),
        as_of=normalized_as_of,
    )
    timing_paper_trading = build_timing_paper_trading_records(
        candidates if signal_session_closed else [],
        as_of=normalized_as_of,
        snapshot_label=snapshot_label,
    )
    timing_paper_trading.update(
        {
            "realtime_observation_only": True,
            "observation_mode": (
                "signal_day_close_confirmed"
                if signal_session_closed
                else "intraday_candidate_observation_only"
            ),
            "signal_visibility": (
                "available_after_signal_session_close"
                if signal_session_closed
                else "withheld_until_after_signal_session_close"
            ),
            "signal_session_closed": signal_session_closed,
            "causal_entry_status": "pending_next_trading_session",
        }
    )
    source_status = {
        "status": "available" if spot_result.get("rows") else "empty",
        "source": spot_result.get("source"),
        "data_semantics": spot_result.get("data_semantics") or "intraday_snapshot",
        "row_count": spot_result.get("row_count", len(spot_result.get("rows") or [])),
        "fallback_used": spot_result.get("fallback_used", False),
        "fallback_reason": spot_result.get("fallback_reason"),
        "source_generated_at": spot_result.get("generated_at"),
    }

    return {
        "schema_version": "1.0",
        "as_of": normalized_as_of,
        "snapshot_label": snapshot_label,
        "generated_at": generated_at or datetime.now().isoformat(timespec="seconds"),
        "report_mode": "realtime_preview",
        "data_semantics": "intraday_snapshot",
        "not_for_calibration": True,
        "not_for_forward_returns": True,
        "not_for_weight_changes": True,
        "selection_policy": {
            "exclude_st": True,
            "exclude_invalid_code": True,
            "main_board_only": True,
            "exclude_non_main_board": True,
            "main_board_prefixes": ["600", "601", "603", "605", "000", "001", "002", "003"],
        },
        "source_status": source_status,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "timing_paper_trading": timing_paper_trading,
        "warnings": warnings,
    }


def _signal_session_closed(
    snapshot_label: str,
    *,
    source_generated_at: Any,
    as_of: str,
) -> bool:
    digits = "".join(character for character in str(snapshot_label or "") if character.isdigit())
    if len(digits) not in (4, 6):
        return False
    hour = int(digits[:2])
    minute = int(digits[2:4])
    second = int(digits[4:6]) if len(digits) == 6 else 0
    if hour > 23 or minute > 59 or second > 59:
        return False
    if (hour, minute, second) <= (15, 0, 0):
        return False
    try:
        source_time = datetime.fromisoformat(str(source_generated_at or "").replace("Z", "+00:00"))
    except ValueError:
        return False
    if source_time.tzinfo is not None:
        source_time = source_time.astimezone(timezone(timedelta(hours=8)))
    return (
        source_time.date().isoformat() == as_of
        and (source_time.hour, source_time.minute, source_time.second) > (15, 0, 0)
    )


def generate_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Realtime Preview Report",
        "",
        "⚠️ This report uses intraday_snapshot data.",
        "It is not a final daily report and must not be used for scoring calibration, forward returns, or weight changes.",
        "",
        f"**Date**: {report.get('as_of', '')}",
        f"**Snapshot**: {report.get('snapshot_label', '')}",
        f"**Generated At**: {report.get('generated_at', '')}",
        f"**Candidate Count**: {report.get('candidate_count', 0)}",
        "",
        "## Source Status",
        "",
    ]

    source_status = report.get("source_status") or {}
    lines.extend(
        [
            f"- Status: {source_status.get('status', 'unknown')}",
            f"- Source: {source_status.get('source', 'unknown')}",
            f"- Row count: {source_status.get('row_count', 0)}",
            f"- Fallback used: {source_status.get('fallback_used', False)}",
            "",
        ]
    )

    candidates = report.get("candidates") or []
    if candidates:
        lines.extend(
            [
                "## Candidates",
                "",
                "| Intraday Rank | Code | Name | Latest Price | Change % | Amount | Volume |",
                "|---:|---|---|---:|---:|---:|---:|",
            ]
        )
        for item in candidates:
            price = item.get("latest_price")
            change = item.get("change_pct")
            amount = item.get("amount")
            volume = item.get("volume")
            lines.append(
                "| {rank} | {code} | {name} | {price} | {change} | {amount} | {volume} |".format(
                    rank=item.get("rank_intraday", ""),
                    code=item.get("code", ""),
                    name=item.get("name", ""),
                    price=f"{price:.2f}" if price is not None else "-",
                    change=f"{change:+.2f}%" if change is not None else "-",
                    amount=f"{amount:,.0f}" if amount is not None else "-",
                    volume=f"{volume:,.0f}" if volume is not None else "-",
                )
            )
        lines.append("")

    warnings = report.get("warnings") or []
    if warnings:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")

    timing = report.get("timing_paper_trading") or {}
    timing_summary = timing.get("summary") or {}
    lines.extend(
        [
            "## Timing Paper Trading",
            "",
            f"- Paper-only: `{timing.get('paper_trading_only', True)}`",
            f"- Record count: `{timing_summary.get('record_count', 0)}`",
            f"- Risk tags: `{timing_summary.get('risk_tag_counts') or {}}`",
            "",
        ]
    )

    lines.extend(
        [
            "---",
            "",
            "Preview-only artifact. Do not merge into daily bridge, scoring calibration, forward returns, or weight-change workflows.",
            "",
        ]
    )
    return "\n".join(lines)


def generate_realtime_aihf_request(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "as_of": report.get("as_of"),
        "snapshot_label": report.get("snapshot_label"),
        "generated_at": report.get("generated_at"),
        "report_mode": "realtime_preview",
        "data_semantics": "intraday_snapshot",
        "not_for_calibration": True,
        "not_for_forward_returns": True,
        "not_for_weight_changes": True,
        "candidates": report.get("candidates") or [],
        "timing_paper_trading": report.get("timing_paper_trading") or {},
    }


def run_realtime_preview(
    as_of: str | None = None,
    snapshot_label: str | None = None,
    top_n: int = 30,
    output_dir: str | Path = "reports/realtime_preview",
    run_aihf: bool = False,
    realtime_client: TodayRealtimeClient | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or datetime.now()
    normalized_as_of = normalize_as_of(as_of, now=current)
    label = snapshot_label or default_snapshot_label(current)
    client = realtime_client or TodayRealtimeClient()

    try:
        spot_result = client.get_a_share_spot()
    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "as_of": normalized_as_of,
            "snapshot_label": label,
        }

    if not spot_result.get("rows"):
        return {
            "status": "failed",
            "error": "Realtime source returned no rows",
            "as_of": normalized_as_of,
            "snapshot_label": label,
        }

    report = build_report(
        as_of=normalized_as_of,
        snapshot_label=label,
        spot_result=spot_result,
        top_n=top_n,
        generated_at=current.isoformat(timespec="seconds"),
    )

    root = Path(output_dir)
    if not root.is_absolute():
        root = PROJECT_ROOT / root
    out_dir = root / normalized_as_of / label
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "realtime_preview.json"
    md_path = out_dir / "realtime_preview.md"
    write_text_preserving_previous(
        json_path,
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
    )
    write_text_preserving_previous(md_path, generate_markdown(report))

    aihf_path = None
    if run_aihf:
        aihf_path = out_dir / "realtime_aihf_request.json"
        write_text_preserving_previous(
            aihf_path,
            json.dumps(generate_realtime_aihf_request(report), ensure_ascii=False, indent=2, allow_nan=False),
        )

    return {
        "status": "ok",
        "output_dir": str(out_dir),
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "aihf_request_path": str(aihf_path) if aihf_path else None,
        "report": report,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run any-time realtime preview report")
    parser.add_argument("--as-of", default=None, help="Date in YYYY-MM-DD or YYYYMMDD. Defaults to today.")
    parser.add_argument("--snapshot-label", default=None, help="Snapshot label. Defaults to current HHMMSS.")
    parser.add_argument("--top-n", type=int, default=30, help="Number of realtime candidates to export.")
    parser.add_argument("--output-dir", default="reports/realtime_preview", help="Preview output root.")
    parser.add_argument("--run-aihf", action="store_true", help="Write realtime_aihf_request.json only; never calls daily bridge.")
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    realtime_client: TodayRealtimeClient | None = None,
    now: datetime | None = None,
) -> int:
    args = parse_args(argv)
    result = run_realtime_preview(
        as_of=args.as_of,
        snapshot_label=args.snapshot_label,
        top_n=args.top_n,
        output_dir=args.output_dir,
        run_aihf=args.run_aihf,
        realtime_client=realtime_client,
        now=now,
    )

    if result["status"] != "ok":
        print(f"Realtime preview failed: {result.get('error')}")
        return 1

    report = result["report"]
    print(f"Realtime preview written: {result['output_dir']}")
    print(f"Candidates: {report['candidate_count']}")
    print("Mode: realtime_preview / intraday_snapshot")
    if result.get("aihf_request_path"):
        print(f"AIHF request written: {result['aihf_request_path']}")
        print("AIHF bridge was not called.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
