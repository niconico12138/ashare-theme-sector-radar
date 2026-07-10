#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量选股验证脚本

对多个历史日期运行 next-day selection validation，汇总因子筛选力。
支持重算候选或使用已有产物。

用法:
  python scripts/run_selection_validation_batch.py \
    --dates 2026-06-29 2026-07-01 2026-07-02 2026-07-03 2026-07-06 2026-07-07 \
    --mode recompute-candidates \
    --source stockdb-sdk \
    --horizon 1 \
    --agent-stock-limit 10 \
    --skip-agent-refresh \
    --force
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.evaluate_next_day_selection import (
    _compute_group_stats,
    _safe_float,
    fetch_next_day_bars,
    run_validation,
    generate_markdown,
)

OUTPUT_DIR = PROJECT_ROOT / "reports" / "selection_validation"


def _scan_available_dates() -> list[str]:
    """Scan reports/unified for available dates."""
    unified_dir = PROJECT_ROOT / "reports" / "unified"
    dates = []
    for d in sorted(unified_dir.iterdir()):
        if d.is_dir() and d.name.startswith("2026"):
            report = d / "unified_report.json"
            if report.exists():
                dates.append(d.name)
    return dates


def _run_export(date: str, stock_limit: int, agent_stock_limit: int) -> bool:
    """Run export_top30_candidates.py for a single date."""
    script = PROJECT_ROOT / "scripts" / "export_top30_candidates.py"
    cmd = [
        sys.executable, str(script),
        "--as-of", date,
        "--stock-limit", str(stock_limit),
        "--agent-stock-limit", str(agent_stock_limit),
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120, cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            print(f"    ❌ export failed: {result.stderr[:300]}")
            return False
        return True
    except Exception as exc:
        print(f"    ❌ export exception: {exc}")
        return False


def _load_or_none(path: Path) -> dict | None:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _compute_market_regime(report: dict) -> str:
    """Determine market regime from candidate avg next return."""
    per_stock = report.get("per_stock", [])
    returns = [
        s["next_return_pct"] for s in per_stock
        if s.get("data_available") and s.get("next_return_pct") is not None
    ]
    if len(returns) < 3:
        return "missing"
    avg = sum(returns) / len(returns)
    if avg > 1.0:
        return "broad_up"
    elif avg < -1.0:
        return "broad_down"
    else:
        return "mixed"


def run_single_date(
    date: str,
    mode: str,
    source: str,
    horizon: int,
    agent_stock_limit: int,
    skip_agent_refresh: bool,
    stock_limit: int,
    force: bool,
) -> dict:
    """Run validation for a single date. Returns status dict."""
    print(f"\n{'='*60}")
    print(f"  Processing {date}...")
    print(f"{'='*60}")

    bridge_dir = PROJECT_ROOT / "reports" / "agent_bridge" / date
    candidate_path = bridge_dir / "top30_candidates.json"
    ranking_path = bridge_dir / "aihf_stock_ranking.json"

    # Step 1: Optionally recompute candidates
    if mode == "recompute-candidates":
        print(f"  📦 Recomputing candidates for {date}...")
        ok = _run_export(date, stock_limit, agent_stock_limit)
        if not ok:
            print(f"  ❌ Export failed for {date}")
            return {"date": date, "status": "export_failed"}

    # Step 2: Check candidate file exists
    if not candidate_path.exists():
        print(f"  ⚠️ Missing candidates: {candidate_path}")
        return {"date": date, "status": "missing_candidates"}

    # Step 3: Load data
    candidate_data = _load_or_none(candidate_path) or {}
    candidates = candidate_data.get("candidates", [])
    ranking_data = _load_or_none(ranking_path) or {}
    ranking_items = ranking_data.get("items", [])

    if not candidates:
        print(f"  ⚠️ Empty candidates for {date}")
        return {"date": date, "status": "missing_candidates"}

    print(f"  📊 Candidates: {len(candidates)}, Ranking items: {len(ranking_items)}")

    # Step 4: Fetch next-day bars
    print(f"  📈 Fetching next-day bars (horizon={horizon})...")
    bar_data = fetch_next_day_bars(candidates, date, source, horizon)
    available = sum(1 for v in bar_data.values() if v.get("data_available"))
    print(f"  📊 Data available: {available}/{len(candidates)}")

    if available == 0:
        print(f"  ⚠️ No forward data for {date}")
        return {"date": date, "status": "missing_forward_data", "candidate_count": len(candidates)}

    # Step 5: Run validation
    try:
        report = run_validation(candidates, bar_data, ranking_items, date)
    except Exception as exc:
        print(f"  ❌ Validation failed: {exc}")
        return {"date": date, "status": "validation_failed", "error": str(exc)}

    # Step 6: Save output
    out_dir = OUTPUT_DIR / date
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "next_day_selection_validation.json"
    if json_path.exists() and not force:
        print(f"  ⚠️ Output exists, skipping (use --force)")
        return {"date": date, "status": "skipped_exists"}

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = generate_markdown(report)
    md_path = out_dir / "next_day_selection_validation.md"
    md_path.write_text(md, encoding="utf-8")

    # Determine market regime
    regime = _compute_market_regime(report)
    print(f"  ✅ Saved. Market regime: {regime}")

    return {
        "date": date,
        "status": "ok",
        "candidate_count": len(candidates),
        "data_available": available,
        "market_regime": regime,
        "avg_candidate_return": _avg_return(report),
    }


def _avg_return(report: dict) -> float | None:
    """Extract avg candidate return from per_stock data."""
    per_stock = report.get("per_stock", [])
    returns = [
        s["next_return_pct"] for s in per_stock
        if s.get("data_available") and s.get("next_return_pct") is not None
    ]
    if not returns:
        return None
    return round(sum(returns) / len(returns), 4)


# ======================================================================
# AGGREGATE
# ======================================================================

def build_aggregate(
    date_results: list[dict],
    single_reports: dict[str, dict],
    run_config: dict,
) -> dict:
    """Build aggregate validation report from multiple single-day results."""
    ok_dates = [r["date"] for r in date_results if r["status"] == "ok"]
    valid_reports = {d: single_reports[d] for d in ok_dates if d in single_reports}

    # === Date Status Table ===
    date_status_table = []
    for r in date_results:
        entry = {
            "date": r["date"],
            "status": r["status"],
            "candidate_count": r.get("candidate_count"),
            "data_available": r.get("data_available"),
            "market_regime": r.get("market_regime"),
            "avg_candidate_return": r.get("avg_candidate_return"),
        }
        date_status_table.append(entry)

    # === Coverage Summary ===
    total_candidates = sum(r.get("candidate_count", 0) for r in date_results if r["status"] == "ok")
    total_available = sum(r.get("data_available", 0) for r in date_results if r["status"] == "ok")
    coverage_summary = {
        "valid_date_count": len(ok_dates),
        "total_candidate_entries": total_candidates,
        "total_data_available": total_available,
        "coverage_ratio": round(total_available / total_candidates, 4) if total_candidates > 0 else 0,
    }

    # === Market Regime Summary ===
    regime_groups: dict[str, list[dict]] = defaultdict(list)
    for r in date_results:
        if r["status"] == "ok" and r.get("market_regime"):
            regime_groups[r["market_regime"]].append(r)

    market_regime_summary = {}
    for regime, items in regime_groups.items():
        avg_returns = [i["avg_candidate_return"] for i in items if i.get("avg_candidate_return") is not None]
        market_regime_summary[regime] = {
            "date_count": len(items),
            "avg_candidate_return": round(sum(avg_returns) / len(avg_returns), 4) if avg_returns else None,
        }

    # === Factor Performance Summary ===
    factor_perf = _aggregate_factor_performance(valid_reports)

    # === Interpretation ===
    interpretation = _build_interpretation(factor_perf, coverage_summary, market_regime_summary)

    return {
        "run_config": run_config,
        "date_status_table": date_status_table,
        "coverage_summary": coverage_summary,
        "market_regime_summary": market_regime_summary,
        "factor_performance_summary": factor_perf,
        "interpretation": interpretation,
        "cautions": [
            "Historical recompute validates current rules on past dates.",
            "This is not the same as live historical performance if candidate files were regenerated.",
            "Sample size is still small (≤30 candidates per date, ≤7 dates).",
            "Do not change scoring weights from this report alone.",
            "Need 20+ trading days of rolling validation before any weight adjustment.",
        ],
    }


def _aggregate_factor_performance(valid_reports: dict[str, dict]) -> dict:
    """Aggregate factor performance across dates."""
    result = {}

    # --- A. Decision Score ---
    ds_gaps = []
    ds_positive_dates = 0
    ds_negative_dates = 0
    ds_top5_avgs = []
    ds_bot10_avgs = []
    for d, report in sorted(valid_reports.items()):
        rg = report.get("ranking_groups", {})
        t5 = rg.get("top5_by_decision_score", {})
        b10 = rg.get("bottom10_by_decision_score", {})
        t5_avg = t5.get("avg_next_return_pct")
        b10_avg = b10.get("avg_next_return_pct")
        if t5_avg is not None and b10_avg is not None:
            gap = t5_avg - b10_avg
            ds_gaps.append(gap)
            if gap > 0:
                ds_positive_dates += 1
            elif gap < 0:
                ds_negative_dates += 1
            ds_top5_avgs.append(t5_avg)
            ds_bot10_avgs.append(b10_avg)

    valid_count = len(ds_gaps)
    result["decision_score"] = {
        "top5_avg_return": round(sum(ds_top5_avgs) / len(ds_top5_avgs), 4) if ds_top5_avgs else None,
        "bottom10_avg_return": round(sum(ds_bot10_avgs) / len(ds_bot10_avgs), 4) if ds_bot10_avgs else None,
        "avg_gap": round(sum(ds_gaps) / len(ds_gaps), 4) if ds_gaps else None,
        "positive_gap_date_count": ds_positive_dates,
        "negative_gap_date_count": ds_negative_dates,
        "valid_date_count": valid_count,
        "signal_consistency": round(ds_positive_dates / valid_count * 100, 1) if valid_count > 0 else None,
    }

    # --- B. Stock Short Score ---
    ss_gaps = []
    ss_pos = 0
    ss_neg = 0
    for d, report in sorted(valid_reports.items()):
        sb = report.get("score_buckets", {})
        h = sb.get("stock_short_score_high", {})
        l = sb.get("stock_short_score_low", {})
        h_avg = h.get("avg_next_return_pct")
        l_avg = l.get("avg_next_return_pct")
        if h_avg is not None and l_avg is not None:
            gap = h_avg - l_avg
            ss_gaps.append(gap)
            if gap > 0:
                ss_pos += 1
            elif gap < 0:
                ss_neg += 1

    ss_valid = len(ss_gaps)
    result["stock_short_score"] = {
        "avg_gap": round(sum(ss_gaps) / len(ss_gaps), 4) if ss_gaps else None,
        "positive_gap_date_count": ss_pos,
        "negative_gap_date_count": ss_neg,
        "valid_date_count": ss_valid,
        "signal_consistency": round(ss_pos / ss_valid * 100, 1) if ss_valid > 0 else None,
    }

    # --- C. Trade Eligibility ---
    elig_returns: dict[str, list[float]] = defaultdict(list)
    for d, report in sorted(valid_reports.items()):
        cat = report.get("categorical_groups", {})
        for elig in ["focus", "watch", "backup", "avoid"]:
            stat = cat.get(f"trade_eligibility_{elig}", {})
            avg = stat.get("avg_next_return_pct")
            if avg is not None:
                elig_returns[elig].append(avg)

    elig_summary = {}
    for elig, rets in elig_returns.items():
        elig_summary[elig] = {
            "avg_return": round(sum(rets) / len(rets), 4) if rets else None,
            "date_count": len(rets),
        }

    focus_avg = elig_returns.get("focus", [])
    avoid_avg = elig_returns.get("avoid", [])
    backup_avg = elig_returns.get("backup", [])
    ba_combined = avoid_avg + backup_avg

    focus_vs_avoid = None
    focus_vs_ba = None
    if focus_avg and avoid_avg:
        focus_vs_avoid = round(sum(focus_avg) / len(focus_avg) - sum(avoid_avg) / len(avoid_avg), 4)
    if focus_avg and ba_combined:
        focus_vs_ba = round(sum(focus_avg) / len(focus_avg) - sum(ba_combined) / len(ba_combined), 4)

    result["trade_eligibility"] = {
        "group_returns": elig_summary,
        "focus_vs_avoid_gap": focus_vs_avoid,
        "focus_vs_backup_avoid_gap": focus_vs_ba,
    }

    # --- D. Source Pool ---
    pool_returns: dict[str, list[float]] = defaultdict(list)
    for d, report in sorted(valid_reports.items()):
        cat = report.get("categorical_groups", {})
        for pool in ["trend", "burst"]:
            stat = cat.get(f"source_pool_{pool}", {})
            avg = stat.get("avg_next_return_pct")
            if avg is not None:
                pool_returns[pool].append(avg)

    trend_avg = pool_returns.get("trend", [])
    burst_avg = pool_returns.get("burst", [])
    trend_vs_burst = None
    if trend_avg and burst_avg:
        trend_vs_burst = round(sum(trend_avg) / len(trend_avg) - sum(burst_avg) / len(burst_avg), 4)

    result["source_pool"] = {
        "trend_avg_return": round(sum(trend_avg) / len(trend_avg), 4) if trend_avg else None,
        "burst_avg_return": round(sum(burst_avg) / len(burst_avg), 4) if burst_avg else None,
        "trend_vs_burst_gap": trend_vs_burst,
        "trend_date_count": len(trend_avg),
        "burst_date_count": len(burst_avg),
    }

    # --- E. Agent Incremental ---
    agent_gaps = []
    for d, report in sorted(valid_reports.items()):
        cat = report.get("categorical_groups", {})
        a = cat.get("analyzed", {})
        s = cat.get("skipped_by_agent_stock_limit", {})
        a_avg = a.get("avg_next_return_pct")
        s_avg = s.get("avg_next_return_pct")
        if a_avg is not None and s_avg is not None:
            agent_gaps.append(a_avg - s_avg)

    result["agent_incremental"] = {
        "avg_gap": round(sum(agent_gaps) / len(agent_gaps), 4) if agent_gaps else None,
        "valid_date_count": len(agent_gaps),
    }

    return result


def _build_interpretation(
    factor_perf: dict,
    coverage: dict,
    market_regime: dict,
) -> dict:
    """Build interpretation from aggregated factor performance."""
    interp = {}
    valid_count = coverage.get("valid_date_count", 0)

    # Decision Score Signal
    ds = factor_perf.get("decision_score", {})
    ds_gap = ds.get("avg_gap")
    ds_consistency = ds.get("signal_consistency")
    if ds_gap is not None and ds_consistency is not None and valid_count >= 5:
        if ds_gap > 1.0 and ds_consistency >= 60:
            interp["decision_score_signal"] = {"signal": "positive", "avg_gap": ds_gap, "consistency": ds_consistency}
        elif ds_gap < -1.0 and ds.get("negative_gap_date_count", 0) / max(1, valid_count) * 100 >= 60:
            interp["decision_score_signal"] = {"signal": "negative", "avg_gap": ds_gap, "consistency": ds_consistency}
        else:
            interp["decision_score_signal"] = {"signal": "inconclusive", "avg_gap": ds_gap, "consistency": ds_consistency}
    else:
        interp["decision_score_signal"] = {"signal": "insufficient_samples", "reason": f"valid_dates={valid_count} < 5"}

    # Stock Short Score Signal
    ss = factor_perf.get("stock_short_score", {})
    ss_gap = ss.get("avg_gap")
    ss_consistency = ss.get("signal_consistency")
    if ss_gap is not None and ss_consistency is not None and valid_count >= 5:
        if ss_gap > 1.0 and ss_consistency >= 60:
            interp["stock_short_score_signal"] = {"signal": "positive", "avg_gap": ss_gap, "consistency": ss_consistency}
        elif ss_gap < -1.0 and ss.get("negative_gap_date_count", 0) / max(1, valid_count) * 100 >= 60:
            interp["stock_short_score_signal"] = {"signal": "negative", "avg_gap": ss_gap, "consistency": ss_consistency}
        else:
            interp["stock_short_score_signal"] = {"signal": "inconclusive", "avg_gap": ss_gap, "consistency": ss_consistency}
    else:
        interp["stock_short_score_signal"] = {"signal": "insufficient_samples", "reason": f"valid_dates={valid_count} < 5"}

    # Trade Eligibility Signal
    te = factor_perf.get("trade_eligibility", {})
    focus_vs_ba = te.get("focus_vs_backup_avoid_gap")
    if focus_vs_ba is not None and valid_count >= 3:
        if focus_vs_ba > 1.0:
            interp["trade_eligibility_signal"] = {"signal": "positive", "focus_vs_backup_avoid_gap": focus_vs_ba}
        else:
            interp["trade_eligibility_signal"] = {"signal": "inconclusive", "focus_vs_backup_avoid_gap": focus_vs_ba}
    else:
        interp["trade_eligibility_signal"] = {"signal": "insufficient_samples"}

    # Agent Incremental Signal
    ag = factor_perf.get("agent_incremental", {})
    ag_gap = ag.get("avg_gap")
    ag_valid = ag.get("valid_date_count", 0)
    if ag_gap is not None and ag_valid >= 3:
        if ag_gap > 1.0:
            interp["agent_incremental_signal"] = {"signal": "positive", "avg_gap": ag_gap}
        elif ag_gap < -1.0:
            interp["agent_incremental_signal"] = {"signal": "negative", "avg_gap": ag_gap}
        else:
            interp["agent_incremental_signal"] = {"signal": "inconclusive", "avg_gap": ag_gap}
    else:
        interp["agent_incremental_signal"] = {"signal": "insufficient_samples", "reason": f"valid_dates={ag_valid}"}

    # Trend vs Burst Signal
    sp = factor_perf.get("source_pool", {})
    tb_gap = sp.get("trend_vs_burst_gap")
    if tb_gap is not None:
        if tb_gap > 1.0:
            interp["trend_vs_burst_signal"] = {"signal": "trend_outperforms", "gap": tb_gap}
        elif tb_gap < -1.0:
            interp["trend_vs_burst_signal"] = {"signal": "burst_outperforms", "gap": tb_gap}
        else:
            interp["trend_vs_burst_signal"] = {"signal": "inconclusive", "gap": tb_gap}
    else:
        interp["trend_vs_burst_signal"] = {"signal": "insufficient_samples"}

    # Market Regime Effect
    regime_effect = {}
    for regime, info in market_regime.items():
        if info.get("date_count", 0) >= 1:
            regime_effect[regime] = {"avg_return": info.get("avg_candidate_return")}
    interp["market_regime_effect"] = regime_effect

    interp["caution"] = "Do not change scoring weights from this report alone. Need 20+ days of rolling validation."

    return interp


def generate_aggregate_markdown(aggregate: dict) -> str:
    """Generate aggregate markdown report."""
    lines = []
    rc = aggregate.get("run_config", {})
    dates = rc.get("dates", [])
    lines.append(f"# Selection Validation Aggregate — {dates[0] if dates else '?'} to {dates[-1] if dates else '?'}")
    lines.append(f"")
    lines.append(f"> Historical recompute validates current rules on past dates. Not a backtest.")
    lines.append(f"")

    # 1. Run Config
    lines.append(f"## 1. Run Config")
    lines.append(f"")
    lines.append(f"- Mode: {rc.get('mode', '?')}")
    lines.append(f"- Source: {rc.get('source', '?')}")
    lines.append(f"- Horizon: {rc.get('horizon', '?')}")
    lines.append(f"- Dates: {', '.join(dates)}")
    lines.append(f"")

    # 2. Date Status
    lines.append(f"## 2. Date Status")
    lines.append(f"")
    lines.append(f"| {'Date':<12} {'Status':<20} {'Candidates':>10} {'Available':>10} {'Regime':<12} {'Avg Ret%':>9} |")
    lines.append(f"|{'─'*14}|{'─'*22}|{'─'*12}|{'─'*12}|{'─'*14}|{'─'*11}|")
    for row in aggregate.get("date_status_table", []):
        ret_s = f"{row['avg_candidate_return']:.2f}" if row.get("avg_candidate_return") is not None else "N/A"
        lines.append(
            f"| {row['date']:<12} {row['status']:<20} "
            f"{row.get('candidate_count') or '-':>10} {row.get('data_available') or '-':>10} "
            f"{row.get('market_regime') or '-':<12} {ret_s:>9} |"
        )
    lines.append(f"")

    # 3. Coverage
    cov = aggregate.get("coverage_summary", {})
    lines.append(f"## 3. Coverage Summary")
    lines.append(f"")
    lines.append(f"- Valid dates: {cov.get('valid_date_count', 0)}")
    lines.append(f"- Total candidate entries: {cov.get('total_candidate_entries', 0)}")
    lines.append(f"- Total data available: {cov.get('total_data_available', 0)}")
    lines.append(f"- Coverage ratio: {cov.get('coverage_ratio', 0):.1%}")
    lines.append(f"")

    # 4. Market Regime
    mr = aggregate.get("market_regime_summary", {})
    lines.append(f"## 4. Market Regime Summary")
    lines.append(f"")
    for regime, info in sorted(mr.items()):
        avg_r = info.get("avg_candidate_return")
        avg_s = f"{avg_r:.2f}%" if avg_r is not None else "N/A"
        lines.append(f"- **{regime}**: {info.get('date_count', 0)} dates, avg_candidate_return={avg_s}")
    lines.append(f"")

    # 5. Decision Score
    fp = aggregate.get("factor_performance_summary", {})
    ds = fp.get("decision_score", {})
    lines.append(f"## 5. Decision Score Validation")
    lines.append(f"")
    lines.append(f"- top5 avg return: {ds.get('top5_avg_return', 'N/A')}")
    lines.append(f"- bottom10 avg return: {ds.get('bottom10_avg_return', 'N/A')}")
    lines.append(f"- avg gap: {ds.get('avg_gap', 'N/A')}")
    lines.append(f"- positive gap dates: {ds.get('positive_gap_date_count', 0)}/{ds.get('valid_date_count', 0)}")
    lines.append(f"- signal consistency: {ds.get('signal_consistency', 'N/A')}%")
    lines.append(f"")

    # 6. Stock Short Score
    ss = fp.get("stock_short_score", {})
    lines.append(f"## 6. Stock Short Score Validation")
    lines.append(f"")
    lines.append(f"- avg gap (high vs low): {ss.get('avg_gap', 'N/A')}")
    lines.append(f"- positive gap dates: {ss.get('positive_gap_date_count', 0)}/{ss.get('valid_date_count', 0)}")
    lines.append(f"- signal consistency: {ss.get('signal_consistency', 'N/A')}%")
    lines.append(f"")

    # 7. Trade Eligibility
    te = fp.get("trade_eligibility", {})
    lines.append(f"## 7. Trade Eligibility Validation")
    lines.append(f"")
    for elig, info in sorted(te.get("group_returns", {}).items()):
        avg_r = info.get("avg_return")
        avg_s = f"{avg_r:.2f}%" if avg_r is not None else "N/A"
        lines.append(f"- **{elig}**: avg_return={avg_s} (over {info.get('date_count', 0)} dates)")
    lines.append(f"- focus vs avoid gap: {te.get('focus_vs_avoid_gap', 'N/A')}")
    lines.append(f"- focus vs backup/avoid gap: {te.get('focus_vs_backup_avoid_gap', 'N/A')}")
    lines.append(f"")

    # 8. Trend vs Burst
    sp = fp.get("source_pool", {})
    lines.append(f"## 8. Trend vs Burst Validation")
    lines.append(f"")
    lines.append(f"- trend avg return: {sp.get('trend_avg_return', 'N/A')} (over {sp.get('trend_date_count', 0)} dates)")
    lines.append(f"- burst avg return: {sp.get('burst_avg_return', 'N/A')} (over {sp.get('burst_date_count', 0)} dates)")
    lines.append(f"- trend vs burst gap: {sp.get('trend_vs_burst_gap', 'N/A')}")
    lines.append(f"")

    # 9. Agent Incremental
    ag = fp.get("agent_incremental", {})
    lines.append(f"## 9. Agent Incremental Validation")
    lines.append(f"")
    lines.append(f"- analyzed vs skipped avg gap: {ag.get('avg_gap', 'N/A')}")
    lines.append(f"- valid dates: {ag.get('valid_date_count', 0)}")
    lines.append(f"")

    # 10. Interpretation
    interp = aggregate.get("interpretation", {})
    lines.append(f"## 10. Interpretation")
    lines.append(f"")
    for key in ["decision_score_signal", "stock_short_score_signal", "trade_eligibility_signal",
                 "agent_incremental_signal", "trend_vs_burst_signal"]:
        sig = interp.get(key, {})
        signal = sig.get("signal", "?")
        icon = "✅" if signal == "positive" else "❌" if signal == "negative" else "⚠️"
        gap = sig.get("avg_gap") or sig.get("gap")
        gap_s = f", gap={gap:.2f}pp" if gap is not None else ""
        consistency = sig.get("consistency")
        cons_s = f", consistency={consistency:.0f}%" if consistency is not None else ""
        reason = sig.get("reason", "")
        reason_s = f" ({reason})" if reason else ""
        lines.append(f"- {icon} **{key}**: {signal}{gap_s}{cons_s}{reason_s}")

    me = interp.get("market_regime_effect", {})
    if me:
        lines.append(f"")
        lines.append(f"**Market regime effect:**")
        for regime, info in sorted(me.items()):
            avg_r = info.get("avg_return")
            avg_s = f"{avg_r:.2f}%" if avg_r is not None else "N/A"
            lines.append(f"- {regime}: avg_candidate_return={avg_s}")
    lines.append(f"")

    # 11. Cautions
    lines.append(f"## 11. Cautions")
    lines.append(f"")
    for c in aggregate.get("cautions", []):
        lines.append(f"- {c}")
    lines.append(f"")

    return "\n".join(lines)


# ======================================================================
# MAIN
# ======================================================================


def _sample_validation_report(date: str, returns: list[float]) -> dict:
    """Build a deterministic validation report for open-source sample mode."""
    per_stock = []
    for idx, ret in enumerate(returns):
        per_stock.append({
            "code": f"600{idx + 1:03d}",
            "name": f"Sample Stock {idx + 1}",
            "data_available": True,
            "next_return_pct": ret,
            "next_high_return_pct": ret + 0.8,
            "next_low_return_pct": ret - 0.7,
            "decision_score": 70 - idx,
            "stock_short_score": 65 - idx,
        })
    top = returns[:5]
    bottom = returns[-5:]
    trend = returns[::2]
    burst = returns[1::2]
    return {
        "as_of": date,
        "sample_mode": True,
        "coverage": {"total_candidates": len(returns), "data_available": len(returns), "data_missing": 0, "missing_codes": []},
        "ranking_groups": {
            "top5_by_decision_score": {"sample_count": len(top), "avg_next_return_pct": round(sum(top) / len(top), 4)},
            "bottom10_by_decision_score": {"sample_count": len(bottom), "avg_next_return_pct": round(sum(bottom) / len(bottom), 4)},
        },
        "score_buckets": {
            "stock_short_score_high": {"sample_count": len(top), "avg_next_return_pct": round(sum(top) / len(top), 4)},
            "stock_short_score_low": {"sample_count": len(bottom), "avg_next_return_pct": round(sum(bottom) / len(bottom), 4)},
        },
        "categorical_groups": {
            "trade_eligibility_focus": {"sample_count": len(top), "avg_next_return_pct": round(sum(top) / len(top), 4)},
            "trade_eligibility_watch": {"sample_count": len(returns), "avg_next_return_pct": round(sum(returns) / len(returns), 4)},
            "trade_eligibility_backup": {"sample_count": len(bottom), "avg_next_return_pct": round(sum(bottom) / len(bottom), 4)},
            "trade_eligibility_avoid": {"sample_count": len(bottom), "avg_next_return_pct": round(sum(bottom) / len(bottom), 4)},
            "source_pool_trend": {"sample_count": len(trend), "avg_next_return_pct": round(sum(trend) / len(trend), 4)},
            "source_pool_burst": {"sample_count": len(burst), "avg_next_return_pct": round(sum(burst) / len(burst), 4)},
            "analyzed": {"sample_count": len(top), "avg_next_return_pct": round(sum(top) / len(top), 4)},
            "skipped_by_agent_stock_limit": {"sample_count": len(bottom), "avg_next_return_pct": round(sum(bottom) / len(bottom), 4)},
        },
        "interpretation": {"caution": "sample mode only; not investment advice"},
        "per_stock": per_stock,
    }


def run_sample_batch(force: bool = False) -> dict:
    """Run a two-date validation sample without external data."""
    sample_reports = {
        "2026-06-27": _sample_validation_report("2026-06-27", [1.8, 1.4, 1.1, 0.8, 0.5, 0.2, -0.1, -0.3, -0.6, -0.9]),
        "2026-06-28": _sample_validation_report("2026-06-28", [0.9, 0.7, 0.4, 0.2, 0.1, -0.1, -0.2, -0.4, -0.6, -0.8]),
    }
    date_results = []
    for date, report in sample_reports.items():
        out_dir = OUTPUT_DIR / date
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / "next_day_selection_validation.json"
        if force or not json_path.exists():
            json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            (out_dir / "next_day_selection_validation.md").write_text(generate_markdown(report), encoding="utf-8")
        date_results.append({
            "date": date,
            "status": "ok",
            "candidate_count": len(report["per_stock"]),
            "data_available": len(report["per_stock"]),
            "market_regime": _compute_market_regime(report),
            "avg_candidate_return": _avg_return(report),
        })
    run_config = {"dates": list(sample_reports.keys()), "mode": "sample", "source": "synthetic-fixture", "horizon": 1, "agent_stock_limit": 5, "stock_limit": 10, "skip_agent_refresh": True}
    aggregate = build_aggregate(date_results, sample_reports, run_config)
    aggregate["sample_mode"] = True
    aggregate["disclaimer"] = "Research sample only. Not investment advice or stock recommendation."
    sample_dir = OUTPUT_DIR / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)
    (sample_dir / "selection_validation_aggregate.json").write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8")
    (sample_dir / "selection_validation_aggregate.md").write_text(generate_aggregate_markdown(aggregate), encoding="utf-8")
    print(f"  Sample validation aggregate: {sample_dir}")
    return aggregate
def main():
    parser = argparse.ArgumentParser(description="Batch selection validation")
    parser.add_argument("--dates", nargs="*", default=None, help="Specific dates to validate")
    parser.add_argument("--start-date", default=None, help="Start date (auto-scan)")
    parser.add_argument("--end-date", default=None, help="End date (auto-scan)")
    parser.add_argument("--mode", default="existing-artifacts",
                        choices=["existing-artifacts", "recompute-candidates", "sample"],
                        help="How to obtain candidates")
    parser.add_argument("--source", default="stockdb-sdk", help="Data source")
    parser.add_argument("--horizon", type=int, default=1, help="Forward days")
    parser.add_argument("--agent-stock-limit", type=int, default=10)
    parser.add_argument("--stock-limit", type=int, default=30)
    parser.add_argument("--skip-agent-refresh", action="store_true")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output")
    args = parser.parse_args()

    if args.mode == "sample":
        run_sample_batch(force=args.force)
        return

    # Determine dates
    if args.dates:
        dates = args.dates
    elif args.start_date and args.end_date:
        all_dates = _scan_available_dates()
        dates = [d for d in all_dates if args.start_date <= d <= args.end_date]
    else:
        dates = _scan_available_dates()

    if not dates:
        print("❌ No dates to validate")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"  Batch Selection Validation")
    print(f"  Dates: {', '.join(dates)}")
    print(f"  Mode: {args.mode}")
    print(f"  Source: {args.source}")
    print(f"{'='*60}")

    # Run each date
    date_results = []
    single_reports: dict[str, dict] = {}

    for date in dates:
        result = run_single_date(
            date=date,
            mode=args.mode,
            source=args.source,
            horizon=args.horizon,
            agent_stock_limit=args.agent_stock_limit,
            skip_agent_refresh=args.skip_agent_refresh,
            stock_limit=args.stock_limit,
            force=args.force,
        )
        date_results.append(result)

        # Load the saved report for aggregation
        if result["status"] == "ok":
            report_path = OUTPUT_DIR / date / "next_day_selection_validation.json"
            if report_path.exists():
                try:
                    single_reports[date] = json.loads(report_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

    # Build aggregate
    ok_count = sum(1 for r in date_results if r["status"] == "ok")
    print(f"\n{'='*60}")
    print(f"  Building aggregate from {ok_count} valid dates...")
    print(f"{'='*60}")

    run_config = {
        "dates": dates,
        "mode": args.mode,
        "source": args.source,
        "horizon": args.horizon,
        "agent_stock_limit": args.agent_stock_limit,
        "stock_limit": args.stock_limit,
        "skip_agent_refresh": args.skip_agent_refresh,
    }

    aggregate = build_aggregate(date_results, single_reports, run_config)

    # Save aggregate
    valid_dates = [r["date"] for r in date_results if r["status"] == "ok"]
    if valid_dates:
        agg_dir = OUTPUT_DIR / "aggregate" / f"{valid_dates[0]}_to_{valid_dates[-1]}"
        agg_dir.mkdir(parents=True, exist_ok=True)

        agg_json = agg_dir / "selection_validation_aggregate.json"
        agg_json.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ Aggregate JSON: {agg_json}")

        agg_md = generate_aggregate_markdown(aggregate)
        agg_md_path = agg_dir / "selection_validation_aggregate.md"
        agg_md_path.write_text(agg_md, encoding="utf-8")
        print(f"  ✅ Aggregate Markdown: {agg_md_path}")

    # Print summary
    interp = aggregate.get("interpretation", {})
    print(f"\n=== Interpretation Summary ===")
    for key in ["decision_score_signal", "stock_short_score_signal", "trade_eligibility_signal",
                 "agent_incremental_signal", "trend_vs_burst_signal"]:
        sig = interp.get(key, {})
        signal = sig.get("signal", "?")
        icon = "✅" if signal == "positive" else "❌" if signal == "negative" else "⚠️"
        gap = sig.get("avg_gap") or sig.get("gap")
        gap_s = f" gap={gap:.2f}pp" if gap is not None else ""
        print(f"  {icon} {key}: {signal}{gap_s}")

    print(f"\n  ⚠️ Do not change scoring weights from this report alone.")


if __name__ == "__main__":
    main()


