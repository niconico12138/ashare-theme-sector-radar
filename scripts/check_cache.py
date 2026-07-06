"""
Check catalyst cache and sector research output for a given date.
Usage:
    python scripts/check_cache.py
    python scripts/check_cache.py 2026-06-29
    python scripts/check_cache.py --date 2026-06-29
"""
import argparse
import json
import sys
from pathlib import Path

# Resolve project root relative to this script (no hardcoded paths)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Check catalyst cache for a given date")
    parser.add_argument(
        "date_positional",
        nargs="?",
        default=None,
        help="Date to check (default: 2026-06-29)",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Date to check (default: 2026-06-29)",
    )
    args = parser.parse_args()

    date_str = args.date or args.date_positional or "2026-06-29"

    # --- Catalyst cache ---
    cache_path = PROJECT_ROOT / "data_cache" / "catalyst_events" / date_str / "events.json"
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"=== Catalyst Cache {date_str} ===")
        print(f"event_count: {data.get('event_count', 0)}")
        events = data.get("events", [])
        sources = {}
        mapped = 0
        unmapped = 0
        for e in events:
            src = e.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1
            if e.get("related_industries") or e.get("related_concepts"):
                mapped += 1
            else:
                unmapped += 1
        print(f"sources: {sources}")
        print(f"mapped: {mapped}, unmapped: {unmapped}")
        for e in events[:3]:
            print(f"  source={e.get('source')}, title={e.get('title', '')[:60]}")
    else:
        print(f"Catalyst cache NOT FOUND for {date_str}")

    # --- Source status ---
    status_path = PROJECT_ROOT / "data_cache" / "catalyst_events" / date_str / "source_status.json"
    if status_path.exists():
        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)
        print(f"\n=== Source Status {date_str} ===")
        for s in status.get("sources", []):
            print(
                f"  {s.get('source_id')}: status={s.get('status')}, "
                f"success={s.get('success_count')}, failed={s.get('failed_count')}"
            )
    else:
        print(f"\nSource status NOT FOUND for {date_str}")

    # --- Sector research ---
    research_path = PROJECT_ROOT / "reports" / "sector_research" / date_str / "sector_research.json"
    if research_path.exists():
        with open(research_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        results = data.get("research_results", [])
        names = [r.get("sector_name", "") for r in results[:10]]
        print(f"\n=== Sector Research {date_str} ===")
        print(f"sector_count: {len(results)}")
        print(f"top 10: {names}")
    else:
        print(f"\nSector research NOT FOUND for {date_str}")


if __name__ == "__main__":
    main()
