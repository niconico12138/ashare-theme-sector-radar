#!/usr/bin/env python3
"""Rebuild trustworthy 1m/5m candidate factors from complete stored 1m sessions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.data.local_minute_archive import (  # noqa: E402
    aggregate_complete_1m_session_to_5m,
    bar_timestamp,
    security_bound_bars_sha256,
    validate_bar_security_identity,
    validate_complete_a_share_session,
)
from theme_sector_radar.factors.calculators import calculate_intraday_factors  # noqa: E402
from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous  # noqa: E402
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256  # noqa: E402


CANDIDATE_FILE_NAMES = (
    "top30_candidates.intraday_backfilled.json",
    "top30_candidates.analysis_backfilled.json",
    "top30_candidates.factor_backfilled.json",
    "top30_candidates.json",
)


def rebuild_5m_candidate_document(
    data: Any,
    *,
    date: str,
    source_path: str,
    source_sha256: str,
) -> dict[str, Any]:
    return rebuild_trusted_candidate_document(
        data,
        date=date,
        source_path=source_path,
        source_sha256=source_sha256,
        target_interval="5m",
    )


def rebuild_trusted_candidate_document(
    data: Any,
    *,
    date: str,
    source_path: str,
    source_sha256: str,
    target_interval: str,
) -> dict[str, Any]:
    bar_source = {
        "1m": "complete_1m_session",
        "5m": "aggregated_from_complete_1m_session",
    }.get(target_interval)
    if bar_source is None:
        raise ValueError(f"unsupported target interval: {target_interval}")
    if not isinstance(data, Mapping) or not isinstance(data.get("candidates"), list):
        raise ValueError("candidate source must be a JSON object with a candidates list")
    if str(data.get("as_of") or "") != date:
        raise ValueError(f"candidate source as_of mismatch: expected {date}, got {data.get('as_of')}")
    rebuilt = deepcopy(dict(data))
    complete_count = 0
    invalid_count = 0
    invalid_reasons: dict[str, int] = {}
    for candidate in rebuilt["candidates"]:
        if not isinstance(candidate, dict):
            continue
        candidate_code = str(candidate.get("code") or "").strip()
        candidate_name = str(candidate.get("name") or "").strip()
        if not candidate_code or not candidate_name:
            raise ValueError("candidate source security identity is required")
        raw_bars = [dict(row) for row in candidate.get("intraday_bars") or [] if isinstance(row, Mapping)]
        validate_bar_security_identity(
            raw_bars,
            code=candidate_code,
            name=candidate_name,
            context=f"candidate {candidate.get('code') or 'missing'}",
        )
        source_security_bars_sha256 = security_bound_bars_sha256(
            raw_bars,
            code=candidate_code,
            name=candidate_name,
        )
        source_bar_count = len(raw_bars)
        complete = validate_complete_a_share_session(raw_bars, interval_minutes=1)
        dated = {
            _timestamp_date(bar_timestamp(row))
            for row in raw_bars
            if _timestamp_date(bar_timestamp(row))
        }
        if complete and dated == {date}:
            target_bars = (
                raw_bars
                if target_interval == "1m"
                else aggregate_complete_1m_session_to_5m(raw_bars)
            )
            candidate["intraday_bars"] = [
                _normalize_aggregated_bar(
                    row,
                    code=candidate_code,
                    name=candidate_name,
                )
                for row in target_bars
            ]
            candidate.update(calculate_intraday_factors(candidate))
            candidate["intraday_bar_identity"] = {
                "bar_interval": target_interval,
                "bar_source": bar_source,
                "complete_session": True,
                "source_1m_bar_count": source_bar_count,
                "bar_count": len(target_bars),
                "invalid_reason": None,
                "source_security_bars_sha256": source_security_bars_sha256,
            }
            complete_count += 1
            continue
        reason = "session_date_mismatch" if complete else "incomplete_1m_session"
        candidate.pop("intraday_bars", None)
        candidate.update(calculate_intraday_factors(candidate))
        candidate["intraday_bar_identity"] = {
            "bar_interval": target_interval,
            "bar_source": bar_source,
            "complete_session": False,
            "source_1m_bar_count": source_bar_count,
            "bar_count": 0,
            "invalid_reason": reason,
            "source_security_bars_sha256": source_security_bars_sha256,
        }
        invalid_count += 1
        invalid_reasons[reason] = invalid_reasons.get(reason, 0) + 1
    identity = {
        "bar_interval": target_interval,
        "bar_source": bar_source,
        "source_bar_interval": "1m",
        "complete_1m_session_required": True,
        "source_path": source_path,
        "source_sha256": source_sha256,
        "derived_output": True,
    }
    rebuilt["intraday_bar_identity"] = identity
    return {
        "data": rebuilt,
        "summary": {
            "date": date,
            "candidate_count": len(rebuilt["candidates"]),
            "complete_candidate_count": complete_count,
            "invalid_candidate_count": invalid_count,
            "invalid_reason_counts": invalid_reasons,
        },
    }


def rebuild_5m_candidate_root(
    *,
    source_root: Path,
    output_root: Path,
    start: str,
    end: str,
) -> dict[str, Any]:
    return rebuild_trusted_candidate_root(
        source_root=source_root,
        output_root=output_root,
        start=start,
        end=end,
        target_interval="5m",
    )


def rebuild_trusted_candidate_root(
    *,
    source_root: Path,
    output_root: Path,
    start: str,
    end: str,
    target_interval: str,
) -> dict[str, Any]:
    resolved_source_root = source_root.resolve()
    resolved_output_root = output_root.resolve()
    if resolved_source_root == resolved_output_root:
        raise ValueError("source and output roots must differ to preserve immutable candidate inputs")
    if (
        resolved_source_root in resolved_output_root.parents
        or resolved_output_root in resolved_source_root.parents
    ):
        raise ValueError("source and output roots must not contain one another")
    bar_source = {
        "1m": "complete_1m_session",
        "5m": "aggregated_from_complete_1m_session",
    }.get(target_interval)
    if bar_source is None:
        raise ValueError(f"unsupported target interval: {target_interval}")
    if end < start:
        raise ValueError("end must be on or after start")
    daily_results = []
    current = datetime.strptime(start, "%Y-%m-%d")
    stop = datetime.strptime(end, "%Y-%m-%d")
    while current <= stop:
        date = current.strftime("%Y-%m-%d")
        source_path = _find_candidate_path(source_root, date)
        if source_path is None:
            daily_results.append({"date": date, "status": "missing_source"})
            current += timedelta(days=1)
            continue
        data, source_sha256 = load_strict_json_with_sha256(source_path)
        rebuilt = rebuild_trusted_candidate_document(
            data,
            date=date,
            source_path=str(source_path),
            source_sha256=source_sha256,
            target_interval=target_interval,
        )
        output_path = output_root / date / "top30_candidates.intraday_backfilled.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        archived = write_text_preserving_previous(
            output_path,
            json.dumps(rebuilt["data"], ensure_ascii=False, indent=2, allow_nan=False),
        )
        daily_results.append(
            {
                **rebuilt["summary"],
                "status": "processed",
                "source_path": str(source_path),
                "source_sha256": source_sha256,
                "output_path": str(output_path),
                "output_sha256": _sha256(output_path),
                "archived_previous_path": str(archived) if archived else None,
            }
        )
        current += timedelta(days=1)
    processed = [item for item in daily_results if item.get("status") == "processed"]
    return {
        "schema_version": "trusted_intraday_candidate_rebuild.v1",
        "source_root": str(source_root),
        "output_root": str(output_root),
        "start": start,
        "end": end,
        "bar_interval": target_interval,
        "bar_source": bar_source,
        "summary": {
            "requested_date_count": len(daily_results),
            "processed_date_count": len(processed),
            "missing_source_date_count": len(daily_results) - len(processed),
            "candidate_count": sum(item.get("candidate_count", 0) for item in processed),
            "complete_candidate_count": sum(item.get("complete_candidate_count", 0) for item in processed),
            "invalid_candidate_count": sum(item.get("invalid_candidate_count", 0) for item in processed),
        },
        "daily_results": daily_results,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }


def _find_candidate_path(root: Path, date: str) -> Path | None:
    for name in CANDIDATE_FILE_NAMES:
        path = root / date / name
        if path.exists():
            return path
    return None


def _normalize_aggregated_bar(row: Mapping[str, Any], *, code: str, name: str) -> dict[str, Any]:
    timestamp = str(bar_timestamp(row) or row.get("date") or "")
    close = row.get("close")
    return {
        "date": timestamp,
        "time": timestamp,
        "code": code,
        "name": name,
        "price": close,
        "close": close,
        "open": row.get("open"),
        "high": row.get("high"),
        "low": row.get("low"),
        "amount": row.get("amount") or 0.0,
        "volume": row.get("volume") or 0.0,
    }


def _timestamp_date(value: Any) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    if len(digits) < 8:
        return ""
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    return (
        "# Trusted Intraday Candidate Rebuild\n\n"
        f"- Source root: `{report.get('source_root')}`\n"
        f"- Output root: `{report.get('output_root')}`\n"
        f"- Range: `{report.get('start')}` to `{report.get('end')}`\n"
        f"- Bar interval: `{report.get('bar_interval')}`\n"
        f"- Bar source: `{report.get('bar_source')}`\n"
        f"- Processed dates: `{summary.get('processed_date_count')}`\n"
        f"- Complete candidates: `{summary.get('complete_candidate_count')}`\n"
        f"- Invalid candidates: `{summary.get('invalid_candidate_count')}`\n"
        "- Paper-only: `True`\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rebuild trustworthy intraday candidate factors from complete 1m sessions")
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--target-interval", required=True, choices=["1m", "5m"])
    args = parser.parse_args(argv)
    report = rebuild_trusted_candidate_root(
        source_root=Path(args.source_root),
        output_root=Path(args.output_root),
        start=args.start,
        end=args.end,
        target_interval=args.target_interval,
    )
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"trusted_{args.target_interval}_candidate_rebuild_{args.start}_{args.end}.json"
    markdown_path = report_dir / f"trusted_{args.target_interval}_candidate_rebuild_{args.start}_{args.end}.md"
    write_text_preserving_previous(
        json_path,
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
    )
    write_text_preserving_previous(markdown_path, _markdown(report))
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
