#!/usr/bin/env python
"""Build a validated, versioned sector-history root from an incremental fetch."""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import shutil
import sys
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.downloader.sector_history_downloader import (
    SectorHistoryDownloader,
)
from theme_sector_radar.models import SectorType
from theme_sector_radar.reporting.strict_json import (
    load_strict_json,
    write_strict_json_atomic,
)


DATE_FIELD = "日期"
NUMERIC_FIELDS = ("开盘价", "最高价", "最低价", "收盘价", "成交量", "成交额")


def validate_history_document(
    document: Any,
    *,
    expected_name: str,
) -> list[str]:
    """Validate one complete or incremental THS industry-history document."""
    if not isinstance(document, dict):
        raise ValueError("history document must be an object")
    if document.get("sector_name") != expected_name:
        raise ValueError("history sector_name does not match expected name")
    if document.get("sector_type") != SectorType.INDUSTRY.value:
        raise ValueError("history sector_type must be industry")
    records = document.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("history records must be a non-empty list")

    dates: list[str] = []
    seen: set[str] = set()
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("history record must be an object")
        raw_date = row.get(DATE_FIELD)
        if not isinstance(raw_date, str):
            raise ValueError("history date must be ISO text")
        try:
            parsed = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise ValueError("history date must be canonical ISO") from exc
        if parsed.isoformat() != raw_date:
            raise ValueError("history date must be canonical ISO")
        if raw_date in seen:
            raise ValueError(f"duplicate history date: {raw_date}")
        seen.add(raw_date)
        dates.append(raw_date)

        values: dict[str, float] = {}
        for field in NUMERIC_FIELDS:
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"history {field} must be numeric")
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(f"history {field} must be finite")
            values[field] = number
        if any(values[field] <= 0 for field in ("开盘价", "最高价", "最低价", "收盘价")):
            raise ValueError("history OHLC values must be positive")
        if values["成交量"] < 0 or values["成交额"] < 0:
            raise ValueError("history volume and turnover must be non-negative")
        if not (
            values["最低价"]
            <= min(values["开盘价"], values["收盘价"])
            <= max(values["开盘价"], values["收盘价"])
            <= values["最高价"]
        ):
            raise ValueError("history OHLC relationship is invalid")

    if dates != sorted(dates):
        raise ValueError("history dates must be strictly increasing")
    metadata_start = document.get("start_date")
    metadata_end = document.get("end_date")
    try:
        start = date.fromisoformat(metadata_start)
        end = date.fromisoformat(metadata_end)
    except (TypeError, ValueError) as exc:
        raise ValueError("history metadata date range must be canonical ISO") from exc
    if start.isoformat() != metadata_start or end.isoformat() != metadata_end:
        raise ValueError("history metadata date range must be canonical ISO")
    if metadata_start > dates[0] or metadata_end < dates[-1]:
        raise ValueError("history metadata date range does not contain records")
    return dates


def merge_history_documents(
    existing: dict[str, Any],
    increment: dict[str, Any],
) -> dict[str, Any]:
    """Merge a validated increment without changing existing rows."""
    name = existing.get("sector_name")
    if not isinstance(name, str) or not name:
        raise ValueError("existing history sector_name is missing")
    validate_history_document(existing, expected_name=name)
    validate_history_document(increment, expected_name=name)

    merged_by_date = {row[DATE_FIELD]: dict(row) for row in existing["records"]}
    for row in increment["records"]:
        row_date = row[DATE_FIELD]
        if row_date in merged_by_date and merged_by_date[row_date] != row:
            raise ValueError(f"conflicting record for {name} on {row_date}")
        merged_by_date.setdefault(row_date, dict(row))

    records = [merged_by_date[key] for key in sorted(merged_by_date)]
    merged = dict(existing)
    merged.update(
        {
            "start_date": existing["start_date"],
            "end_date": records[-1][DATE_FIELD],
            "fetched_at": increment.get("fetched_at"),
            "records": records,
        }
    )
    validate_history_document(merged, expected_name=name)
    return merged


def update_sector_history(
    *,
    source_root: Path,
    output_root: Path,
    start_date: str,
    end_date: str,
    expected_sector_count: int = 90,
    sleep_seconds: float = 0.2,
) -> dict[str, Any]:
    """Fetch all frozen-universe increments and publish a new complete root."""
    source_root = source_root.resolve(strict=True)
    source_dir = source_root / "industry"
    if not source_dir.is_dir():
        raise ValueError(f"source industry directory is missing: {source_dir}")
    output_root = output_root.resolve(strict=False)
    if output_root.exists():
        raise FileExistsError(f"output root already exists: {output_root}")

    source_paths = sorted(source_dir.glob("*.json"), key=lambda path: path.name)
    if len(source_paths) != expected_sector_count:
        raise ValueError(
            f"expected {expected_sector_count} source sectors, found {len(source_paths)}"
        )
    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root = output_root.parent / f".{output_root.name}.staging-{uuid.uuid4().hex}"
    staging_dir = staging_root / "industry"
    staging_dir.mkdir(parents=True)

    downloader = SectorHistoryDownloader(sleep_seconds=sleep_seconds)
    documents = []
    common_increment_dates: list[str] | None = None
    try:
        for index, source_path in enumerate(source_paths, 1):
            existing = load_strict_json(source_path)
            name = existing.get("sector_name")
            if not isinstance(name, str) or not name:
                raise ValueError(f"source sector_name is missing: {source_path}")
            old_dates = validate_history_document(existing, expected_name=name)
            increment = downloader.download_sector_history(
                name,
                SectorType.INDUSTRY,
                start_date.replace("-", ""),
                end_date.replace("-", ""),
            )
            if increment is None:
                raise ValueError(f"incremental fetch failed for {name}")
            increment = {
                **increment,
                "start_date": start_date,
                "end_date": end_date,
            }
            increment_dates = validate_history_document(increment, expected_name=name)
            if common_increment_dates is None:
                common_increment_dates = increment_dates
            elif increment_dates != common_increment_dates:
                raise ValueError(f"increment date set differs for {name}")
            merged = merge_history_documents(existing, increment)
            target_path = staging_dir / source_path.name
            write_strict_json_atomic(target_path, merged)
            documents.append(
                {
                    "sector_name": name,
                    "relative_path": f"industry/{source_path.name}",
                    "old_sha256": _sha256(source_path),
                    "increment_sha256": _payload_sha256(increment),
                    "merged_sha256": _sha256(target_path),
                    "old_record_count": len(old_dates),
                    "increment_record_count": len(increment_dates),
                    "merged_record_count": len(merged["records"]),
                }
            )
            print(f"[{index}/{len(source_paths)}] {name}: {len(increment_dates)} rows")
            if index < len(source_paths) and sleep_seconds > 0:
                time.sleep(sleep_seconds)

        if not common_increment_dates:
            raise ValueError("increment did not contain any dates")
        if common_increment_dates[0] < start_date or common_increment_dates[-1] != end_date:
            raise ValueError("increment date coverage does not reach requested end date")
        manifest = {
            "schema_version": "sector_history_incremental_update.v1",
            "source_root": str(source_root),
            "output_root": str(output_root),
            "sector_type": "industry",
            "sector_count": len(documents),
            "requested_start_date": start_date,
            "requested_end_date": end_date,
            "increment_dates": common_increment_dates,
            "source_unchanged": True,
            "publication_mode": "same_parent_atomic_directory_rename",
            "documents": documents,
        }
        write_strict_json_atomic(staging_root / "update_manifest.json", manifest)
        os.replace(staging_root, output_root)
        return manifest
    except Exception:
        shutil.rmtree(staging_root, ignore_errors=True)
        raise


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _payload_sha256(payload: Any) -> str:
    import json

    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--expected-sector-count", type=int, default=90)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    args = parser.parse_args()
    for value in (args.start_date, args.end_date):
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError("dates must be canonical ISO")
    if args.start_date > args.end_date:
        raise ValueError("start-date must not exceed end-date")
    manifest = update_sector_history(
        source_root=args.source_root,
        output_root=args.output_root,
        start_date=args.start_date,
        end_date=args.end_date,
        expected_sector_count=args.expected_sector_count,
        sleep_seconds=args.sleep_seconds,
    )
    print(f"published {manifest['sector_count']} sectors to {manifest['output_root']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
