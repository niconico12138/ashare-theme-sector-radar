"""Capture one prospective ML stock-ranker shadow day and mature old labels."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.data.stock_bars_provider import get_stock_bars_for_factor
from theme_sector_radar.ml.accumulation import (
    archive_daily_snapshot,
    archive_mature_label_snapshot,
    build_archive_readiness_report,
    count_sector_history_dates,
    extract_candidate_snapshot,
)
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)
from theme_sector_radar.data.trading_calendar import load_trading_calendar


def _blocked(path: Path, *, reason: str, error: Exception | None = None) -> int:
    report = {
        "schema_version": "ml-stock-daily-cycle-v1",
        "mode": "paper_shadow_research_only",
        "status": "blocked",
        "reason": reason,
        "error_type": type(error).__name__ if error else None,
        "promotion_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": "Research output only; no broker connection and no live order instruction.",
    }
    validate_no_executable_instructions(report, context="ML daily cycle")
    write_strict_json_atomic(path, report)
    return 2


def _constituent_sources(
    *,
    candidate_snapshot: dict[str, Any],
    root: Path,
    as_of_date: str,
) -> list[dict[str, Any]]:
    sectors = sorted(
        {
            (
                str(row.get("sector_type") or "industry"),
                str(row.get("sector_name") or ""),
            )
            for row in candidate_snapshot["feature_candidates"]
        }
    )
    output: list[dict[str, Any]] = []
    for sector_type, sector_name in sectors:
        path = root / f"{as_of_date}_{sector_type}_{sector_name}.json"
        payload, sha256 = load_strict_json_with_sha256(path)
        if (
            payload.get("as_of_date") != as_of_date
            or payload.get("sector_name") != sector_name
            or not isinstance(payload.get("stocks"), list)
        ):
            raise ValueError(f"dated constituent source identity mismatch: {sector_name}")
        output.append(
            {
                "path": str(path.resolve()),
                "sha256": sha256,
                "as_of_date": as_of_date,
                "sector_name": sector_name,
                "source": payload.get("source"),
            }
        )
    return output


def _fetch_stock_bars(
    codes: list[str], *, as_of_date: str, source: str, cache_dir: Path, lookback: int
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    bars: dict[str, list[dict[str, Any]]] = {}
    source_by_code: dict[str, dict[str, Any]] = {}
    for code in codes:
        result = get_stock_bars_for_factor(
            code,
            as_of_date,
            lookback=lookback,
            source=source,
            cache_dir=cache_dir,
        )
        if result.get("status") != "ok":
            raise ValueError(f"stock bars unavailable for {code}: {result.get('missing_reason')}")
        bars[code] = list(result.get("bars") or [])
        source_by_code[code] = {
            "requested_source": source,
            "actual_source": str(result.get("source") or ""),
            "path": str((cache_dir / f"{code}.json").resolve()),
            "sha256": hashlib.sha256(
                (cache_dir / f"{code}.json").read_bytes()
            ).hexdigest(),
        }
    return bars, source_by_code


def _sector_bars(
    path: Path, *, label_as_of_date: str
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    payload, sha256 = load_strict_json_with_sha256(path)
    rows = payload.get("records")
    if not isinstance(rows, list):
        raise ValueError(f"sector history records are missing: {path}")
    output = []
    for row in rows:
        day = row.get("\u65e5\u671f")
        close = row.get("\u6536\u76d8\u4ef7")
        if day is not None and str(day) <= label_as_of_date:
            output.append({"date": str(day), "close": close})
    return output, {"path": str(path.resolve()), "sha256": sha256}


def _mature_labels(
    *,
    archive_root: Path,
    run_as_of: str,
    bars_source: str,
    stock_bars_cache: Path,
    sector_history_root: Path,
    lookback: int,
) -> list[dict[str, Any]]:
    index, _sha = load_strict_json_with_sha256(archive_root / "index.json")
    results: list[dict[str, Any]] = []
    for entry in index.get("entries") or []:
        signal_date = str(entry.get("as_of_date") or "")
        existing_label_path = archive_root / "labels" / f"{signal_date}.json"
        if existing_label_path.exists():
            _existing_label, existing_sha = load_strict_json_with_sha256(
                existing_label_path
            )
            results.append(
                {
                    "status": "already_captured",
                    "signal_date": signal_date,
                    "label_snapshot_sha256": existing_sha,
                    "promotion_allowed": False,
                }
            )
            continue
        snapshot, _snapshot_sha = load_strict_json_with_sha256(
            archive_root / "snapshots" / f"{signal_date}.json"
        )
        calendar_dates = list(
            (snapshot.get("source_manifest", {}).get("trading_calendar") or {}).get(
                "dates"
            )
            or []
        )
        try:
            target_5d = calendar_dates[calendar_dates.index(signal_date) + 5]
        except (ValueError, IndexError):
            results.append(
                {
                    "status": "pending_calendar_coverage",
                    "signal_date": signal_date,
                    "promotion_allowed": False,
                }
            )
            continue
        if run_as_of < target_5d:
            results.append(
                {
                    "status": "pending_label_maturity",
                    "signal_date": signal_date,
                    "target_5d": target_5d,
                    "promotion_allowed": False,
                }
            )
            continue
        baseline_rows = list(snapshot.get("baseline_rows") or [])
        target_codes = sorted({str(row["stock_code"]) for row in baseline_rows})
        target_sectors = sorted({str(row["sector_name"]) for row in baseline_rows})
        if not target_codes or not target_sectors:
            continue
        try:
            stock_bars, stock_bars_source_by_code = _fetch_stock_bars(
                target_codes,
                as_of_date=run_as_of,
                source=bars_source,
                cache_dir=stock_bars_cache,
                lookback=max(lookback, 80),
            )
            sector_results = {
                sector: _sector_bars(
                    sector_history_root / f"{sector}.json",
                    label_as_of_date=run_as_of,
                )
                for sector in target_sectors
            }
            sector_bars = {
                sector: result[0] for sector, result in sector_results.items()
            }
            sector_bars_source_by_name = {
                sector: result[1] for sector, result in sector_results.items()
            }
            results.append(
                archive_mature_label_snapshot(
                    archive_root=archive_root,
                    signal_date=signal_date,
                    label_as_of_date=run_as_of,
                    stock_bars_by_code=stock_bars,
                    sector_bars_by_name=sector_bars,
                    label_source={
                        "provider": bars_source,
                        "adjustment": "qfq",
                        "frequency": "1d",
                        "query_end": run_as_of,
                        "stock_bars_by_code": stock_bars_source_by_code,
                        "sector_bars_by_name": sector_bars_source_by_name,
                    },
                )
            )
        except (ValueError, OSError, FileNotFoundError) as exc:
            results.append(
                {
                    "status": "pending_source_data",
                    "signal_date": signal_date,
                    "error_type": type(exc).__name__,
                    "reason": str(exc),
                    "promotion_allowed": False,
                }
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unified-report", required=True, type=Path)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--constituent-root", required=True, type=Path)
    parser.add_argument("--sector-history-root", required=True, type=Path)
    parser.add_argument("--trading-calendar-path", required=True, type=Path)
    parser.add_argument("--expected-calendar-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bars-source", choices=("auto", "cache", "http", "stockdb-sdk"), default="auto")
    parser.add_argument("--stock-bars-cache", type=Path, default=PROJECT_ROOT / "data_cache" / "stock_bars")
    parser.add_argument("--lookback", type=int, default=80)
    parser.add_argument("--run-as-of", default=None)
    args = parser.parse_args()

    try:
        report, report_sha = load_strict_json_with_sha256(args.unified_report)
        candidate_snapshot = extract_candidate_snapshot(report)
        as_of_date = candidate_snapshot["as_of_date"]
        calendar = load_trading_calendar(
            args.trading_calendar_path.resolve(),
            as_of=as_of_date,
            include_future=True,
        )
        if calendar["sha256"] != str(args.expected_calendar_sha256).lower():
            raise ValueError("trading calendar SHA mismatch")
        constituent_sources = _constituent_sources(
            candidate_snapshot=candidate_snapshot,
            root=args.constituent_root,
            as_of_date=as_of_date,
        )
        codes = sorted(row["stock_code"] for row in candidate_snapshot["baseline_rows"])
        bars, bars_source_by_code = _fetch_stock_bars(
            codes,
            as_of_date=as_of_date,
            source=args.bars_source,
            cache_dir=args.stock_bars_cache,
            lookback=args.lookback,
        )
        captured = archive_daily_snapshot(
            archive_root=args.archive_root,
            candidate_report=report,
            candidate_source={
                "path": str(args.unified_report.resolve()),
                "sha256": report_sha,
                "generated_at": report.get("generated_at"),
                "as_of_date": as_of_date,
            },
            constituent_sources=constituent_sources,
            bars_by_code=bars,
            bars_source={
                "provider": args.bars_source,
                "adjustment": "qfq",
                "frequency": "1d",
                "query_end": as_of_date,
                "by_code": bars_source_by_code,
            },
            trading_calendar=calendar,
        )
        run_as_of = args.run_as_of or as_of_date
        label_results = _mature_labels(
            archive_root=args.archive_root,
            run_as_of=run_as_of,
            bars_source=args.bars_source,
            stock_bars_cache=args.stock_bars_cache,
            sector_history_root=args.sector_history_root,
            lookback=args.lookback,
        )
        readiness = build_archive_readiness_report(
            args.archive_root,
            sector_history_date_count=count_sector_history_dates(
                args.sector_history_root
            ),
        )
        cycle = {
            "schema_version": "ml-stock-daily-cycle-v1",
            "mode": "paper_shadow_research_only",
            "status": "ready" if readiness["model_training_ready"] else "blocked",
            "as_of_date": as_of_date,
            "run_as_of": run_as_of,
            "snapshot": {
                "path": captured["snapshot_path"],
                "sha256": captured["snapshot_sha256"],
                "created": captured["created"],
            },
            "mature_label_results": label_results,
            "readiness": readiness,
            "promotion_allowed": False,
            "generated_at": datetime.now().astimezone().isoformat(),
            "disclaimer": "Research output only; no broker connection and no live order instruction.",
        }
        validate_no_executable_instructions(cycle, context="ML daily cycle")
        write_strict_json_atomic(args.output, cycle)
        print(
            f"status={cycle['status']} as_of={as_of_date} "
            f"training_ready={readiness['model_training_ready']}"
        )
        return 0
    except (ValueError, OSError, FileNotFoundError) as exc:
        return _blocked(args.output, reason="daily_shadow_capture_blocked", error=exc)


if __name__ == "__main__":
    raise SystemExit(main())
