"""Phase 52 helper: check catalyst cache and sector_research data"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)

def check_catalyst_cache(date_str):
    """Check events.json and source_status.json for a given date"""
    cache_dir = f"data_cache/catalyst_events/{date_str}"
    events_path = os.path.join(cache_dir, "events.json")
    status_path = os.path.join(cache_dir, "source_status.json")

    print(f"=== Catalyst Cache: {date_str} ===")

    if not os.path.exists(events_path):
        print(f"  events.json: NOT FOUND")
        return None

    with open(events_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    event_count = data.get("event_count", 0)
    events = data.get("events", [])
    print(f"  event_count: {event_count}")

    source_counts = {}
    mapped_count = 0
    unmapped_count = 0
    for e in events:
        src = e.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
        if e.get("related_industries") or e.get("related_concepts"):
            mapped_count += 1
        else:
            unmapped_count += 1

    print(f"  sources: {source_counts}")
    print(f"  mapped: {mapped_count}, unmapped: {unmapped_count}")

    if os.path.exists(status_path):
        with open(status_path, "r", encoding="utf-8") as f:
            status = json.load(f)
        sources = status.get("sources", [])
        print(f"  source_status entries: {len(sources)}")
        for s in sources:
            print(f"    - {s.get('source_id')}: status={s.get('status')}, success={s.get('success_count')}, failed={s.get('failed_count')}")
    else:
        print(f"  source_status.json: NOT FOUND")

    return data

def check_sector_research(date_str):
    """Check sector_research for a given date"""
    path = f"reports/sector_research/{date_str}/sector_research.json"
    print(f"\n=== Sector Research: {date_str} ===")

    if not os.path.exists(path):
        print(f"  NOT FOUND")
        return None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("research_results", [])
    names = [r.get("sector_name", "") for r in results[:10]]
    print(f"  sector_count: {len(results)}")
    print(f"  top 10: {names}")
    return data

if __name__ == "__main__":
    date_str = sys.argv[1] if len(sys.argv) > 1 else "2026-06-29"
    check_catalyst_cache(date_str)
    check_sector_research(date_str)
