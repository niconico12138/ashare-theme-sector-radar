#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Next-Day Selection Validation

用次日行情验证当前因子是否真的有筛选力。
对比 decision_score / stock_short_score / trade_eligibility / agent_score 等分组的次日表现。

用法:
  python scripts/evaluate_next_day_selection.py \
    --as-of 2026-07-07 \
    --candidate-path reports/agent_bridge/2026-07-07/top30_candidates.json \
    --ranking-path reports/agent_bridge/2026-07-07/aihf_stock_ranking.json \
    --source stockdb-sdk
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _next_trade_date(date_str: str) -> str:
    """Compute next calendar date (YYYY-MM-DD → YYYYMMDD for SDK)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    nxt = dt + timedelta(days=1)
    return nxt.strftime("%Y%m%d")


def _date_to_compact(date_str: str) -> str:
    """YYYY-MM-DD → YYYYMMDD."""
    return date_str.replace("-", "")


def _safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _compute_group_stats(returns: list[float], highs: list[float], lows: list[float]) -> dict:
    """Compute summary statistics for a group of stocks."""
    if not returns:
        return {
            "candidate_count": 0, "sample_count": 0,
            "avg_next_return_pct": None, "median_next_return_pct": None,
            "hit_rate_positive": None,
            "avg_next_high_return_pct": None, "avg_next_low_return_pct": None,
            "worst_next_return_pct": None, "best_next_return_pct": None,
        }
    n = len(returns)
    avg_ret = sum(returns) / n
    sorted_ret = sorted(returns)
    median_ret = sorted_ret[n // 2] if n % 2 == 1 else (sorted_ret[n // 2 - 1] + sorted_ret[n // 2]) / 2
    positive_count = sum(1 for r in returns if r > 0)
    hit_rate = positive_count / n * 100

    avg_high = sum(highs) / len(highs) if highs else None
    avg_low = sum(lows) / len(lows) if lows else None

    return {
        "candidate_count": n,
        "sample_count": n,
        "avg_next_return_pct": round(avg_ret, 4),
        "median_next_return_pct": round(median_ret, 4),
        "hit_rate_positive": round(hit_rate, 2),
        "avg_next_high_return_pct": round(avg_high, 4) if avg_high is not None else None,
        "avg_next_low_return_pct": round(avg_low, 4) if avg_low is not None else None,
        "worst_next_return_pct": round(min(returns), 4),
        "best_next_return_pct": round(max(returns), 4),
    }


def _split_by_quantile(candidates: list[dict], field: str, n_groups: int = 3) -> dict[str, list[dict]]:
    """Split candidates into quantile groups by a numeric field."""
    valid = [(c, _safe_float(c.get(field, 0))) for c in candidates]
    valid.sort(key=lambda x: x[1], reverse=True)
    n = len(valid)
    group_size = max(1, n // n_groups)
    labels = ["high", "mid", "low"] if n_groups == 3 else [f"group_{i}" for i in range(n_groups)]
    groups: dict[str, list[dict]] = {l: [] for l in labels}
    for i, (c, _) in enumerate(valid):
        g_idx = min(i // group_size, n_groups - 1)
        groups[labels[g_idx]].append(c)
    return groups


def _interpret_signal(
    top_stat: dict | None,
    bot_stat: dict | None,
    min_samples: int = 5,
    threshold: float = 1.0,
) -> dict:
    """Determine if a signal is positive/negative/inconclusive."""
    if not top_stat or not bot_stat:
        return {"signal": "insufficient_samples", "reason": "missing group data"}
    top_n = top_stat.get("sample_count", 0)
    bot_n = bot_stat.get("sample_count", 0)
    if top_n < min_samples or bot_n < min_samples:
        return {"signal": "insufficient_samples", "reason": f"top_n={top_n}, bot_n={bot_n} < {min_samples}"}
    top_avg = top_stat.get("avg_next_return_pct")
    bot_avg = bot_stat.get("avg_next_return_pct")
    if top_avg is None or bot_avg is None:
        return {"signal": "insufficient_samples", "reason": "avg_return is None"}
    gap = top_avg - bot_avg
    if gap > threshold:
        return {"signal": "positive", "gap_pct": round(gap, 4),
                "top_avg": round(top_avg, 4), "bot_avg": round(bot_avg, 4)}
    elif gap < -threshold:
        return {"signal": "negative", "gap_pct": round(gap, 4),
                "top_avg": round(top_avg, 4), "bot_avg": round(bot_avg, 4)}
    else:
        return {"signal": "inconclusive", "gap_pct": round(gap, 4),
                "top_avg": round(top_avg, 4), "bot_avg": round(bot_avg, 4)}


def _fetch_stockdb_bars_bulk(codes: list[str], start: str, end: str) -> dict[str, list[dict]] | None:
    """Fetch daily bars from StockDB without the heavy SDK preload."""
    if not codes:
        return {}
    try:
        import sys
        from pathlib import Path

        sdk_path = Path(os.environ.get("STOCKDB_SDK_PATH", ""))
        if str(sdk_path) not in sys.path:
            sys.path.insert(0, str(sdk_path))
        from stockdb import init

        rd = init(host=os.environ.get("STOCKDB_HOST", "127.0.0.1"), port=int(os.environ.get("STOCKDB_PORT", "7899")), password=os.environ.get("STOCKDB_PASSWORD", ""))
        time_query = start if start == end else f"{start}<{end}"
        grouped: dict[str, list[dict]] = {}
        for code in codes:
            rows = rd.get("日k", str(code), time_query)
            normalized: list[dict] = []
            if isinstance(rows, dict):
                normalized.append(dict(rows))
            else:
                for item in list(rows or []):
                    if isinstance(item, dict):
                        normalized.append(dict(item))
                    elif isinstance(item, (list, tuple)) and len(item) > 1 and isinstance(item[1], dict):
                        normalized.append(dict(item[1]))
            for row in normalized:
                if "date" in row:
                    row["date"] = str(row.get("date", "")).replace("-", "")[:8]
                if "code" in row and row.get("code") is not None:
                    row["code"] = str(row.get("code")).strip()
            grouped[str(code)] = normalized
        return grouped
    except Exception as exc:
        print(f"  StockDB batch read failed, falling back to router: {exc}")
        return None


def fetch_next_day_bars(
    candidates: list[dict],
    as_of: str,
    source: str = "stockdb-sdk",
    horizon: int = 1,
) -> dict[str, dict]:
    """Fetch next-day bars for all candidates. Returns code → bar info dict."""
    try:
        from theme_sector_radar.data.bars_data_router import AutoBarsClient
        client = AutoBarsClient(expected_min_date=_date_to_compact(as_of))
    except Exception as exc:
        print(f"  ⚠️ Failed to init AutoBarsClient: {exc}")
        return {}

    as_of_compact = _date_to_compact(as_of)
    # Fetch a window around the next trade date
    dt_as_of = datetime.strptime(as_of, "%Y-%m-%d")
    end_dt = dt_as_of + timedelta(days=horizon + 5)  # extra buffer for weekends
    start_str = as_of_compact
    end_str = end_dt.strftime("%Y%m%d")

    codes = [str(c.get("code", "")).strip() for c in candidates if c.get("code")]
    bulk_bars = _fetch_stockdb_bars_bulk(codes, start_str, end_str) if source == "stockdb-sdk" else None
    client = None
    if bulk_bars is None:
        try:
            from theme_sector_radar.data.bars_data_router import AutoBarsClient
            client = AutoBarsClient(expected_min_date=_date_to_compact(as_of))
        except Exception as exc:
            print(f"  Failed to init AutoBarsClient: {exc}")
            return {}

    results: dict[str, dict] = {}
    for c in candidates:
        code = c.get("code", "")
        if not code:
            continue
        if bulk_bars is not None:
            bars = bulk_bars.get(str(code), [])
        else:
            try:
                bars = client.get_stock_bars(code, start_str, end_str, frequency="1d", fq="qfq")
            except Exception:
                bars = []

        if not bars:
            results[code] = {"data_available": False}
            continue

        # bars are returned newest-first from SDK; find as_of bar and next bar
        bar_by_date = {}
        for b in bars:
            d = str(b.get("date", "")).replace("-", "")[:8]
            bar_by_date[d] = b

        entry_bar = bar_by_date.get(as_of_compact)
        # Find next trading date (first bar after as_of)
        sorted_dates = sorted(bar_by_date.keys())
        next_date = None
        for d in sorted_dates:
            if d > as_of_compact:
                next_date = d
                break

        if not entry_bar or not next_date:
            results[code] = {"data_available": False}
            continue

        next_bar = bar_by_date[next_date]
        entry_close = _safe_float(entry_bar.get("close"))
        next_close = _safe_float(next_bar.get("close"))
        next_high = _safe_float(next_bar.get("high"))
        next_low = _safe_float(next_bar.get("low"))
        entry_high = _safe_float(entry_bar.get("high"))
        entry_low = _safe_float(entry_bar.get("low"))

        if entry_close <= 0:
            results[code] = {"data_available": False}
            continue

        next_return = (next_close - entry_close) / entry_close * 100
        next_high_return = (next_high - entry_close) / entry_close * 100
        next_low_return = (next_low - entry_close) / entry_close * 100
        # Max intraday drawdown from entry close
        max_dd = min(0, (next_low - entry_close) / entry_close * 100)

        results[code] = {
            "data_available": True,
            "next_trade_date": next_date,
            "entry_close": round(entry_close, 4),
            "next_close": round(next_close, 4),
            "next_high": round(next_high, 4),
            "next_low": round(next_low, 4),
            "next_return_pct": round(next_return, 4),
            "next_high_return_pct": round(next_high_return, 4),
            "next_low_return_pct": round(next_low_return, 4),
            "max_intraday_drawdown_pct": round(max_dd, 4),
        }

    return results


def fetch_next_day_bars_bulk_first(
    candidates: list[dict],
    as_of: str,
    source: str = "stockdb-sdk",
    horizon: int = 1,
) -> dict[str, dict]:
    """Fetch next-day bars, preferring one StockDB batch request for historical runs."""
    as_of_compact = _date_to_compact(as_of)
    dt_as_of = datetime.strptime(as_of, "%Y-%m-%d")
    end_dt = dt_as_of + timedelta(days=horizon + 5)
    start_str = as_of_compact
    end_str = end_dt.strftime("%Y%m%d")

    codes = [str(c.get("code", "")).strip() for c in candidates if c.get("code")]
    bulk_bars = _fetch_stockdb_bars_bulk(codes, start_str, end_str) if source == "stockdb-sdk" else None
    client = None
    if bulk_bars is None:
        try:
            from theme_sector_radar.data.bars_data_router import AutoBarsClient

            client = AutoBarsClient(expected_min_date=_date_to_compact(as_of))
        except Exception as exc:
            print(f"  Failed to init AutoBarsClient: {exc}")
            return {}

    results: dict[str, dict] = {}
    for c in candidates:
        code = c.get("code", "")
        if not code:
            continue
        if bulk_bars is not None:
            bars = bulk_bars.get(str(code), [])
        else:
            try:
                bars = client.get_stock_bars(code, start_str, end_str, frequency="1d", fq="qfq")
            except Exception:
                bars = []

        if not bars:
            results[code] = {"data_available": False}
            continue

        bar_by_date = {}
        for b in bars:
            d = str(b.get("date", "")).replace("-", "")[:8]
            bar_by_date[d] = b

        entry_bar = bar_by_date.get(as_of_compact)
        sorted_dates = sorted(bar_by_date.keys())
        next_date = None
        for d in sorted_dates:
            if d > as_of_compact:
                next_date = d
                break

        if not entry_bar or not next_date:
            results[code] = {"data_available": False}
            continue

        next_bar = bar_by_date[next_date]
        entry_close = _safe_float(entry_bar.get("close"))
        next_close = _safe_float(next_bar.get("close"))
        next_high = _safe_float(next_bar.get("high"))
        next_low = _safe_float(next_bar.get("low"))

        if entry_close <= 0:
            results[code] = {"data_available": False}
            continue

        next_return = (next_close - entry_close) / entry_close * 100
        next_high_return = (next_high - entry_close) / entry_close * 100
        next_low_return = (next_low - entry_close) / entry_close * 100
        max_dd = min(0, (next_low - entry_close) / entry_close * 100)

        results[code] = {
            "data_available": True,
            "next_trade_date": next_date,
            "entry_close": round(entry_close, 4),
            "next_close": round(next_close, 4),
            "next_high": round(next_high, 4),
            "next_low": round(next_low, 4),
            "next_return_pct": round(next_return, 4),
            "next_high_return_pct": round(next_high_return, 4),
            "next_low_return_pct": round(next_low_return, 4),
            "max_intraday_drawdown_pct": round(max_dd, 4),
        }

    return results


def run_validation(
    candidates: list[dict],
    bar_data: dict[str, dict],
    ranking_items: list[dict],
    as_of: str,
) -> dict:
    """Run full validation analysis."""
    # Enrich candidates with bar data and ranking data
    ranking_lookup = {str(r.get("code", "")): r for r in ranking_items}

    enriched = []
    for c in candidates:
        code = c.get("code", "")
        bar = bar_data.get(code, {})
        rank = ranking_lookup.get(code, {})

        entry = dict(c)
        entry["bar_data"] = bar
        entry["agent_score_from_ranking"] = rank.get("agent_score")
        entry["risk_level_from_ranking"] = rank.get("risk_level")
        entry["risk_adjusted_score_from_ranking"] = rank.get("risk_adjusted_score")
        # Merge agent fields if not already in candidate
        if entry.get("agent_score") is None and rank.get("agent_score") is not None:
            entry["agent_score"] = rank["agent_score"]
        if entry.get("risk_level") is None and rank.get("risk_level") is not None:
            entry["risk_level"] = rank["risk_level"]
        enriched.append(entry)

    # Filter to available data
    available = [e for e in enriched if e.get("bar_data", {}).get("data_available")]
    missing = [e for e in enriched if not e.get("bar_data", {}).get("data_available")]

    def _returns(cands):
        return [c["bar_data"]["next_return_pct"] for c in cands if c.get("bar_data", {}).get("data_available")]

    def _highs(cands):
        return [c["bar_data"]["next_high_return_pct"] for c in cands if c.get("bar_data", {}).get("data_available")]

    def _lows(cands):
        return [c["bar_data"]["next_low_return_pct"] for c in cands if c.get("bar_data", {}).get("data_available")]

    def _group_stats(cands):
        return _compute_group_stats(_returns(cands), _highs(cands), _lows(cands))

    # === A. Ranking Groups ===
    sorted_by_decision = sorted(available, key=lambda x: _safe_float(x.get("decision_score", 0)), reverse=True)
    ranking_groups = {
        "top1_by_decision_score": _group_stats(sorted_by_decision[:1]),
        "top3_by_decision_score": _group_stats(sorted_by_decision[:3]),
        "top5_by_decision_score": _group_stats(sorted_by_decision[:5]),
        "top10_by_decision_score": _group_stats(sorted_by_decision[:10]),
        "bottom10_by_decision_score": _group_stats(sorted_by_decision[-10:]),
    }

    # === B. Score Buckets ===
    score_buckets = {}
    for field in ["decision_score", "stock_short_score", "stock_trend_score"]:
        groups = _split_by_quantile(available, field, 3)
        for label, cands in groups.items():
            score_buckets[f"{field}_{label}"] = _group_stats(cands)

    # Agent score buckets
    agent_with_score = [e for e in available if _safe_float(e.get("agent_score")) > 0]
    agent_missing = [e for e in available if e.get("agent_score") is None or _safe_float(e.get("agent_score")) == 0]
    if agent_with_score:
        agent_groups = _split_by_quantile(agent_with_score, "agent_score", 3)
        for label, cands in agent_groups.items():
            score_buckets[f"agent_score_{label}"] = _group_stats(cands)
    score_buckets["agent_score_missing"] = _group_stats(agent_missing)

    # === C. Categorical Groups ===
    categorical = {}

    # Trade eligibility
    for elig in ["focus", "watch", "backup", "avoid"]:
        group = [e for e in available if e.get("trade_eligibility") == elig]
        categorical[f"trade_eligibility_{elig}"] = _group_stats(group)

    # Source pool
    for pool in ["trend", "burst", "both"]:
        group = [e for e in available if e.get("source_pool") == pool]
        categorical[f"source_pool_{pool}"] = _group_stats(group)

    # Agent analysis status
    analyzed = [e for e in available if e.get("agent_analysis_status") in ("pending_agent_analysis", "analyzed")]
    skipped = [e for e in available if e.get("agent_analysis_status") == "skipped_by_agent_stock_limit"]
    categorical["analyzed"] = _group_stats(analyzed)
    categorical["skipped_by_agent_stock_limit"] = _group_stats(skipped)

    # Risk level from ranking
    for level in ["low", "medium", "high"]:
        group = [e for e in available if e.get("risk_level") == level or e.get("risk_level_from_ranking") == level]
        categorical[f"risk_level_{level}"] = _group_stats(group)
    categorical["risk_level_missing"] = _group_stats(
        [e for e in available if not e.get("risk_level") and not e.get("risk_level_from_ranking")]
    )

    # === Interpretation ===
    interpretation = {}

    # Decision score signal
    top5 = ranking_groups["top5_by_decision_score"]
    bot10 = ranking_groups["bottom10_by_decision_score"]
    interpretation["decision_score_signal"] = _interpret_signal(top5, bot10)

    # Stock short score signal
    short_high = score_buckets.get("stock_short_score_high", {})
    short_low = score_buckets.get("stock_short_score_low", {})
    interpretation["stock_short_score_signal"] = _interpret_signal(short_high, short_low)

    # Trade eligibility signal
    focus_stat = categorical.get("trade_eligibility_focus", {})
    avoid_stat = categorical.get("trade_eligibility_avoid", {})
    interpretation["trade_eligibility_signal"] = _interpret_signal(focus_stat, avoid_stat)

    # Agent incremental signal
    analyzed_stat = categorical.get("analyzed", {})
    skipped_stat = categorical.get("skipped_by_agent_stock_limit", {})
    interpretation["analyzed_vs_skipped_signal"] = _interpret_signal(analyzed_stat, skipped_stat)

    # Agent score signal
    agent_high = score_buckets.get("agent_score_high", {})
    agent_miss = score_buckets.get("agent_score_missing", {})
    interpretation["agent_incremental_signal"] = _interpret_signal(agent_high, agent_miss)

    # Trend vs burst signal
    trend_stat = categorical.get("source_pool_trend", {})
    burst_stat = categorical.get("source_pool_burst", {})
    interpretation["trend_vs_burst_signal"] = _interpret_signal(burst_stat, trend_stat)

    # Add caution
    interpretation["caution"] = "single-day validation only; not enough for weight changes"

    # Coverage
    coverage = {
        "total_candidates": len(candidates),
        "data_available": len(available),
        "data_missing": len(missing),
        "missing_codes": [m.get("code") for m in missing],
    }

    return {
        "as_of": as_of,
        "horizon": 1,
        "generated_at": datetime.now().isoformat(),
        "coverage": coverage,
        "ranking_groups": ranking_groups,
        "score_buckets": score_buckets,
        "categorical_groups": categorical,
        "interpretation": interpretation,
        "per_stock": [
            {
                "code": e.get("code"),
                "name": e.get("name"),
                "decision_score": e.get("decision_score"),
                "stock_short_score": e.get("stock_short_score"),
                "trade_eligibility": e.get("trade_eligibility"),
                "source_pool": e.get("source_pool"),
                "agent_score": e.get("agent_score"),
                "next_return_pct": e.get("bar_data", {}).get("next_return_pct"),
                "data_available": e.get("bar_data", {}).get("data_available", False),
            }
            for e in enriched
        ],
    }


def generate_markdown(report: dict) -> str:
    """Generate markdown validation report."""
    lines = []
    as_of = report.get("as_of", "?")
    lines.append(f"# Next-Day Selection Validation — {as_of}")
    lines.append(f"")
    lines.append(f"> **single-day validation only; not enough for weight changes.**")
    lines.append(f"")
    lines.append(f"Generated: {report.get('generated_at', '')}")
    lines.append(f"")

    # Coverage
    cov = report.get("coverage", {})
    lines.append(f"## 1. Data Coverage")
    lines.append(f"")
    lines.append(f"- Total candidates: {cov.get('total_candidates', 0)}")
    lines.append(f"- Data available: {cov.get('data_available', 0)}")
    lines.append(f"- Data missing: {cov.get('data_missing', 0)}")
    missing_codes = cov.get("missing_codes", [])
    if missing_codes:
        lines.append(f"- Missing codes: {', '.join(missing_codes)}")
    lines.append(f"")

    # Decision score results
    rg = report.get("ranking_groups", {})
    lines.append(f"## 2. Top Decision Score Results")
    lines.append(f"")
    for key in ["top1_by_decision_score", "top3_by_decision_score", "top5_by_decision_score",
                 "top10_by_decision_score", "bottom10_by_decision_score"]:
        stat = rg.get(key, {})
        n = stat.get("sample_count", 0)
        avg = stat.get("avg_next_return_pct")
        hit = stat.get("hit_rate_positive")
        avg_s = f"{avg:.2f}" if avg is not None else "N/A"
        hit_s = f"{hit:.1f}" if hit is not None else "N/A"
        lines.append(f"- **{key}** (n={n}): avg_return={avg_s}%, hit_rate={hit_s}%")
    lines.append(f"")

    # Score bucket validation
    lines.append(f"## 3. Score Bucket Validation")
    lines.append(f"")
    sb = report.get("score_buckets", {})
    lines.append(f"| {'Group':<35} {'n':>4} {'avg_ret%':>9} {'median%':>9} {'hit%':>6} {'best%':>8} {'worst%':>8} |")
    lines.append(f"|{'─'*37}|{'─'*6}|{'─'*11}|{'─'*11}|{'─'*8}|{'─'*10}|{'─'*10}|")
    for key in ["decision_score_high", "decision_score_mid", "decision_score_low",
                 "stock_short_score_high", "stock_short_score_mid", "stock_short_score_low",
                 "stock_trend_score_high", "stock_trend_score_mid", "stock_trend_score_low",
                 "agent_score_high", "agent_score_mid", "agent_score_low", "agent_score_missing"]:
        stat = sb.get(key, {})
        n = stat.get("sample_count", 0)
        avg = stat.get("avg_next_return_pct")
        med = stat.get("median_next_return_pct")
        hit = stat.get("hit_rate_positive")
        best = stat.get("best_next_return_pct")
        worst = stat.get("worst_next_return_pct")
        avg_s = f"{avg:.2f}" if avg is not None else "N/A"
        med_s = f"{med:.2f}" if med is not None else "N/A"
        hit_s = f"{hit:.1f}" if hit is not None else "N/A"
        best_s = f"{best:.2f}" if best is not None else "N/A"
        worst_s = f"{worst:.2f}" if worst is not None else "N/A"
        lines.append(f"| {key:<35} {n:>4} {avg_s:>9} {med_s:>9} {hit_s:>6} {best_s:>8} {worst_s:>8} |")
    lines.append(f"")

    # Trade eligibility validation
    lines.append(f"## 4. Trade Eligibility Validation")
    lines.append(f"")
    cat = report.get("categorical_groups", {})
    lines.append(f"| {'Category':<35} {'n':>4} {'avg_ret%':>9} {'hit%':>6} |")
    lines.append(f"|{'─'*37}|{'─'*6}|{'─'*11}|{'─'*8}|")
    for key in ["trade_eligibility_focus", "trade_eligibility_watch", "trade_eligibility_backup", "trade_eligibility_avoid"]:
        stat = cat.get(key, {})
        n = stat.get("sample_count", 0)
        avg = stat.get("avg_next_return_pct")
        hit = stat.get("hit_rate_positive")
        avg_s = f"{avg:.2f}" if avg is not None else "N/A"
        hit_s = f"{hit:.1f}" if hit is not None else "N/A"
        lines.append(f"| {key:<35} {n:>4} {avg_s:>9} {hit_s:>6} |")
    lines.append(f"")

    # Agent incremental validation
    lines.append(f"## 5. Agent Incremental Validation")
    lines.append(f"")
    for key in ["analyzed", "skipped_by_agent_stock_limit"]:
        stat = cat.get(key, {})
        n = stat.get("sample_count", 0)
        avg = stat.get("avg_next_return_pct")
        hit = stat.get("hit_rate_positive")
        avg_s = f"{avg:.2f}" if avg is not None else "N/A"
        hit_s = f"{hit:.1f}" if hit is not None else "N/A"
        lines.append(f"- **{key}** (n={n}): avg_return={avg_s}%, hit_rate={hit_s}%")
    lines.append(f"")

    # Trend vs burst
    lines.append(f"## 6. Trend vs Burst Validation")
    lines.append(f"")
    for key in ["source_pool_trend", "source_pool_burst", "source_pool_both"]:
        stat = cat.get(key, {})
        n = stat.get("sample_count", 0)
        avg = stat.get("avg_next_return_pct")
        hit = stat.get("hit_rate_positive")
        avg_s = f"{avg:.2f}" if avg is not None else "N/A"
        hit_s = f"{hit:.1f}" if hit is not None else "N/A"
        lines.append(f"- **{key}** (n={n}): avg_return={avg_s}%, hit_rate={hit_s}%")
    lines.append(f"")

    # Interpretation
    interp = report.get("interpretation", {})
    lines.append(f"## 7. Interpretation")
    lines.append(f"")
    for key in ["decision_score_signal", "stock_short_score_signal", "trade_eligibility_signal",
                 "agent_incremental_signal", "analyzed_vs_skipped_signal", "trend_vs_burst_signal"]:
        sig = interp.get(key, {})
        signal = sig.get("signal", "?")
        icon = "✅" if signal == "positive" else "❌" if signal == "negative" else "⚠️"
        gap = sig.get("gap_pct")
        gap_s = f", gap={gap:.2f}pp" if gap is not None else ""
        reason = sig.get("reason", "")
        reason_s = f" ({reason})" if reason else ""
        lines.append(f"- {icon} **{key}**: {signal}{gap_s}{reason_s}")
    lines.append(f"")

    # Cautions
    lines.append(f"## 8. Cautions / Limitations")
    lines.append(f"")
    lines.append(f"- This is a **single-day validation** based on {as_of} → next trading day.")
    lines.append(f"- Sample sizes are small (n≤30); results are **not statistically significant**.")
    lines.append(f"- **Do not change weights** based on this report alone.")
    lines.append(f"- Need multi-day / rolling window validation before any parameter adjustment.")
    lines.append(f"- Market regime on {as_of} may not generalize.")
    lines.append(f"")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Evaluate next-day selection quality")
    parser.add_argument("--as-of", required=True, help="Date YYYY-MM-DD")
    parser.add_argument("--candidate-path", required=True, help="Path to top30_candidates.json")
    parser.add_argument("--ranking-path", required=True, help="Path to aihf_stock_ranking.json")
    parser.add_argument("--source", default="stockdb-sdk", help="Data source")
    parser.add_argument("--horizon", type=int, default=1, help="Forward days")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output")
    args = parser.parse_args()

    candidate_path = Path(args.candidate_path)
    ranking_path = Path(args.ranking_path)

    if not candidate_path.exists():
        print(f"❌ Candidate file not found: {candidate_path}")
        sys.exit(1)

    # Load candidates
    candidate_data = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidates = candidate_data.get("candidates", [])

    # Load ranking (optional)
    ranking_items = []
    if ranking_path.exists():
        ranking_data = json.loads(ranking_path.read_text(encoding="utf-8"))
        ranking_items = ranking_data.get("items", [])

    print(f"  Loading {len(candidates)} candidates, {len(ranking_items)} ranking items...")

    # Fetch next-day bars
    print(f"  Fetching next-day bars (horizon={args.horizon})...")
    bar_data = fetch_next_day_bars_bulk_first(candidates, args.as_of, args.source, args.horizon)
    available = sum(1 for v in bar_data.values() if v.get("data_available"))
    print(f"  Data available: {available}/{len(candidates)}")

    # Run validation
    report = run_validation(candidates, bar_data, ranking_items, args.as_of)

    # Output
    out_dir = Path(args.output_dir) if args.output_dir else (
        PROJECT_ROOT / "reports" / "selection_validation" / args.as_of
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "next_day_selection_validation.json"
    if json_path.exists() and not args.force:
        print(f"  ⚠️ Output exists, use --force to overwrite: {json_path}")
    else:
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ JSON saved: {json_path}")

    md = generate_markdown(report)
    md_path = out_dir / "next_day_selection_validation.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  ✅ Markdown saved: {md_path}")

    # Print summary
    interp = report.get("interpretation", {})
    print(f"\n=== Interpretation Summary ===")
    for key in ["decision_score_signal", "stock_short_score_signal", "trade_eligibility_signal",
                 "agent_incremental_signal", "analyzed_vs_skipped_signal", "trend_vs_burst_signal"]:
        sig = interp.get(key, {})
        signal = sig.get("signal", "?")
        gap = sig.get("gap_pct")
        icon = "✅" if signal == "positive" else "❌" if signal == "negative" else "⚠️"
        gap_s = f" gap={gap:.2f}pp" if gap is not None else ""
        print(f"  {icon} {key}: {signal}{gap_s}")
    print(f"\n  ⚠️ {interp.get('caution', '')}")


if __name__ == "__main__":
    main()

