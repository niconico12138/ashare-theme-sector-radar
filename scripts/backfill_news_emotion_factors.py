#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backfill short-burst market emotion and catalyst shadow factors."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.factors.calculators import calculate_bar_factors  # noqa: E402
from theme_sector_radar.reporting.selection_quality import (  # noqa: E402
    SHORT_BURST_NEWS_EMOTION_FACTOR_IDS,
    classify_stock_candidate,
)


POSITIVE_POLICY_WORDS = ("政策", "规划", "获批", "补贴", "试点", "会议", "方案")
EARNINGS_WORDS = ("业绩", "订单", "回购", "分红", "合同", "增长", "预告")
NEGATIVE_WORDS = ("减持", "问询", "处罚", "亏损", "下跌", "回撤", "澄清")
RUMOR_WORDS = ("传闻", "炒作", "概念", "网传")


def _date_range(start: str, end: str) -> list[str]:
    current = datetime.strptime(start, "%Y-%m-%d")
    stop = datetime.strptime(end, "%Y-%m-%d")
    dates = []
    while current <= stop:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _candidate_path(root: Path, date: str) -> Path | None:
    for name in (
        "top30_candidates.news_emotion_backfilled.json",
        "top30_candidates.intraday_backfilled.json",
        "top30_candidates.analysis_backfilled.json",
        "top30_candidates.factor_backfilled.json",
        "top30_candidates.json",
    ):
        path = root / date / name
        if path.exists():
            return path
    return None


def _load_candidates(path: Path) -> tuple[Any, list[dict]]:
    data = _load_json(path)
    if isinstance(data, list):
        return data, [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("candidates"), list):
        return data, [item for item in data["candidates"] if isinstance(item, dict)]
    return data, []


def _save_candidates(template: Any, candidates: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(template, dict):
        output = dict(template)
        output["candidates"] = candidates
    else:
        output = candidates
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_match_token(value: Any) -> str:
    text = str(value or "").strip().lower()
    return "".join(ch for ch in text if not ch.isspace() and ch not in "｜|,，;；:：()（）[]【】")


def _load_events(cache_root: Path, date: str) -> list[dict]:
    path = cache_root / date / "events.json"
    if not path.exists():
        return []
    data = _load_json(path)
    return [event for event in data.get("events", []) if isinstance(event, dict)]


def _market_proxy(candidates: list[dict]) -> dict[str, float]:
    if not candidates:
        return {}
    short_scores = [_safe_float(c.get("stock_short_score_v2") or c.get("stock_short_score")) for c in candidates]
    risk_scores = [_safe_float(c.get("risk_penalty_score")) for c in candidates]
    leader_scores = [_safe_float(c.get("sector_leader_score")) for c in candidates]
    sectors = [
        str(c.get("sector_name") or c.get("sector") or c.get("theme") or "").strip()
        for c in candidates
    ]
    sector_counts = Counter(sector for sector in sectors if sector)
    concentration = max(sector_counts.values()) / len(candidates) if sector_counts else 0.5
    hot_count = sum(1 for score in short_scores if score >= 70)
    weak_count = sum(1 for score in short_scores if score <= 35)
    failure_proxy = sum(1 for score in risk_scores if score >= 12) / len(candidates)
    leader_rate = sum(1 for score in leader_scores if score >= 70) / len(candidates)
    return {
        "market_limit_up_count": float(hot_count * 6),
        "market_limit_down_count": float(weak_count),
        "market_limit_up_failure_rate": round(failure_proxy, 4),
        "leader_continuation_rate": round(leader_rate, 4),
        "market_hot_sector_concentration": round(concentration, 4),
    }


def _event_stats_by_token(events: list[dict], as_of: str) -> dict[str, dict[str, float]]:
    stats: dict[str, dict[str, float]] = defaultdict(lambda: {
        "news_count_3d": 0.0,
        "policy_catalyst_count": 0.0,
        "earnings_catalyst_count": 0.0,
        "event_age_days": 9.0,
        "event_continuation_days": 0.0,
        "negative_news_count_3d": 0.0,
        "rumor_risk_count": 0.0,
    })
    as_of_dt = datetime.strptime(as_of, "%Y-%m-%d")
    seen_days: dict[str, set[str]] = defaultdict(set)
    for event in events:
        symbols = [str(s).strip() for s in event.get("related_symbols", []) if str(s).strip()]
        symbols.extend(str(s).strip() for s in event.get("related_symbol_names", []) if str(s).strip())
        symbols.extend(str(s).strip() for s in event.get("related_industries", []) if str(s).strip())
        symbols.extend(str(s).strip() for s in event.get("related_concepts", []) if str(s).strip())
        title = str(event.get("title") or "")
        if title:
            symbols.append(title)
        event_date = str(event.get("event_date") or as_of)
        try:
            age = max(0, (as_of_dt - datetime.strptime(event_date, "%Y-%m-%d")).days)
        except ValueError:
            age = 9
        if age > 3:
            continue
        for symbol in symbols:
            bucket = stats[symbol]
            bucket["news_count_3d"] += 1
            bucket["event_age_days"] = min(bucket["event_age_days"], float(age))
            seen_days[symbol].add(event_date)
            if any(word in title for word in POSITIVE_POLICY_WORDS):
                bucket["policy_catalyst_count"] += 1
            if any(word in title for word in EARNINGS_WORDS):
                bucket["earnings_catalyst_count"] += 1
            if any(word in title for word in NEGATIVE_WORDS):
                bucket["negative_news_count_3d"] += 1
            if any(word in title for word in RUMOR_WORDS):
                bucket["rumor_risk_count"] += 1
    for symbol, days in seen_days.items():
        stats[symbol]["event_continuation_days"] = float(len(days))
    return stats


def _candidate_event_tokens(candidate: dict) -> set[str]:
    tokens = {
        str(candidate.get("code", "")).strip(),
        str(candidate.get("name", "")).strip(),
        str(candidate.get("sector_name", "")).strip(),
        str(candidate.get("sector", "")).strip(),
        str(candidate.get("theme", "")).strip(),
    }
    for field in ("boards", "board_types", "leader_tags"):
        values = candidate.get(field)
        if isinstance(values, list):
            tokens.update(str(value).strip() for value in values if str(value).strip())
    return {token for token in tokens if token}


def _merge_event_stats(tokens: set[str], stats_by_token: dict[str, dict[str, float]]) -> dict[str, float]:
    normalized_tokens = [_normalize_match_token(token) for token in tokens]
    matched = []
    seen_keys = set()
    for key, value in stats_by_token.items():
        normalized_key = _normalize_match_token(key)
        if not normalized_key:
            continue
        for token in normalized_tokens:
            if len(token) < 2:
                continue
            if token == normalized_key or token in normalized_key or normalized_key in token:
                if key not in seen_keys:
                    matched.append(value)
                    seen_keys.add(key)
                break
    if not matched:
        return {}
    return {
        "news_count_3d": sum(item["news_count_3d"] for item in matched),
        "policy_catalyst_count": sum(item["policy_catalyst_count"] for item in matched),
        "earnings_catalyst_count": sum(item["earnings_catalyst_count"] for item in matched),
        "event_age_days": min(item["event_age_days"] for item in matched),
        "event_continuation_days": max(item["event_continuation_days"] for item in matched),
        "negative_news_count_3d": sum(item["negative_news_count_3d"] for item in matched),
        "rumor_risk_count": sum(item["rumor_risk_count"] for item in matched),
    }


def _global_event_stats(events: list[dict], as_of: str) -> dict[str, float]:
    if not events:
        return {}
    as_of_dt = datetime.strptime(as_of, "%Y-%m-%d")
    bucket = {
        "news_count_3d": 0.0,
        "policy_catalyst_count": 0.0,
        "earnings_catalyst_count": 0.0,
        "event_age_days": 9.0,
        "event_continuation_days": 0.0,
        "negative_news_count_3d": 0.0,
        "rumor_risk_count": 0.0,
    }
    days = set()
    for event in events:
        title = str(event.get("title") or "")
        event_date = str(event.get("event_date") or as_of)
        try:
            age = max(0, (as_of_dt - datetime.strptime(event_date, "%Y-%m-%d")).days)
        except ValueError:
            age = 9
        if age > 3:
            continue
        bucket["news_count_3d"] += 1
        bucket["event_age_days"] = min(bucket["event_age_days"], float(age))
        days.add(event_date)
        if any(word in title for word in POSITIVE_POLICY_WORDS):
            bucket["policy_catalyst_count"] += 1
        if any(word in title for word in EARNINGS_WORDS):
            bucket["earnings_catalyst_count"] += 1
        if any(word in title for word in NEGATIVE_WORDS):
            bucket["negative_news_count_3d"] += 1
        if any(word in title for word in RUMOR_WORDS):
            bucket["rumor_risk_count"] += 1
    if bucket["news_count_3d"] <= 0:
        return {}
    bucket["event_continuation_days"] = float(len(days))
    return bucket


def _dummy_bars() -> list[dict]:
    return [
        {"date": f"2026-01-{idx + 1:02d}", "close": 100.0 + idx * 0.2, "high": 101.0 + idx * 0.2, "low": 99.0 + idx * 0.2, "amount": 100_000_000.0}
        for idx in range(30)
    ]


def backfill_range(start: str, end: str, candidate_root: Path, catalyst_root: Path) -> dict:
    report = {
        "schema_version": "news_emotion_factor_backfill.v1",
        "start": start,
        "end": end,
        "processed_days": 0,
        "candidate_count": 0,
        "factor_observed_count": 0,
        "event_matched_count": 0,
        "daily_results": [],
    }
    bars = _dummy_bars()
    for date in _date_range(start, end):
        path = _candidate_path(candidate_root, date)
        if path is None:
            report["daily_results"].append({"date": date, "status": "missing_candidate_file"})
            continue
        template, candidates = _load_candidates(path)
        market = _market_proxy(candidates)
        events = _load_events(catalyst_root, date)
        event_stats = _event_stats_by_token(events, date)
        global_stats = _global_event_stats(events, date)
        updated = []
        observed = 0
        matched = 0
        for candidate in candidates:
            enriched = dict(candidate)
            enriched.update(market)
            if global_stats:
                enriched.update(global_stats)
            merged_stats = _merge_event_stats(_candidate_event_tokens(enriched), event_stats)
            if merged_stats:
                enriched.update(merged_stats)
                matched += 1
            factors = calculate_bar_factors(enriched, bars)
            for factor_id in SHORT_BURST_NEWS_EMOTION_FACTOR_IDS:
                value = factors.get(factor_id)
                enriched[factor_id] = value
                if value is not None:
                    observed += 1
            classification = classify_stock_candidate(enriched, str(enriched.get("source_pool") or "burst_top"))
            enriched["short_burst_news_emotion_overlay_shadow"] = classification.get("short_burst_news_emotion_overlay_shadow")
            enriched["short_burst_observation_rank_shadow"] = classification.get("short_burst_observation_rank_shadow")
            enriched["watch_ranking_decision"] = classification.get("watch_ranking_decision", enriched.get("watch_ranking_decision", {}))
            updated.append(enriched)
        output_path = path.parent / "top30_candidates.news_emotion_backfilled.json"
        _save_candidates(template, updated, output_path)
        report["processed_days"] += 1
        report["candidate_count"] += len(updated)
        report["factor_observed_count"] += observed
        report["event_matched_count"] += matched
        report["daily_results"].append({
            "date": date,
            "status": "processed",
            "source_path": str(path),
            "output_path": str(output_path),
            "candidate_count": len(updated),
            "event_count": len(events),
            "event_matched_count": matched,
            "factor_observed_count": observed,
        })
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill short-burst news emotion shadow factors")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--candidate-root", default=str(PROJECT_ROOT / "reports" / "agent_bridge"))
    parser.add_argument("--catalyst-root", default=str(PROJECT_ROOT / "data_cache" / "catalyst_events"))
    parser.add_argument("--report-dir", default=str(PROJECT_ROOT / "reports" / "news_emotion_factor_backfill"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = backfill_range(args.start, args.end, Path(args.candidate_root), Path(args.catalyst_root))
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"news_emotion_factor_backfill_{args.start}_{args.end}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("News emotion backfill complete")
    print(f"Processed days: {report['processed_days']}")
    print(f"Candidates: {report['candidate_count']}")
    print(f"Event matched: {report['event_matched_count']}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
